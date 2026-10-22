"""Provedores fictícios para o replay de demonstração e para os testes."""

from __future__ import annotations

import json

from placar.llm.base import LlmRequest
from placar.llm.router import ProviderRouter


def scripted(request: LlmRequest) -> str:
    if request.task == "classify_turn":
        return _turn(request.user)
    text = request.user.lower()
    if request.task == "classify":
        if "350" in text:
            return json.dumps(
                {
                    "tipo": "afirmacao_checavel",
                    "tema": "gastos do governo",
                    "afirmacao": "O governo gastou mais de 350 bilhões de reais para se reeleger.",
                    "contexto": "Fala sobre gastos e reeleição.",
                },
                ensure_ascii=False,
            )
        if "creche" in text:
            return json.dumps(
                {
                    "tipo": "proposta",
                    "tema": "creche",
                    "titulo": "Ampliar vagas em creche",
                    "explicacao": "Ampliar as vagas em creche em todo o país.",
                },
                ensure_ascii=False,
            )
        if "mente toda vez" in text:
            return json.dumps(
                {
                    "tipo": "ataque",
                    "tema": "conduta",
                    "resumo": "Acusou o adversário de mentir o tempo todo.",
                },
                ensure_ascii=False,
            )
        if "infla" in text:
            return json.dumps(
                {
                    "tipo": "afirmacao_checavel",
                    "tema": "inflação",
                    "afirmacao": "A inflação deste ano está em 2 por cento.",
                    "contexto": "Comparação com o índice oficial.",
                },
                ensure_ascii=False,
            )
        return json.dumps(
            {"tipo": "defesa", "tema": "salário mínimo", "tom": "defesa"},
            ensure_ascii=False,
        )
    if request.task == "verify" and "infla" in text:
        return json.dumps(
            {
                "veredito": "verdadeiro",
                "motivo": "O segundo modelo não encontrou exagero.",
                "fonte_titulo": "IBGE ilustrativo",
                "fonte_url": "https://exemplo.com/ibge",
            },
            ensure_ascii=False,
        )
    if "350" in text:
        return json.dumps(
            {
                "veredito": "falso",
                "motivo": "Série ilustrativa: o número citado não é gasto direto.",
                "fonte_titulo": "Série ilustrativa",
                "fonte_url": "https://exemplo.com/gastometro",
            },
            ensure_ascii=False,
        )
    if "infla" in text:
        return json.dumps(
            {
                "veredito": "impreciso",
                "motivo": "Série ilustrativa: o índice oficial do período é outro.",
                "fonte_titulo": "IBGE ilustrativo",
                "fonte_url": "https://exemplo.com/ibge",
            },
            ensure_ascii=False,
        )
    return json.dumps(
        {"veredito": "sem_dados", "motivo": "Sem fonte na série ilustrativa."},
        ensure_ascii=False,
    )


class ScriptedProvider:
    def __init__(self, name: str, *, fail_substring: str = "") -> None:
        self.name = name
        self.fail_substring = fail_substring

    def generate(self, request: LlmRequest, timeout_s: float) -> str:
        if (
            self.fail_substring
            and self.fail_substring in request.user
            and request.task == "classify"
        ):
            return "nao e json"
        return scripted(request)


def mock_router() -> ProviderRouter:
    return ProviderRouter(
        [
            ScriptedProvider("mock-claude", fail_substring="mente toda vez"),
            ScriptedProvider("mock-openrouter"),
        ],
        retries=1,
        breaker_threshold=5,
        timeout_s=5,
    )


def _turn(user: str) -> str:
    """Turno fictício: acha frases com 'vou' (proposta) e com número (afirmação)."""
    import re

    text = user.split("Turno:", 1)[-1]
    itens = []
    for frase in re.split(r"(?<=[.!?])\s+", text):
        f = frase.strip()
        if not f:
            continue
        if re.search(r"\bvou\b|\bvamos\b", f):
            itens.append({"tipo": "proposta", "titulo": f[:40], "citacao": f, "categoria": "outro"})
        elif re.search(r"\d", f):
            itens.append({"tipo": "afirmacao_checavel", "titulo": f[:40], "citacao": f,
                          "categoria": "outro", "busca": f[:80]})
    return json.dumps({"tom": "proposta" if itens else "outro", "itens": itens[:4]}, ensure_ascii=False)
