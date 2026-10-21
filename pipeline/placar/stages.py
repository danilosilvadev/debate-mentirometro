"""Uma fala: classificar, publicar, checar, só então fechar falso ou impreciso."""

from __future__ import annotations

import time
from dataclasses import dataclass, field
from typing import Any

from placar.board import Board
from placar.llm.base import LlmRequest, ProviderError
from placar.llm.router import ProviderRouter
from placar.retrieve import Retriever
from placar.schemas import CLASSIFY_SCHEMA, JUDGE_SCHEMA

SYSTEM_CLASSIFY = (
    "Você separa falas de debate eleitoral no Brasil. "
    "proposta = compromisso concreto. ataque = golpe no adversário. "
    "afirmacao_checavel = número, dado ou ato de governo que dá para conferir. "
    "defesa = resposta a uma acusação. balanco = fala sobre o passado do próprio governo. "
    "outro = opinião, saudação ou retórica. Não invente citação."
)

SYSTEM_JUDGE = (
    "Você julga uma afirmação de debate só com as fontes recebidas. "
    "verdadeiro = os dados confirmam. impreciso = exagerado ou fora de contexto. "
    "falso = os dados contradizem. sem_dados = não deu para verificar. "
    "Não use em_revisao. Cite a fonte que pesou mais."
)


@dataclass
class StageTiming:
    classify_ms: float = 0.0
    retrieve_ms: float = 0.0
    judge_ms: float = 0.0
    verify_ms: float = 0.0
    providers: list[str] = field(default_factory=list)


def process_utterance(
    board: Board,
    utterance: dict[str, Any],
    llm: ProviderRouter,
    retriever: Retriever,
) -> StageTiming:
    timing = StageTiming()
    text = str(utterance.get("text") or "").strip()
    quem = str(utterance.get("quem") or "other")
    t_ms = int(utterance["t_ms"])
    dur_s = float(utterance.get("dur_s") or 0)
    if not text or quem not in board.nomes:
        if quem in board.nomes and dur_s:
            board.add_time(quem, "outro", dur_s)
        return timing

    started = time.perf_counter()
    try:
        classified = llm.complete(
            LlmRequest(
                task="classify",
                system=SYSTEM_CLASSIFY,
                user=f"Candidato {quem} ({board.nomes[quem]}) disse: {text}",
                schema=CLASSIFY_SCHEMA,
            )
        )
    except ProviderError:
        board.add_time(quem, "outro", dur_s)
        timing.classify_ms = (time.perf_counter() - started) * 1000
        return timing
    timing.classify_ms = (time.perf_counter() - started) * 1000
    timing.providers.append(classified.provider)
    data = classified.data
    tipo = data["tipo"]
    tom = data.get("tom") or _tom_of(tipo)
    board.add_time(quem, tom, dur_s)

    if tipo == "proposta":
        board.add_proposal(
            quem=quem,
            titulo=data.get("titulo") or data.get("tema") or text[:80],
            explicacao=data.get("explicacao") or text,
            t_ms=t_ms,
        )
    elif tipo == "ataque":
        board.add_attack(
            quem=quem,
            resumo=data.get("resumo") or text[:180],
            t_ms=t_ms,
        )
    elif tipo == "afirmacao_checavel":
        _check_claim(board, llm, retriever, utterance, data, timing)
    board.note_score()
    return timing


def _check_claim(
    board: Board,
    llm: ProviderRouter,
    retriever: Retriever,
    utterance: dict[str, Any],
    classified: dict[str, Any],
    timing: StageTiming,
) -> None:
    quem = str(utterance["quem"])
    t_ms = int(utterance["t_ms"])
    literal = str(utterance.get("text") or "")
    claim = board.open_claim(
        quem=quem,
        tema=classified.get("tema") or "geral",
        afirmacao=classified.get("afirmacao") or literal,
        contexto=classified.get("contexto") or "",
        literal=literal,
        t_ms=t_ms,
    )
    started = time.perf_counter()
    evidence = retriever.search(claim["afirmacao"])
    timing.retrieve_ms = (time.perf_counter() - started) * 1000
    evidence_text = "\n".join(
        f"- {item.titulo} ({item.url}): {item.trecho}" for item in evidence
    ) or "Nenhuma fonte encontrada."
    started = time.perf_counter()
    try:
        judged = llm.complete(
            LlmRequest(
                task="judge",
                system=SYSTEM_JUDGE,
                user=(
                    f"Afirmação: {claim['afirmacao']}\n"
                    f"Contexto: {claim['contexto']}\n"
                    f"Fontes:\n{evidence_text}"
                ),
                schema=JUDGE_SCHEMA,
            )
        )
    except ProviderError:
        timing.judge_ms = (time.perf_counter() - started) * 1000
        return
    timing.judge_ms = (time.perf_counter() - started) * 1000
    timing.providers.append(judged.provider)
    verdict = judged.data["veredito"]
    if verdict in ("falso", "impreciso"):
        started = time.perf_counter()
        try:
            second = llm.complete(
                LlmRequest(
                    task="verify",
                    system=SYSTEM_JUDGE
                    + " Você é o segundo modelo. Confirme ou corrija o veredito.",
                    user=(
                        f"Um modelo marcou como {verdict}. "
                        f"Motivo: {judged.data.get('motivo', '')}\n"
                        f"Afirmação: {claim['afirmacao']}\nFontes:\n{evidence_text}"
                    ),
                    schema=JUDGE_SCHEMA,
                ),
                exclude={judged.provider},
            )
        except ProviderError:
            timing.verify_ms = (time.perf_counter() - started) * 1000
            return
        timing.verify_ms = (time.perf_counter() - started) * 1000
        timing.providers.append(second.provider)
        if second.provider == judged.provider or second.data["veredito"] != verdict:
            claim["motivo"] = (
                "Em revisão: o segundo modelo não confirmou o veredito "
                f"({second.data['veredito']})."
            )
            return
        board.set_verdict(
            claim,
            veredito=verdict,
            motivo=judged.data.get("motivo") or "",
            fonte_titulo=judged.data.get("fonte_titulo") or "",
            fonte_url=judged.data.get("fonte_url") or "",
        )
        return
    board.set_verdict(
        claim,
        veredito=verdict,
        motivo=judged.data.get("motivo") or "",
        fonte_titulo=judged.data.get("fonte_titulo") or "",
        fonte_url=judged.data.get("fonte_url") or "",
    )


def _tom_of(tipo: str) -> str:
    if tipo in ("proposta", "ataque", "defesa", "balanco"):
        return tipo
    return "outro"
