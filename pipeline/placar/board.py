"""Monta o placar.json no formato que o app Flutter já lê, e a fita de eventos."""

from __future__ import annotations

import time
from typing import Any

from placar.scoring import VEREDICTS_ON_BOARD

TOM_KEYS = ("proposta", "ataque", "defesa", "balanco", "outro")


def _tempo() -> dict[str, float]:
    return {key: 0.0 for key in TOM_KEYS}


DECIDED = ("verdadeiro", "impreciso", "falso")
NO_SOURCE_TEXT = "Sem dados: nenhuma fonte verificável sustenta um veredito; não publicamos opinião."
# Não são fonte verificável de fato: redes sociais, vídeo, agregadores e páginas de busca.
BAD_SOURCE_HOSTS = ("youtube.com", "youtu.be", "facebook.com", "instagram.com", "tiktok.com", "twitter.com",
                    "x.com", "t.me", "whatsapp.com", "kwai.com", "threads.net", "reddit.com", "google.com/search",
                    "bing.com", "duckduckgo.com", "brainly.com.br", "pinterest.com")


def _host(url: str) -> str:
    from urllib.parse import urlparse
    return (urlparse(url).hostname or "").removeprefix("www.")


def source_ok(src: Any) -> bool:
    """Fonte = dict com url http(s) real (host com ponto) fora da lista de não-fontes."""
    if not isinstance(src, dict):
        return False
    url = str(src.get("url") or "").strip()
    if not url.startswith(("http://", "https://")) or " " in url:
        return False
    host = _host(url)
    if "." not in host or host in ("localhost", "example.com"):
        return False
    low = url.lower()
    return not any(b in low.split("?")[0] if "/" in b else (host == b or host.endswith("." + b))
                   for b in BAD_SOURCE_HOSTS)


