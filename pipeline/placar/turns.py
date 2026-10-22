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
    "O que AINDA VAI acontecer ('vão ficar presos até 80 anos', 'vou acabar com') é proposta, nunca afirmacao_checavel. "
    "titulo de afirmacao_checavel deve ser AUTOCONTIDO: troque pronomes ('ele', 'isso', 'lá') pelo sujeito real, "
    "usando o contexto anterior (ex.: 'ele tem três inquéritos', dito sobre o filho → 'Lulinha é alvo de três inquéritos'; "
    "'ele está preso' sobre Vorcaro → 'Vorcaro está preso'). busca também deve nomear o sujeito real.\n"
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
    "- Use também a lista de presidentes recebida (fato fixo) para contas de anos e mandatos; "
    "faça a conta explicitamente.\n"
    "- Fonte que só REPRODUZ a fala do candidato (transcrição do debate, 'Lula disse que...') NÃO é prova; "
    "ignore-a como evidência. Mas se a fonte for uma CHECAGEM dessa mesma frase (Aos Fatos, Lupa, Fato ou Fake, "
    "Estadão Verifica, UOL Confere, Comprova), siga a classificação do checador: Verdadeiro/Fato=verdadeiro; "
    "Exagerado/Não é bem assim/Distorcido=impreciso; Falso/Fake=falso.\n"
    "- impreciso só quando o número, o período, o sujeito ou o sentido estão materialmente errados. "
    "Diferença de palavra ('golpe' x 'fraude'), arredondamento e ressalvas que não mudam o núcleo = verdadeiro.\n"
    "- Se a fonte traz o mesmo fato com data ou número diferente do dito, é impreciso (ou falso se muito longe), não sem_dados.\n"
    "- Julgue o que o candidato quis dizer, com o sujeito real indicado no resumo e no contexto do turno.\n"
    "motivo: 1 ou 2 frases citando o dado da fonte, com números corretos. fonte_url deve ser uma das URLs recebidas."
)

SYSTEM_VERIFY = (
    SYSTEM_JUDGE_TURN
    + "\nVocê é o segundo checador e julga de forma independente; outro modelo já opinou, "
    "mas você não sabe o que ele disse. Seja rigoroso: falso e impreciso exigem dado na fonte. "
    "Refaça toda conta de anos, porcentagens e valores passo a passo antes de decidir; o seu motivo "
    "é o que será publicado, então ele precisa estar correto e completo (ex.: incluir o mandato atual)."
)

# Fatos de referência que o modelo erra sem ajuda (ex.: "PT governou 20 dos últimos 24
# anos": o juiz contou só 2003-2016 e esqueceu 2023-hoje). Vão no prompt do juiz e do
# confirmador. Datas oficiais de posse/saída.
MANDATOS = (
    ("Fernando Henrique Cardoso", "PSDB", 1995, 2002),
    ("Lula", "PT", 2003, 2010),
    ("Dilma Rousseff", "PT", 2011, 2016),  # afastada em maio/2016, impeachment em ago/2016
    ("Michel Temer", "MDB", 2016, 2018),
    ("Jair Bolsonaro", "PL", 2019, 2022),
    ("Lula", "PT", 2023, None),
)


