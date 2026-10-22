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

SYSTEM_TURN = (
    "Você analisa um turno de fala de um candidato em debate presidencial no Brasil "
    "(transcrição automática: pode ter erros de palavra, ignore-os). Devolva a LISTA de itens.\n"
    "Tipos (escolha com cuidado, um item por ideia):\n"
    "- proposta: promessa do PRÓPRIO candidato para o futuro ('vou', 'vamos', 'meu governo vai'). "
    "Promessa NUNCA é afirmacao_checavel, mesmo com número ('vou construir 500 mil vagas' = proposta).\n"
    "- ataque: crítica direta ao adversário, ao governo ou ao partido dele, sem número verificável.\n"
    "- afirmacao_checavel: fato do PASSADO ou PRESENTE com número, data, lei ou ato de governo "
    "que um checador confere em fonte pública ('o PIB cresceu 7,5% em 2010', 'o PT governou 20 dos "
    "últimos 24 anos'). Opinião, adjetivo e comparação vaga ('fizemos mais que todos') NÃO são.\n"
    "Um ataque com número verificável vira afirmacao_checavel.\n"
    "Campos: titulo = frase curta e clara em português (até 8 palavras) que diga o conteúdo, "
    "ex. 'PIB cresceu 10,5% em 2010'; citacao = trecho EXATO copiado do texto, a menor frase "
    "que sustenta o item; categoria = tema real (seguranca, economia, saude, educacao, social, "
    "meio_ambiente, corrupcao, politica, infraestrutura, outro); busca (só afirmacao_checavel) = "
    "consulta de 4 a 10 palavras como um jornalista digitaria no buscador, com o número, o ano e o "
    "assunto, sem o nome do candidato (ex. 'PIB Brasil 2010 crescimento IBGE').\n"
    "Não invente nada que não esteja no texto. Saudação, regra do debate e retórica vazia não viram item. "
    "Lista vazia é válida. tom = tipo dominante do turno (proposta, ataque, defesa, balanco, outro); "
    "balanco = o candidato fala do que o próprio governo fez; defesa = responde a acusação."
)

SYSTEM_JUDGE_TURN = (
    "Você é checador de fatos. Julgue a afirmação de um candidato usando SÓ as fontes recebidas "
    "(títulos e trechos). Regras:\n"
    "- verdadeiro: as fontes confirmam o núcleo (número e período); arredondamento pequeno é ok.\n"
    "- impreciso: tem base mas exagera, troca período/indicador ou tira de contexto.\n"
    "- falso: as fontes contradizem claramente.\n"
    "- sem_dados: as fontes não tratam do ponto. Na dúvida, sem_dados. Não use conhecimento próprio "
    "para contradizer sem fonte.\n"
    "motivo: 1 ou 2 frases citando o dado da fonte. fonte_url deve ser uma das URLs recebidas."
)

SYSTEM_VERIFY = (
    SYSTEM_JUDGE_TURN
    + "\nVocê é o segundo checador e julga de forma independente; outro modelo já opinou, "
    "mas você não sabe o que ele disse. Seja rigoroso: falso e impreciso exigem dado na fonte."
)

REVIEW_TEXT = "Em revisão: aguardando um segundo modelo confirmar com as fontes."
DIVERGE_TEXT = "Em revisão: os checadores automáticos não chegaram a acordo; fica fora do Mentirômetro."


@dataclass
class TurnResult:
    classify_ms: float = 0.0
    retrieve_ms: list[float] = field(default_factory=list)
    judge_ms: list[float] = field(default_factory=list)
    verify_ms: list[float] = field(default_factory=list)
    verdicts: list[dict[str, Any]] = field(default_factory=list)
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
    if not evidence and item.get("busca"):
        evidence = retriever.search(item["citacao"][:160])
    res.retrieve_ms.append((time.perf_counter() - started) * 1000)
    if not evidence:
        with lock:
            board.set_verdict(claim, veredito="sem_dados", motivo="Nenhuma fonte confiável encontrada na busca.")
        res.verdicts.append({"titulo": claim["afirmacao"], "veredito": "sem_dados", "fontes": 0})
        return
    if not can_call():
        return  # fica em revisão
    sources = "\n".join(f"- {e.titulo} ({e.url}): {e.trecho}" for e in evidence)
    import datetime as _dt

    hoje = _dt.date.today().isoformat()
    prompt = (f"Data de hoje: {hoje}. Candidato: {board.nomes.get(claim['quem'], '')}. "
              "Considere o período até hoje (ex.: 'últimos 24 anos' conta até o ano atual).\n") + \
        f"Afirmação (literal): {claim['literal']}\nResumo: {claim['afirmacao']}\nFontes:\n{sources}"
    started = time.perf_counter()
    try:
        judged = llm.complete(LlmRequest(task="judge", system=SYSTEM_JUDGE_TURN, user=prompt, schema=JUDGE_SCHEMA))
    except ProviderError:
        res.judge_ms.append((time.perf_counter() - started) * 1000)
        return
    res.judge_ms.append((time.perf_counter() - started) * 1000)
    verdict = judged.data["veredito"]
    title, url = _pick_source(judged.data, evidence)
    motivo = judged.data.get("motivo") or ""
    entry = {"titulo": claim["afirmacao"], "veredito": verdict, "fontes": len(evidence),
             "judge": judged.provider, "url": url}
    res.verdicts.append(entry)
    if verdict not in ("falso", "impreciso"):
        with lock:
            board.set_verdict(claim, veredito=verdict, motivo=motivo, fonte_titulo=title, fonte_url=url)
            board.note_score()
        return
    # Falso/impreciso: só publica se um SEGUNDO provedor, cego ao primeiro, concordar.
    with lock:
        claim["motivo"] = REVIEW_TEXT
        claim["fonte"] = {"titulo": title, "url": url}
        claim["_primeiro"] = {"veredito": verdict, "provider": judged.provider}
        board.note_score()
    if not can_call():
        return
    order = getattr(llm, "verify_order", None) or None
    started = time.perf_counter()
    try:
        second = llm.complete(LlmRequest(task="verify", system=SYSTEM_VERIFY, user=prompt, schema=JUDGE_SCHEMA),
                              exclude={judged.provider}, prefer=order)
    except ProviderError as exc:
        res.verify_ms.append((time.perf_counter() - started) * 1000)
        entry["verify"] = f"erro: {exc.message[:80]}"
        return
    res.verify_ms.append((time.perf_counter() - started) * 1000)
    v2 = second.data["veredito"]
    entry.update(verify=second.provider, verify_veredito=v2)
    with lock:
        if second.provider == judged.provider or v2 not in ("falso", "impreciso"):
            claim["motivo"] = DIVERGE_TEXT
            board.note_score()
            entry["publicado"] = "em_revisao"
            return
        final = verdict if v2 == verdict else "impreciso"  # discordam no grau: o mais brando
        if final != verdict:
            motivo = second.data.get("motivo") or motivo
        board.set_verdict(claim, veredito=final, motivo=motivo, fonte_titulo=title, fonte_url=url)
        board.note_score()
        entry["publicado"] = final


def _pick_source(data, evidence):
    url = data.get("fonte_url") or ""
    if url not in {e.url for e in evidence}:
        return evidence[0].titulo, evidence[0].url
    return data.get("fonte_titulo") or next(e.titulo for e in evidence if e.url == url), url
