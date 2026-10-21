"""API direta do Gemini. Só entra na cadeia se GEMINI_API_KEY existir."""

from __future__ import annotations

import json
from urllib.request import Request

from placar.llm.base import LlmRequest, RateLimitFailure, TransportFailure
from placar.llm.openrouter import Transport, urllib_transport


class GeminiProvider:
    name = "gemini"

    def __init__(
        self,
        *,
        api_key: str,
        model: str = "gemini-2.5-flash-lite",
        transport: Transport | None = None,
    ) -> None:
        self.api_key = api_key
        self.model = model
        self._transport = transport or urllib_transport

    def generate(self, request: LlmRequest, timeout_s: float) -> str:
        if not self.api_key:
            raise TransportFailure("GEMINI_API_KEY não está definida.")
        url = (
            "https://generativelanguage.googleapis.com/v1beta/models/"
            f"{self.model}:generateContent?key={self.api_key}"
        )
        body = {
            "systemInstruction": {"parts": [{"text": request.system}]},
            "contents": [
                {
                    "role": "user",
                    "parts": [
                        {
                            "text": (
                                "Responda apenas com JSON deste schema:\n"
                                f"{json.dumps(request.schema, ensure_ascii=False)}\n\n"
                                f"{request.user}"
                            )
                        }
                    ],
                }
            ],
            "generationConfig": {
                "temperature": 0,
                "responseMimeType": "application/json",
            },
        }
        http_request = Request(
            url,
            data=json.dumps(body).encode("utf-8"),
            headers={"content-type": "application/json"},
            method="POST",
        )
        status, text = self._transport(http_request, timeout_s)
        if status == 429:
            raise RateLimitFailure("Gemini limitou (429).")
        if status >= 400:
            raise TransportFailure(f"Gemini HTTP {status}: {text[:300]}")
        try:
            payload = json.loads(text)
            return payload["candidates"][0]["content"]["parts"][0]["text"]
        except (KeyError, IndexError, json.JSONDecodeError, TypeError) as exc:
            raise TransportFailure("Gemini devolveu um corpo inesperado.") from exc
