"""Confere se a página citada de fato traz o dado que sustenta o veredito.

Regras (precisão acima de cobertura):
- verdadeiro: os números da afirmação aparecem na página (ou, sem números, >= 60% das
  palavras de conteúdo da afirmação);
- falso/impreciso: algum número do motivo que NÃO é o número dito pelo candidato aparece
  na página (o dado correto), ou, sem números, >= 60% das palavras do motivo;
- página que só reproduz a fala (8 palavras seguidas da citação) não vale, exceto checadores.
Se a página não abre, usa o trecho da busca.
"""

from __future__ import annotations

import html as htmllib
import re
import urllib.request
from functools import lru_cache
from urllib.parse import urlparse

from placar.claim_bank import _fold, numbers, stems

FACTCHECKERS = ("aosfatos.org", "lupa.uol.com.br", "lupa.news", "estadao.com.br/estadao-verifica", "oglobo.globo.com/fato-ou-fake",
                "g1.globo.com/fato-ou-fake", "noticias.uol.com.br/confere", "projetocomprova.com.br", "oglobo.globo.com/google/amp/fato-ou-fake")


@lru_cache(maxsize=256)
def fetch_text(url: str, timeout_s: float = 5.0) -> str:
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0 (placar-pipeline)", "Accept-Language": "pt-BR"})
        with urllib.request.urlopen(req, timeout=timeout_s) as resp:  # noqa: S310 - URL de fonte da busca
            raw = resp.read(1_500_000).decode(resp.headers.get_content_charset() or "utf-8", "replace")
    except Exception:  # noqa: BLE001
        return ""
    raw = re.sub(r"(?is)<(script|style|noscript)[^>]*>.*?</\1>", " ", raw)
    return re.sub(r"\s+", " ", htmllib.unescape(re.sub(r"<[^>]+>", " ", raw)))


def _num_in(n: str, page_nums: set[str]) -> bool:
    return n in page_nums or n.replace(",", ".") in page_nums


def is_factchecker(url: str) -> bool:
    return any(f in url for f in FACTCHECKERS)


def circular(literal: str, page: str, url: str) -> bool:
    if is_factchecker(url):
        return False
    words = re.findall(r"[a-z0-9]+", _fold(literal))
    folded = " ".join(re.findall(r"[a-z0-9]+", _fold(page)))
    for i in range(0, max(0, len(words) - 7)):
        if " ".join(words[i:i + 8]) in folded:
            return True
    return False


def supports(*, veredito: str, literal: str, afirmacao: str, motivo: str, url: str, snippet: str = "",
             fetch=None) -> tuple[bool, str]:
    if veredito not in ("verdadeiro", "falso", "impreciso"):
        return True, "não se aplica"
    if not urlparse(url).scheme.startswith("http"):
        return False, "sem URL"
    page = (fetch or FETCH)(url) or ""
    text = f"{page} {snippet}"
    if not text.strip():
        return False, "página vazia"
    if circular(literal, page, url):
        return False, "fonte só reproduz a fala"
    page_nums, page_stems = numbers(text), stems(text)
    said = numbers(f"{literal} {afirmacao}")
    if veredito == "verdadeiro":
        if said:
            ok = all(_num_in(n, page_nums) for n in said if len(n) < 5 or n.startswith(("19", "20")))
            return ok, "números da fala na fonte" if ok else "número da fala não está na fonte"
        need = stems(afirmacao)
    else:
        right = {n for n in numbers(motivo) if n not in said}
        if right:
            ok = any(_num_in(n, page_nums) for n in right)
            return ok, "dado correto na fonte" if ok else "dado do motivo não está na fonte"
        need = stems(motivo)
    if not need:
        return False, "nada para conferir"
    share = len(need & page_stems) / len(need)
    return share >= 0.6, f"palavras na fonte {share:.0%}"


FETCH = fetch_text  # testes trocam por um falso
