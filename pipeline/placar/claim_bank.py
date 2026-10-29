"""Banco de afirmações já checadas (checadores profissionais + audit interno).

Casamento local, sem LLM (não gasta cota): palavras de conteúdo normalizadas
(sem acento, radical de 5 letras) e números. Todos os números da entrada do banco
precisam aparecer na fala; e pelo menos `min_overlap` das palavras de conteúdo.
"""

from __future__ import annotations

import json
import re
import unicodedata
from pathlib import Path
from typing import Any

BANK_PATH = Path(__file__).parent / "data" / "claim_bank.json"
STOP = set("""a o os as um uma uns umas de do da dos das em no na nos nas por para pra com sem que e ou se
eu ele ela eles elas voce nos meu minha seu sua dele dela isso esse essa este esta aqui la ja nao sim foi era
sao ser ter tem tinha mais menos muito quando como mas ao aos pelo pela pelos pelas so ate entre sobre""".split())


def _fold(text: str) -> str:
    text = unicodedata.normalize("NFKD", text.lower())
    return "".join(c for c in text if not unicodedata.combining(c))


WORDNUM = {"um": "1", "dois": "2", "duas": "2", "tres": "3", "quatro": "4", "cinco": "5", "seis": "6", "sete": "7",
           "oito": "8", "nove": "9", "dez": "10", "onze": "11", "doze": "12", "vinte": "20", "trinta": "30"}


def numbers(text: str) -> set[str]:
    folded = _fold(text).replace("e meio", ",5")
    folded = re.sub(r"\b(" + "|".join(WORDNUM) + r")\b", lambda m: WORDNUM[m.group(1)], folded)
    return {n.replace(".", "").rstrip(",") for n in re.findall(r"\d+(?:[.,]\d+)*", folded)}


def stems(text: str) -> set[str]:
    words = re.findall(r"[a-z]+", _fold(text))
    return {w[:5] for w in words if w not in STOP and len(w) > 2}


class ClaimBank:
    def __init__(self, items: list[dict[str, Any]], *, min_overlap: float = 0.6) -> None:
        self.items = items
        self.min_overlap = min_overlap

    @classmethod
    def load(cls, path: Path | None = None) -> "ClaimBank":
        path = path or BANK_PATH
        if not path.exists():
            return cls([])
        return cls(json.loads(path.read_text(encoding="utf-8")).get("itens") or [])

    def match(self, speaker: str, *texts: str) -> dict[str, Any] | None:
        joined = " ".join(t for t in texts if t)
        have_words, have_nums = stems(joined), numbers(joined)
        who = _fold(speaker)
        best, best_score = None, 0.0
        for item in self.items:
            if item.get("quem") and item["quem"] not in who:
                continue
            need = set(item.get("numeros") or [])
            if need and not need <= have_nums:
                continue
            words = stems(item["frase"]) - {w[:5] for w in need}
            words = {w for w in words if not w.isdigit()}
            if not words:
                continue
            score = len(words & have_words) / len(words)
            limit = self.min_overlap - 0.15 if need else self.min_overlap  # números iguais já são forte indício
            if score >= limit and score > best_score:
                best, best_score = item, score
        return {**best, "score": round(best_score, 2)} if best else None