class Board:
    def __init__(
        self,
        *,
        debate_id: str,
        candidatos: dict[str, str],
        origin_ms: int,
        video: dict[str, Any] | None = None,
        aviso: str = "",
        clock_ms: Any = None,
    ) -> None:
        self.debate_id = debate_id
        self.nomes = dict(candidatos)
        self.origin_ms = origin_ms
        self.video = video or {
            "id": "",
            "ao_vivo": True,
            "inicio": 0,
            "t0": origin_ms,
            "comeco": origin_ms,
        }
        self.aviso = aviso
        self._clock_ms = clock_ms or (lambda: int(time.time() * 1000))
        self.tempo = {slot: _tempo() for slot in candidatos}
        self.claims: list[dict[str, Any]] = []
        self.propostas: list[dict[str, Any]] = []
        self.ataques: list[dict[str, Any]] = []
        self.linha: dict[str, dict[str, int]] = {}
        self.events: list[dict[str, Any]] = []
        self.seq = 0
        self.pausado = False
        self.encerrado: dict[str, str] | None = None

    def add_time(self, quem: str, tom: str, seconds: float) -> None:
        bucket = self.tempo.setdefault(quem, _tempo())
        key = tom if tom in TOM_KEYS else "outro"
        bucket[key] = round(bucket[key] + max(0.0, seconds), 3)

    def add_attack(self, *, quem: str, resumo: str, t_ms: int) -> None:
        self.ataques.insert(0, {"quem": quem, "resumo": resumo, "t": t_ms})
        self._bump(t_ms, f"a{quem}")
        self._emit(
            "ataque.created",
            t_ms,
            quem,
            {"resumo": resumo},
        )

    def add_proposal(
        self, *, quem: str, titulo: str, explicacao: str, t_ms: int
    ) -> None:
        title = titulo.strip()
        for item in self.propostas:
            if item["quem"] == quem and item["titulo"] == title:
                item["vezes"] += 1
                item["t"] = t_ms
                if explicacao.strip():
                    item["explicacao"] = explicacao.strip()
                self._bump(t_ms, f"p{quem}")
                self._emit(
                    "proposta.incremented",
                    t_ms,
                    quem,
                    {"titulo": title, "vezes": item["vezes"]},
                )
                return
        self.propostas.append(
            {
                "quem": quem,
                "titulo": title,
                "explicacao": explicacao.strip(),
                "vezes": 1,
                "t": t_ms,
            }
        )
        self._bump(t_ms, f"p{quem}")
        self._emit(
            "proposta.created",
            t_ms,
            quem,
            {"titulo": title, "explicacao": explicacao.strip()},
        )

    def open_claim(
        self,
        *,
        quem: str,
        tema: str,
        afirmacao: str,
        contexto: str,
        literal: str,
        t_ms: int,
    ) -> dict[str, Any]:
        claim = {
            "id": f"c{len(self.claims) + 1}",
            "t": t_ms,
            "quem": quem,
            "tema": tema.strip() or "geral",
            "afirmacao": afirmacao.strip() or literal.strip(),
            "contexto": contexto.strip(),
            "veredito": "em_revisao",
            "motivo": "Áudio e fontes ainda em conferência.",
            "fonte": None,
            "literal": literal.strip(),
            "corrigido": None,
        }
        self.claims.append(claim)
        self._emit(
            "claim.created",
            t_ms,
            quem,
            {
                "tema": claim["tema"],
                "afirmacao": claim["afirmacao"],
                "literal": claim["literal"],
                "contexto": claim["contexto"],
                "veredito": "em_revisao",
            },
        )
        return claim

    def set_verdict(
        self,
        claim: dict[str, Any],
        *,
        veredito: str,
        motivo: str,
        fonte_titulo: str = "",
        fonte_url: str = "",
    ) -> None:
        # REGRA DURA: veredito (verdadeiro/impreciso/falso) só sai com fonte verificável.
        # Sem URL http(s) de fonte aceitável -> sem_dados. Nunca publica opinião do modelo.
        if veredito in DECIDED:
            src = {"titulo": fonte_titulo, "url": fonte_url} if fonte_url else claim.get("fonte")
            if not source_ok(src):
                veredito, motivo = "sem_dados", NO_SOURCE_TEXT
                fonte_titulo = fonte_url = ""
                claim["fonte"] = None
            elif not fonte_titulo and src:
                fonte_titulo = src.get("titulo") or _host(src.get("url") or "")
                fonte_url = src.get("url") or ""
        previous = claim["veredito"]
        if previous != "em_revisao" and previous != veredito:
            claim["corrigido"] = {"antes": previous}
        claim["veredito"] = veredito
        claim["motivo"] = motivo
        if fonte_titulo and fonte_url.startswith(("http://", "https://")):
            claim["fonte"] = {"titulo": fonte_titulo, "url": fonte_url}
        self._emit(
            "claim.updated",
            claim["t"],
            claim["quem"],
            {
                "tema": claim["tema"],
                "afirmacao": claim["afirmacao"],
                "veredito": veredito,
                "motivo": motivo,
                "fonte": claim["fonte"],
                "corrigido": claim["corrigido"],
            },
        )

    def finish(self, *, proximo: str = "", texto: str = "") -> None:
        for claim in self.claims:
            if claim["veredito"] == "em_revisao":
                self.set_verdict(claim, veredito="sem_dados",
                                 motivo="Sem confirmação: não deu tempo de checar com fontes durante o debate.")
        self.video = {**self.video, "ao_vivo": False}
        if proximo and texto:
            self.encerrado = {"proximo": proximo, "texto": texto}
        self._emit(
            "debate.status",
            self._clock_ms(),
            "",
            {"ao_vivo": False, "encerrado": self.encerrado},
        )

    def snapshot(self) -> dict[str, Any]:
        grouped: dict[str, list[dict[str, Any]]] = {}
        for claim in self.claims:
            grouped.setdefault(claim["tema"], []).append(claim)
        fatos = []
        for tema, items in grouped.items():
            fatos.append(
                {
                    "tema": tema,
                    "atualizado": max(item["t"] for item in items),
                    "declaracoes": [_public_claim(item) for item in items],
                }
            )
        counts = _counts(self.claims)
        candidatos = {}
        for slot, nome in self.nomes.items():
            tally = counts.get(slot, {})
            propostas = sum(
                item["vezes"] for item in self.propostas if item["quem"] == slot
            )
            ataques = sum(1 for item in self.ataques if item["quem"] == slot)
            candidatos[slot] = {
                "nome": nome,
                "verdadeiro": tally.get("verdadeiro", 0),
                "impreciso": tally.get("impreciso", 0),
                "falso": tally.get("falso", 0),
                "sem_dados": tally.get("sem_dados", 0),
                "propostas": propostas,
                "ataques": ataques,
                "tempo": dict(self.tempo.get(slot, _tempo())),
            }
        body: dict[str, Any] = {
            "atualizado": self._clock_ms(),
            "video": self.video,
            "candidatos": candidatos,
            "fatos": fatos,
            "propostas": list(self.propostas),
            "ataques": list(self.ataques),
            "linha": self.linha,
            "pausado": self.pausado,
        }
        if self.aviso:
            body["aviso"] = self.aviso
        if self.encerrado:
            body["encerrado"] = self.encerrado
        return body

    def note_score(self) -> None:
        snap = self.snapshot()
        self._emit(
            "score.updated",
            snap["atualizado"],
            "",
            {
                "candidatos": {
                    slot: {
                        "verdadeiro": row["verdadeiro"],
                        "impreciso": row["impreciso"],
                        "falso": row["falso"],
                        "sem_dados": row["sem_dados"],
                    }
                    for slot, row in snap["candidatos"].items()
                }
            },
        )

    def _bump(self, t_ms: int, key: str) -> None:
        minute = max(0, (t_ms - self.origin_ms) // 60000)
        bucket = self.linha.setdefault(str(minute), {})
        bucket[key] = bucket.get(key, 0) + 1

    def _emit(self, kind: str, t_ms: int, quem: str, payload: dict[str, Any]) -> None:
        self.seq += 1
        event: dict[str, Any] = {
            "v": 1,
            "debate_id": self.debate_id,
            "seq": self.seq,
            "t": t_ms,
            "type": kind,
            "payload": payload,
        }
        if quem:
            event["quem"] = quem
        self.events.append(event)


def _public_claim(claim: dict[str, Any]) -> dict[str, Any]:
    body = {
        "id": claim.get("id", ""),
        "t": claim["t"],
        "quem": claim["quem"],
        "afirmacao": claim["afirmacao"],
        "contexto": claim["contexto"],
        "veredito": claim["veredito"],
        "motivo": claim["motivo"],
        "literal": claim["literal"],
    }
    if claim.get("fonte"):
        body["fonte"] = claim["fonte"]
    if claim.get("corrigido"):
        body["corrigido"] = claim["corrigido"]
    for key in ("va", "vv", "lat", "banco"):
        if claim.get(key) is not None:
            body[key] = claim[key]
    return body


def _counts(claims: list[dict[str, Any]]) -> dict[str, dict[str, int]]:
    out: dict[str, dict[str, int]] = {}
    for claim in claims:
        verdict = claim["veredito"]
        if verdict not in VEREDICTS_ON_BOARD and verdict != "sem_dados":
            continue
        slot = out.setdefault(
            claim["quem"],
            {"verdadeiro": 0, "impreciso": 0, "falso": 0, "sem_dados": 0},
        )
        slot[verdict] = slot.get(verdict, 0) + 1
    return out
