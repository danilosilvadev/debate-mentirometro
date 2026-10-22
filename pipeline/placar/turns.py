"""Turno de fala -> lista de itens (uma chamada) -> busca -> julgamento.

Pensado para rodar num worker (placar.worker): nada aqui segura o laço de
áudio. Toda escrita no Board passa por `lock`.
"""

from __future__ import annotations

import threading
import time
from dataclasses import dataclass, field
from typing import Any, Callable

from placar.board import Board
from placar.llm.base import LlmRequest, ProviderError
from placar.llm.router import ProviderRouter
from placar.retrieve import Retriever
from placar.schemas import JUDGE_SCHEMA, TURN_SCHEMA
from placar.stages import SYSTEM_JUDGE

SYSTEM_TURN = (
    "Você analisa um turno de fala de um candidato em debate presidencial no Brasil "
    "(transcrição automática, pode ter erros). Devolva a LISTA de itens do turno:\n"
    "- proposta: compromisso concreto do próprio candidato para o futuro ('vou', 'vamos criar').\n"
    "- ataque: crítica direta ao adversário ou ao governo/partido dele.\n"
    "- afirmacao_checavel: número, dado, data ou ato de governo verificável em fonte pública.\n"
    "Cada item: titulo curto (até 8 palavras, em português, sem underline), citacao EXATA "
    "copiada do texto (a menor frase que sustenta o item), categoria, e para "
    "afirmacao_checavel um campo busca com palavras-chave para pesquisar. "
    "Não invente nada que não esteja no texto. Saudações e retórica vazia não viram item. "
    "Lista vazia é válida. tom = o tipo dominante do turno (proposta, ataque, defesa, balanco, outro)."
)


@dataclass
class TurnResult:
    classify_ms: float = 0.0
    retrieve_ms: list[float] = field(default_factory=list)
    judge_ms: list[float] = field(default_factory=list)
    items: int = 0
    error: str = ""


def process_turn(
    board: Board,
    turn: dict[str, Any],
    llm: ProviderRouter,
    retriever: Retriever,
    *,
    lock: threading.Lock | None = None,
    on_change: Callable[[], None] = lambda: None,
    max_claims: int = 2,
    can_call: Callable[[], bool] = lambda: True,
) -> TurnResult:
    lock = lock or threading.Lock()
    res = TurnResult()
    quem, text, t_ms = str(turn["quem"]), str(turn["text"]).strip(), int(turn["t_ms"])
    dur_s = float(turn.get("dur_s") or 0)
    if quem not in board.nomes or not text:
        return res
    if not can_call():
        with lock:
            board.add_time(quem, "outro", dur_s)
        res.error = "orçamento de chamadas esgotado"
        return res
    started = time.perf_counter()
    try:
        out = llm.complete(
            LlmRequest(
                task="classify_turn",
                system=SYSTEM_TURN,
                user=f"Candidato: {board.nomes[quem]}\nTurno:\n{text}",
                schema=TURN_SCHEMA,
            )
        )
    except ProviderError as exc:
        res.classify_ms = (time.perf_counter() - started) * 1000
        res.error = exc.message
        with lock:
            board.add_time(quem, "outro", dur_s)
        on_change()
        return res
    res.classify_ms = (time.perf_counter() - started) * 1000
    data = out.data
    items = data.get("itens") or []
    res.items = len(items)
    claims = []
    with lock:
        board.add_time(quem, data.get("tom") or "outro", dur_s)
        for item in items:
            quote = item["citacao"].strip()
            if item["tipo"] == "proposta":
                board.add_proposal(quem=quem, titulo=item["titulo"], explicacao=quote, t_ms=t_ms)
            elif item["tipo"] == "ataque":
                board.add_attack(quem=quem, resumo=f"{item['titulo']}: “{quote}”", t_ms=t_ms)
            elif len(claims) < max_claims:
                claim = board.open_claim(
                    quem=quem, tema=item["categoria"], afirmacao=item["titulo"],
                    contexto=item.get("busca") or "", literal=quote, t_ms=t_ms,
                )
                claims.append((claim, item))
        board.note_score()
    on_change()
    for claim, item in claims:
        _judge(board, claim, item, llm, retriever, lock, res, can_call)
        on_change()
    return res


def _judge(board, claim, item, llm, retriever, lock, res, can_call) -> None:
    query = item.get("busca") or item["citacao"]
    started = time.perf_counter()
    evidence = retriever.search(query)
    res.retrieve_ms.append((time.perf_counter() - started) * 1000)
    if not evidence:
        with lock:
            board.set_verdict(claim, veredito="sem_dados", motivo="Nenhuma fonte confiável encontrada na busca.")
        return
    if not can_call():
        return  # fica em revisão
    sources = "\n".join(f"- {e.titulo} ({e.url}): {e.trecho}" for e in evidence)
    started = time.perf_counter()
    try:
        judged = llm.complete(
            LlmRequest(
                task="judge",
                system=SYSTEM_JUDGE + " fonte_url deve ser uma das URLs recebidas.",
                user=f"Afirmação (literal): {claim['literal']}\nResumo: {claim['afirmacao']}\nFontes:\n{sources}",
                schema=JUDGE_SCHEMA,
            )
        )
    except ProviderError:
        res.judge_ms.append((time.perf_counter() - started) * 1000)
        return
    res.judge_ms.append((time.perf_counter() - started) * 1000)
    verdict = judged.data["veredito"]
    url = judged.data.get("fonte_url") or ""
    if url not in {e.url for e in evidence}:
        url, title = evidence[0].url, evidence[0].titulo
    else:
        title = judged.data.get("fonte_titulo") or next(e.titulo for e in evidence if e.url == url)
    with lock:
        if verdict in ("falso", "impreciso"):
            # Regra do pipeline: falso/impreciso só com segundo provedor. Sem ele, fica em revisão.
            claim["motivo"] = f"Em revisão: primeiro modelo marcou {verdict}. {judged.data.get('motivo', '')}"
            claim["fonte"] = {"titulo": title, "url": url}
            board.note_score()
            return
        board.set_verdict(claim, veredito=verdict, motivo=judged.data.get("motivo") or "",
                          fonte_titulo=title, fonte_url=url)
        board.note_score()
