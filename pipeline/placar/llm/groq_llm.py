"""LLM hospedado na Groq (API compatível com OpenAI), com a mesma GROQ_API_KEY do STT.

Conferido em 21/10/2026 na lista /openai/v1/models da conta: `openai/gpt-oss-120b`
(aceita json_schema strict, ~0,5 s por chamada) e `qwen/qwen3.8-27b` (outra família,
~0,2 s). O pipeline usa o primeiro como fallback rápido do Claude CLI e o segundo
como modelo que confirma falso/impreciso.
"""

from __future__ import annotations

from placar.llm.openrouter import OpenRouterProvider

GROQ_CHAT_URL = "https://api.groq.com/openai/v1/chat/completions"


class GroqLlmProvider(OpenRouterProvider):
    def __init__(self, *, api_key: str, model: str, name: str = "groq", transport=None) -> None:
        import os
        # Plano gratuito: 8000 tokens/min por modelo. O roteador espaça as chamadas abaixo disso.
        self.tpm = int(os.environ.get("GROQ_TPM", "7000"))
        super().__init__(api_key=api_key, model=model, transport=transport, url=GROQ_CHAT_URL,
                         name=name, label=f"Groq {model}", key_env="GROQ_API_KEY")
        # Na Groq, strict exige todos os campos em required; nossos schemas têm opcionais.
        self.strict_schema = False
