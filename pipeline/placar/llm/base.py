"""Contrato de um provedor de LLM e os erros que disparam failover."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Protocol


@dataclass(frozen=True)
class LlmRequest:
    task: str
    system: str
    user: str
    schema: dict[str, Any]


@dataclass
class CallRecord:
    task: str
    provider: str
    latency_ms: float
    ok: bool
    failover: bool
    error: str | None = None
    attempt: int = 1


class ProviderError(Exception):
    retryable = True
    rate_limited = False

    def __init__(self, message: str) -> None:
        super().__init__(message)
        self.message = message


class TimeoutFailure(ProviderError):
    pass


class RateLimitFailure(ProviderError):
    retryable = False
    rate_limited = True


class CliFailure(ProviderError):
    pass


class TransportFailure(ProviderError):
    pass


class ProviderUnavailable(ProviderError):
    """O provedor não existe nesta máquina (binário ausente). Não adianta tentar de novo."""

    retryable = False


@dataclass
class LlmResult:
    data: dict[str, Any]
    provider: str
    latency_ms: float
    records: list[CallRecord] = field(default_factory=list)


class LlmProvider(Protocol):
    name: str

    def generate(self, request: LlmRequest, timeout_s: float) -> str:
        """Texto cru. JSON inválido volta ao roteador, que tenta consertar."""
