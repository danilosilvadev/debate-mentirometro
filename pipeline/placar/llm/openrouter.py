"""OpenRouter, API compatível com OpenAI. Modelos `:free` são o fallback.

Limites conferidos em 2026-10-21 na documentação oficial
(https://openrouter.ai/docs/api/reference/limits): variantes `:free` têm
20 pedidos por minuto. Por dia: 50 se a conta comprou menos de 10 créditos
no total, 1.000 a partir de 10 créditos comprados alguma vez.
"""

from __future__ import annotations

import json
from typing import Any, Callable
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

from placar.llm.base import LlmRequest, RateLimitFailure, TransportFailure

Transport = Callable[[Request, float], tuple[int, str]]

OPENROUTER_URL = "https://openrouter.ai/api/v1/chat/completions"


def urllib_transport(request: Request, timeout_s: float) -> tuple[int, str]:
    try:
        with urlopen(request, timeout=timeout_s) as response:
            return response.status, response.read().decode("utf-8", "replace")
    except HTTPError as exc:
        body = exc.read().decode("utf-8", "replace")
        return exc.code, body
    except URLError as exc:
        raise TransportFailure(f"OpenRouter inacessível: {exc.reason}") from exc
    except TimeoutError as exc:
        raise TransportFailure("OpenRouter estourou o tempo.") from exc


class OpenRouterProvider:
    name = "openrouter"

    def __init__(
        self,
        *,
        api_key: str,
        model: str = "nvidia/nemotron-3.5-super-vl:free",
        transport: Transport | None = None,
        app_url: str = "http://127.0.0.1:8787",
        url: str = OPENROUTER_URL,
        name: str = "openrouter",
        label: str = "OpenRouter",
        key_env: str = "OPENROUTER_API_KEY",
    ) -> None:
        self.url = url
        self.strict_schema = True
        self.name = name
        self.label = label
        self.key_env = key_env
        self.api_key = api_key
        self.model = model
        self._transport = transport or urllib_transport
        self.app_url = app_url

    def generate(self, request: LlmRequest, timeout_s: float) -> str:
        if not self.api_key:
            raise TransportFailure(f"{self.key_env} não está definida.")
        try:
            return self._post(request, timeout_s, schema=True)
        except TransportFailure as exc:
            if "400" not in exc.message and "schema" not in exc.message.lower():
                raise
            return self._post(request, timeout_s, schema=False)

    def _post(self, request: LlmRequest, timeout_s: float, *, schema: bool) -> str:
        body: dict[str, Any] = {
            "model": self.model,
            "messages": [
                {"role": "system", "content": request.system},
                {
                    "role": "user",
                    "content": (
                        "Responda apenas com o objeto JSON pedido"
                        + ("" if schema else ", neste JSON Schema:\n"
                           + json.dumps(request.schema, ensure_ascii=False))
                        + "\n\n" + request.user
                    ),
                },
            ],
            "temperature": 0,
        }
        if "gpt-oss" in self.model:
            body["reasoning_effort"] = "low"  # menos tokens de raciocínio, menos cota por minuto
        if schema:
            body["response_format"] = {
                "type": "json_schema",
                "json_schema": {
                    "name": request.task.replace(".", "_"),
                    "strict": self.strict_schema,
                    "schema": request.schema,
                },
            }
        else:
            body["response_format"] = {"type": "json_object"}
        raw = json.dumps(body).encode("utf-8")
        http_request = Request(
            self.url,
            data=raw,
            headers={
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json",
                "HTTP-Referer": self.app_url,
                "X-Title": "Placar da Verdade",
                # O Cloudflare da Groq recusa o User-Agent do urllib (erro 1010).
                "User-Agent": "placar-pipeline/0.2",
            },
            method="POST",
        )
        import time as _time

        started = _time.monotonic()
        status, text = self._transport(http_request, timeout_s)
        wait = _retry_after(text) if status == 429 else None
        # Limite de tokens por minuto (Groq): costuma liberar em poucos segundos; espera uma vez.
        if wait is not None and wait + (_time.monotonic() - started) < timeout_s - 1:
            _time.sleep(wait + 0.2)
            status, text = self._transport(http_request, timeout_s)
        if status == 429 or (status >= 400 and _rate_limited(text)):
            raise RateLimitFailure(f"{self.label} limitou ({status}).")
        if status == 402:
            raise RateLimitFailure(f"{self.label} recusou por crédito ou cota (402).")
        if status >= 400:
            raise TransportFailure(f"{self.label} HTTP {status}: {text[:300]}")
        try:
            payload = json.loads(text)
            return payload["choices"][0]["message"]["content"]
        except (KeyError, IndexError, json.JSONDecodeError, TypeError) as exc:
            raise TransportFailure(f"{self.label} devolveu um corpo inesperado.") from exc


def _rate_limited(text: str) -> bool:
    folded = text.lower()
    return "rate limit" in folded or "rate_limit" in folded or "429" in folded


def _retry_after(text: str) -> float | None:
    import re

    match = re.search(r"try again in (?:(\d+)m)?([\d.]+)(ms|s)", text)
    if not match:
        return None
    value = float(match.group(2)) / (1000 if match.group(3) == "ms" else 1)
    return value + 60 * int(match.group(1) or 0)
