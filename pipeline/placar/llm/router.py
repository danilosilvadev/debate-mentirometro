"""Roteador: Claude CLI primeiro, OpenRouter depois, APIs opcionais no fim.

Failover em erro de CLI, timeout, limite de uso ou JSON inválido.
Uma retentativa no mesmo provedor quando o erro é transitório.
Limite de uso abre o circuit breaker na hora. Os outros erros abrem
depois de N falhas seguidas. Cada chamada fica no log com provedor e latência.
"""

from __future__ import annotations

import logging
import time
from typing import Callable

from placar.jsonrepair import InvalidJson, parse_model_json
from placar.llm.base import (
    CallRecord,
    LlmProvider,
    LlmRequest,
    LlmResult,
    ProviderError,
    ProviderUnavailable,
    RateLimitFailure,
    TimeoutFailure,
)

log = logging.getLogger("placar.llm")


class CircuitBreaker:
    def __init__(
        self, *, threshold: int, cooldown_s: float, clock: Callable[[], float]
    ) -> None:
        self.threshold = threshold
        self.cooldown_s = cooldown_s
        self._clock = clock
        self._failures: dict[str, int] = {}
        self._open_until: dict[str, float] = {}

    def allow(self, name: str) -> bool:
        return self._clock() >= self._open_until.get(name, 0.0)

    def success(self, name: str) -> None:
        self._failures[name] = 0
        self._open_until[name] = 0.0

    def fail(self, name: str, *, force_open: bool = False) -> None:
        count = self._failures.get(name, 0) + 1
        self._failures[name] = count
        if force_open or count >= self.threshold:
            self._open_until[name] = self._clock() + self.cooldown_s
            self._failures[name] = 0

    def open_for(self, name: str) -> bool:
        return not self.allow(name)


class ProviderRouter:
    def __init__(
        self,
        providers: list[LlmProvider],
        *,
        retries: int = 1,
        breaker_threshold: int = 3,
        breaker_cooldown_s: float = 60.0,
        timeout_s: float = 12.0,
        clock: Callable[[], float] | None = None,
        perf: Callable[[], float] | None = None,
    ) -> None:
        if not providers:
            raise ValueError("O roteador precisa de ao menos um provedor.")
        self.providers = providers
        self.retries = retries
        self.timeout_s = timeout_s
        self._clock = clock or time.monotonic
        self._perf = perf or time.perf_counter
        self.breaker = CircuitBreaker(
            threshold=breaker_threshold,
            cooldown_s=breaker_cooldown_s,
            clock=self._clock,
        )
        self.history: list[CallRecord] = []
        self.unavailable: set[str] = set()

    def complete(
        self, request: LlmRequest, *, exclude: set[str] | None = None
    ) -> LlmResult:
        skipped = exclude or set()
        records: list[CallRecord] = []
        errors: list[str] = []
        considered = [item for item in self.providers if item.name not in skipped]
        if not considered:
            raise ProviderError("Nenhum provedor sobrou para esta chamada.")
        primary = considered[0].name
        for provider in considered:
            if provider.name in self.unavailable:
                continue
            if not self.breaker.allow(provider.name):
                record = CallRecord(
                    task=request.task,
                    provider=provider.name,
                    latency_ms=0.0,
                    ok=False,
                    failover=provider.name != primary,
                    error="circuit breaker aberto",
                )
                records.append(record)
                self.history.append(record)
                errors.append(f"{provider.name}: circuit breaker aberto")
                continue
            attempts = self.retries + 1
            for attempt in range(1, attempts + 1):
                started = self._perf()
                try:
                    raw = self._generate(provider, request)
                    data = parse_model_json(raw, request.schema)
                except InvalidJson as exc:
                    self._note(
                        records,
                        request,
                        provider.name,
                        started,
                        ok=False,
                        failover=provider.name != primary,
                        error=f"json inválido: {exc.message}",
                        attempt=attempt,
                    )
                    self.breaker.fail(provider.name)
                    errors.append(f"{provider.name}: json inválido")
                    continue
                except ProviderUnavailable as exc:
                    self._note(
                        records,
                        request,
                        provider.name,
                        started,
                        ok=False,
                        failover=True,
                        error=exc.message,
                        attempt=attempt,
                    )
                    self.unavailable.add(provider.name)
                    log.warning("llm provider=%s indisponível, pulando: %s", provider.name, exc.message)
                    errors.append(f"{provider.name}: {exc.message}")
                    break
                except RateLimitFailure as exc:
                    self._note(
                        records,
                        request,
                        provider.name,
                        started,
                        ok=False,
                        failover=True,
                        error=exc.message,
                        attempt=attempt,
                    )
                    self.breaker.fail(provider.name, force_open=True)
                    errors.append(f"{provider.name}: {exc.message}")
                    break
                except ProviderError as exc:
                    self._note(
                        records,
                        request,
                        provider.name,
                        started,
                        ok=False,
                        failover=provider.name != primary,
                        error=exc.message,
                        attempt=attempt,
                    )
                    self.breaker.fail(provider.name)
                    errors.append(f"{provider.name}: {exc.message}")
                    if not exc.retryable or attempt == attempts:
                        break
                    continue
                self.breaker.success(provider.name)
                latency = (self._perf() - started) * 1000
                record = CallRecord(
                    task=request.task,
                    provider=provider.name,
                    latency_ms=latency,
                    ok=True,
                    failover=provider.name != primary,
                    attempt=attempt,
                )
                records.append(record)
                self.history.append(record)
                log.info(
                    "llm task=%s provider=%s ok=1 latency_ms=%.1f failover=%s",
                    request.task,
                    provider.name,
                    latency,
                    int(record.failover),
                )
                return LlmResult(
                    data=data,
                    provider=provider.name,
                    latency_ms=latency,
                    records=records,
                )
        raise ProviderError("Todos os provedores falharam: " + "; ".join(errors))

    def _generate(self, provider: LlmProvider, request: LlmRequest) -> str:
        """Chama o provedor com prazo de relógio de parede.

        O timeout do urllib vale por leitura de socket, não pelo pedido todo:
        um modelo grátis que pinga bytes devagar segurou 120 s no teste.
        """
        import concurrent.futures

        timeout_s = float(getattr(provider, "timeout_s", 0) or self.timeout_s)
        pool = concurrent.futures.ThreadPoolExecutor(max_workers=1)
        future = pool.submit(provider.generate, request, timeout_s)
        try:
            return future.result(timeout=timeout_s + 1.0)
        except concurrent.futures.TimeoutError as exc:
            raise TimeoutFailure(f"{provider.name} passou de {timeout_s:.0f}s.") from exc
        finally:
            pool.shutdown(wait=False, cancel_futures=True)

    def _note(
        self,
        records: list[CallRecord],
        request: LlmRequest,
        provider: str,
        started: float,
        *,
        ok: bool,
        failover: bool,
        error: str,
        attempt: int,
    ) -> None:
        latency = (self._perf() - started) * 1000
        record = CallRecord(
            task=request.task,
            provider=provider,
            latency_ms=latency,
            ok=ok,
            failover=failover,
            error=error,
            attempt=attempt,
        )
        records.append(record)
        self.history.append(record)
        log.info(
            "llm task=%s provider=%s ok=0 latency_ms=%.1f failover=%s error=%s",
            request.task,
            provider,
            latency,
            int(failover),
            error,
        )
