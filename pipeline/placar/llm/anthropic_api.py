"""API direta da Anthropic. Só entra na cadeia se ANTHROPIC_API_KEY existir."""

from __future__ import annotations

import json
from typing import Any

from placar.llm.base import LlmRequest, RateLimitFailure, TransportFailure
from placar.llm.openrouter import Transport, urllib_transport

URL = "https://api.anthropic.com/v1/messages"


class AnthropicApiProvider:
    name = "anthropic"

    def __init__(
        self,
        *,
        api_key: str,
        model: str = "claude-haiku-4-5",
        transport: Transport | None = None,
    ) -> None:
        self.api_key = api_key
        self.model = model
        self._transport = transport or urllib_transport

    def generate(self, request: LlmRequest, timeout_s: float) -> str:
        if not self.api_key:
            raise TransportFailure("ANTHROPIC_API_KEY não está definida.")
        body: dict[str, Any] = {
            "model": self.model,
            "max_tokens": 800,
            "system": request.system,
            "messages": [
                {
                    "role": "user",
                    "content": (
                        "Responda apenas com JSON deste schema:\n"
                        f"{json.dumps(request.schema, ensure_ascii=False)}\n\n"
                        f"{request.user}"
                    ),
                }
            ],
        }
        http_request = __import__("urllib.request", fromlist=["Request"]).Request(
            URL,
            data=json.dumps(body).encode("utf-8"),
            headers={
                "x-api-key": self.api_key,
                "anthropic-version": "2023-06-01",
                "content-type": "application/json",
            },
            method="POST",
        )
        status, text = self._transport(http_request, timeout_s)
        if status == 429:
            raise RateLimitFailure("Anthropic API limitou (429).")
        if status >= 400:
            raise TransportFailure(f"Anthropic API HTTP {status}: {text[:300]}")
        try:
            payload = json.loads(text)
            return payload["content"][0]["text"]
        except (KeyError, IndexError, json.JSONDecodeError, TypeError) as exc:
            raise TransportFailure("Anthropic API devolveu um corpo inesperado.") from exc
