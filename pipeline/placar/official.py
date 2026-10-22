"""Dados oficiais (fonte primária) para afirmações com número: IBGE SIDRA e Banco Central SGS.

Sem LLM: palavras-chave da fala -> série oficial -> trecho com os valores dos anos citados
(e o dado mais recente). Vira uma Evidence a mais para o juiz, com a URL da própria API.
Falha de rede = lista vazia (nunca bloqueia a checagem)."""

from __future__ import annotations

import json
import re
import threading
import time
import urllib.request
from typing import Any

from placar.claim_bank import _fold
from placar.retrieve import Evidence

_CACHE: dict[str, tuple[float, Any]] = {}
_LOCK = threading.Lock()
TTL_S = 6 * 3600


def _get(url: str, timeout_s: float = 6.0) -> Any:
    with _LOCK:
        hit = _CACHE.get(url)
        if hit and time.time() - hit[0] < TTL_S:
            return hit[1]
    req = urllib.request.Request(url, headers={"User-Agent": "placar-debate/1.0"})
    with urllib.request.urlopen(req, timeout=timeout_s) as r:
        data = json.loads(r.read().decode("utf-8"))
    with _LOCK:
        _CACHE[url] = (time.time(), data)
    return data


def _sidra(table: int, var: int, period: str) -> list[tuple[str, str]]:
    rows = _get(f"https://apisidra.ibge.gov.br/values/t/{table}/n1/all/v/{var}/p/{period}")
    return [(r["D3N"], r["V"]) for r in rows[1:] if r.get("V") not in (None, "", "...", "-")]


def _sgs(code: int, years: list[int]) -> list[tuple[str, str]]:
    """Série inteira desde 1999 numa chamada (cache de 6 h); último valor + dezembro dos anos pedidos."""
    rows = []
    for a, b in ((1999, 2008), (2009, 2018), (2019, time.gmtime().tm_year)):  # séries diárias: janela máx. 10 anos
        rows += _get(f"https://api.bcb.gov.br/dados/serie/bcdata.sgs.{code}/dados?formato=json"
                     f"&dataInicial=01/01/{a}&dataFinal=31/12/{b}", timeout_s=15.0)
    if not rows:
        return []
    out = [(f"último ({rows[-1]['data']})", rows[-1]["valor"])]
    for y in years:
        dec = [x for x in rows if x["data"].endswith(f"/12/{y}")]
        if dec:
            out.append((f"dez/{y}", dec[-1]["valor"]))
    return out


def warm() -> None:
    """Chamar no início da transmissão: baixa as séries antes da primeira fala."""
    for code in (432, 3546, 13761, 13762):
        try:
            _sgs(code, [])
        except Exception:  # noqa: BLE001
            pass


def _br(v: str, unit: str = "") -> str:
    out = v.replace(".", ",")
    if "milhões" in unit:
        x = float(v) * 1e6
        word, div = ("trilhões", 1e12) if x >= 1e12 else ("bilhões", 1e9)
        out += f" (≈ {x / div:.1f} {word})".replace(".", ",")
    return out


# (palavras, rótulo, função(anos) -> linhas, url pública, unidade)
def _pib(years):
    per = ",".join(str(y) for y in years) if years else "last%203"
    return _sidra(6784, 9810, per)


def _ipca(years):
    rows = _sidra(1737, 2265, "last%201")
    if years:
        rows += _sidra(1737, 69, ",".join(f"{y}12" for y in years))
    return rows


def _desemprego(years):
    rows = _sidra(6381, 4099, "last%201")
    ys = [y for y in years if y >= 2012]
    if ys:
        rows += _sidra(6381, 4099, ",".join(f"{y}12" for y in ys))
    return rows


INDICATORS = [
    (("pib", "economia cresceu", "pais cresceu", "crescimento economico", "cresceu "),
     "IBGE/SIDRA tabela 6784 — PIB, variação real anual (%)", _pib,
     "https://sidra.ibge.gov.br/tabela/6784", "%"),
    (("ipca", "inflacao"), "IBGE/SIDRA tabela 1737 — IPCA (%; 12 meses no último mês; no ano em dezembro)", _ipca,
     "https://sidra.ibge.gov.br/tabela/1737", "%"),
    (("desemprego", "desocupa", "desempregad"), "IBGE/SIDRA tabela 6381 — PNAD Contínua, taxa de desocupação (%)",
     _desemprego, "https://sidra.ibge.gov.br/tabela/6381", "%"),
    (("selic", "taxa de juros", "juros basic"), "Banco Central/SGS 432 — meta Selic (% a.a.)",
     lambda ys: _sgs(432, ys), "https://api.bcb.gov.br/dados/serie/bcdata.sgs.432/dados?formato=json", "% a.a."),
    (("reserva",), "Banco Central/SGS 13621/3546 — reservas internacionais (US$ milhões)",
     lambda ys: _sgs(3546, ys), "https://api.bcb.gov.br/dados/serie/bcdata.sgs.3546/dados?formato=json",
     "US$ milhões"),
    (("divida publica", "divida bruta", "endividamento", "divida do governo", "divida de"),
     "Banco Central/SGS 13761/13762 — dívida bruta do governo geral (R$ milhões; % do PIB)",
     lambda ys: [(f"{p} R$ milhões", v) for p, v in _sgs(13761, [y for y in ys if y >= 2006])]
     + [(f"{p} % do PIB", v) for p, v in _sgs(13762, [y for y in ys if y >= 2006])],
     "https://api.bcb.gov.br/dados/serie/bcdata.sgs.13761/dados?formato=json", ""),
]


def official_evidence(text: str, *, max_items: int = 2) -> list[Evidence]:
    folded = _fold(text)
    if not re.search(r"\d|milh|bilh|trilh|por cento", folded):
        return []
    years = sorted({int(y) for y in re.findall(r"\b(19[89]\d|20[0-3]\d)\b", folded)})[:4]
    # sem ano dito: fim de cada mandato (comparações "quando eu cheguei/saí")
    term_ends = years or [2002, 2010, 2014, 2018, 2022]
    out = []
    for keys, label, fn, url, unit in INDICATORS:
        if "alimento" in folded and fn is _ipca:
            continue  # inflação de alimentos não é o IPCA cheio
        if not any(k in folded for k in keys):
            continue
        try:
            rows = fn(term_ends if fn not in (_pib, _ipca, _desemprego) else years)
        except Exception:  # noqa: BLE001 - fonte oficial fora do ar: segue sem ela
            continue
        if rows:
            trecho = f"{label}: " + "; ".join(f"{p}: {_br(v, unit + p)} {unit}" for p, v in rows)
            out.append(Evidence(titulo=label.split(" — ")[0] + " (dado oficial)", url=url, trecho=trecho, origem="oficial"))
        if len(out) >= max_items:
            break
    return out