def reference_facts(today=None) -> str:
    import datetime as _dt

    today = today or _dt.date.today()
    rows = []
    for nome, partido, ini, fim in MANDATOS:
        rows.append(f"{nome} ({partido}): {ini}–{fim if fim else 'hoje (' + str(today.year) + ')'}")
    pt_years = sum(((fim or today.year) - ini + 1) for _, partido, ini, fim in MANDATOS if partido == "PT")
    return (
        f"Data de hoje: {today.isoformat()}. Presidentes desde 1995 (fato fixo, use para contas de período):\n- "
        + "\n- ".join(rows)
        + f"\nAnos civis com o PT na Presidência de 2003 até {today.year}: cerca de {pt_years - 1} "
        "(Dilma saiu em 2016; 2016 conta pela metade)."
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


import os as _os

from placar.claim_bank import ClaimBank

_BANK: ClaimBank | None = None


def claim_bank() -> ClaimBank:
    """PLACAR_BANK=0 desliga (para medir a precisão sem o banco)."""
    global _BANK
    if _BANK is None:
        _BANK = ClaimBank.load() if _os.environ.get("PLACAR_BANK", "1") != "0" else ClaimBank([])
    return _BANK


def _now_v(turn: dict[str, Any]) -> float | None:
    """Segundo do vídeo/áudio 'agora': clock = (perf_counter de referência, segundo do áudio nele, velocidade)."""
    clock = turn.get("clock")
    if not clock:
        return None
    wall, audio_s, speed = clock
    return round(audio_s + (time.perf_counter() - wall) * (speed or 1), 1)


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
                user=(f"Candidato: {board.nomes[quem]}\n"
                      + (f"Contexto imediatamente antes (outras falas, só para entender pronomes e tema):\n{turn['antes']}\n"
                         if turn.get("antes") else "")
                      + f"Turno:\n{text}"),
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
                claim["_turno"] = text[-700:]
                claim["_job"] = turn
                va = _now_v(turn)
                if va is not None:
                    claim["va"] = va
                    if turn.get("end_v") is not None:
                        claim["lat"] = round(va - turn["end_v"], 1)
                claim["_antes"] = (turn.get("antes") or "")[-400:]
                claims.append((claim, item))
        board.note_score()
    on_change()
    for claim, item in claims:
        _judge(board, claim, item, llm, retriever, lock, res, can_call)
        on_change()
    return res


def _judge(board, claim, item, llm, retriever, lock, res, can_call) -> None:
    try:
        _judge_inner(board, claim, item, llm, retriever, lock, res, can_call)
    finally:
        vv = _now_v(claim.get("_job") or {})
        if vv is not None and claim.get("vv") is None:
            claim["vv"] = vv


def _judge_inner(board, claim, item, llm, retriever, lock, res, can_call) -> None:
    hit = claim_bank().match(board.nomes.get(claim["quem"], ""), claim["afirmacao"], claim["literal"])
    if hit:
        with lock:
            board.set_verdict(claim, veredito=hit["veredito"], motivo=hit["motivo"],
                              fonte_titulo=hit["fonte"], fonte_url=hit["url"])
            claim["banco"] = hit["fonte"]
            board.note_score()
        res.verdicts.append({"titulo": claim["afirmacao"], "veredito": hit["veredito"], "banco": hit["frase"],
                             "score": hit["score"], "publicado": claim["veredito"]})
        return
    started = time.perf_counter()
    evidence = []
    seen: set[str] = set()
    for query in claim_queries(item):
        for e in retriever.search(query):
            if e.url not in seen:
                seen.add(e.url)
                evidence.append(e)
        if len(evidence) >= 6:
            break
    evidence = evidence[:6]
    res.retrieve_ms.append((time.perf_counter() - started) * 1000)
    if not evidence:
        with lock:
            board.set_verdict(claim, veredito="sem_dados", motivo="Nenhuma fonte confiável encontrada na busca.")
        res.verdicts.append({"titulo": claim["afirmacao"], "veredito": "sem_dados", "fontes": 0})
        return
    if not can_call():
        return  # fica em revisão
    sources = "\n".join(f"- {e.titulo} ({e.url}): {e.trecho}" for e in evidence)
    prompt = reference_facts() + f"\nCandidato: {board.nomes.get(claim['quem'], '')}.\n" + \
        (f"Contexto do turno: {claim.get('_turno', '')}\n" if claim.get('_turno') else "") + \
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
        disagree = second.provider == judged.provider or v2 not in ("falso", "impreciso")
    if disagree:
        # Desempate: terceiro voto (o juiz principal de novo, com o prompt do confirmador).
        third = None
        if can_call():
            try:
                third = llm.complete(LlmRequest(task="judge", system=SYSTEM_VERIFY, user=prompt, schema=JUDGE_SCHEMA),
                                     exclude={second.provider})
            except ProviderError:
                third = None
        v3 = third.data["veredito"] if third else None
        entry.update(tiebreak=third.provider if third else None, tiebreak_veredito=v3)
        with lock:
            if v3 is not None and v3 == v2 and v2 not in ("falso", "impreciso"):
                # 2 de 3 dizem que não há erro: publica (verdadeiro ou sem_dados).
                board.set_verdict(claim, veredito=v2, motivo=second.data.get("motivo") or "",
                                  fonte_titulo=title, fonte_url=url)
                entry["publicado"] = v2
            elif v3 in ("falso", "impreciso") and v3 == verdict:
                # 2 de 3 confirmam o erro, mas o confirmador independente não: fica em revisão (regra conservadora)
                claim["motivo"] = DIVERGE_TEXT
                entry["publicado"] = "em_revisao"
            else:
                claim["motivo"] = DIVERGE_TEXT
                entry["publicado"] = "em_revisao"
            board.note_score()
        return
    with lock:
        final = verdict if v2 == verdict else "impreciso"  # discordam no grau: o mais brando
        # O motivo publicado é o do confirmador, que refez as contas.
        motivo = second.data.get("motivo") or motivo
        board.set_verdict(claim, veredito=final, motivo=motivo, fonte_titulo=title, fonte_url=url)
        board.note_score()
        entry["publicado"] = final


LEGAL_WORDS = ("lei", "emenda", "constitui", "pec", "artigo", "decreto", "medida provisória",
               "stf", "supremo", "congresso", "câmara", "senado", "aprovad", "sancion", "projeto")


def claim_queries(item: dict[str, Any]) -> list[str]:
    """Várias consultas por afirmação: a do modelo, a citação literal e, para
    lei/Constituição/Congresso, uma voltada às fontes oficiais (Planalto, Câmara,
    Senado, Agência Senado/Câmara). No teste de 21/10 metade dos 'sem dados' eram
    afirmações legais em que a busca única só trouxe o texto genérico."""
    busca = (item.get("busca") or "").strip()
    quote = " ".join((item.get("citacao") or "").split())[:160]
    queries = [q for q in (busca, quote) if q]
    if busca:
        queries.append(f"{busca} checagem fato")  # checadores costumam ter o dado exato
    folded = f"{busca} {quote}".lower()
    if any(w in folded for w in LEGAL_WORDS):
        base = busca or quote
        queries.append(f"{base} planalto.gov.br OR camara.leg.br OR senado.leg.br")
        queries.append(f"{base} agência senado câmara notícias")
    out: list[str] = []
    for q in queries:
        if q.lower() not in {x.lower() for x in out}:
            out.append(q)
    return out[:4]


def _pick_source(data, evidence):
    url = data.get("fonte_url") or ""
    if url not in {e.url for e in evidence}:
        return evidence[0].titulo, evidence[0].url
    return data.get("fonte_titulo") or next(e.titulo for e in evidence if e.url == url), url
