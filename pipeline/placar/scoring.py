"""Mentirômetro. A mesma conta do app Flutter e do site.

Falso vale 1, impreciso vale 0,5. Sem dados e em revisão ficam de fora.
O ponteiro só sai do centro com pelo menos 3 fatos checáveis de cada lado.
Ângulo = (erro da direita − erro da esquerda) × 90. Diferença < 0,1 é empate.
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from enum import Enum

MINIMO = 3

VEREDICTS_ON_BOARD = ("verdadeiro", "impreciso", "falso")


def js_round(value: float) -> int:
    """Math.round / Dart .round() para valores que o placar usa (não negativos)."""
    if value >= 0:
        return int(math.floor(value + 0.5))
    return int(math.ceil(value - 0.5))


@dataclass(frozen=True)
class ErrorIndex:
    total: int
    verdadeiro_pct: int
    impreciso_pct: int
    falso_pct: int
    erro: float

    @property
    def erro_pct(self) -> int:
        return js_round(self.erro * 100)


def error_index(*, verdadeiro: int, impreciso: int, falso: int) -> ErrorIndex:
    total = verdadeiro + impreciso + falso
    if total == 0:
        return ErrorIndex(0, 0, 0, 0, 0.0)

    def pct(count: int) -> int:
        return js_round(count / total * 100)

    erro = (falso + impreciso / 2) / total
    return ErrorIndex(total, pct(verdadeiro), pct(impreciso), pct(falso), erro)


class NeedleCall(str, Enum):
    waiting = "waiting"
    tie = "tie"
    left = "left"
    right = "right"


@dataclass(frozen=True)
class Reading:
    left: ErrorIndex
    right: ErrorIndex
    ready: bool
    angle_degrees: float
    call: NeedleCall
    headline: str
    detail: str
    basis: str


def mentiromentro(
    *,
    left_name: str,
    right_name: str,
    left_verdadeiro: int,
    left_impreciso: int,
    left_falso: int,
    right_verdadeiro: int,
    right_impreciso: int,
    right_falso: int,
) -> Reading:
    left = error_index(
        verdadeiro=left_verdadeiro, impreciso=left_impreciso, falso=left_falso
    )
    right = error_index(
        verdadeiro=right_verdadeiro, impreciso=right_impreciso, falso=right_falso
    )
    ready = left.total >= MINIMO and right.total >= MINIMO
    angle = (right.erro - left.erro) * 90 if ready else 0.0
    diff = abs(left.erro - right.erro)
    if not ready:
        call = NeedleCall.waiting
        headline = "Esperando mais fatos"
        detail = (
            "o ponteiro só se mexe com pelo menos "
            f"{MINIMO} fatos checáveis de cada lado"
        )
    elif diff < 0.1:
        call = NeedleCall.tie
        headline = "Empate técnico"
        detail = "os dois erram parecido até agora"
    elif left.erro > right.erro:
        call = NeedleCall.left
        headline = f"{left_name} está errando mais"
        detail = f"{left.erro_pct}% contra {right.erro_pct}% de índice de erro"
    else:
        call = NeedleCall.right
        headline = f"{right_name} está errando mais"
        detail = f"{right.erro_pct}% contra {left.erro_pct}% de índice de erro"
    left_word = "fato checável" if left.total == 1 else "fatos checáveis"
    basis = (
        f"com base em {left.total} {left_word} de {left_name} "
        f"e {right.total} de {right_name} (sem dados fica de fora)"
    )
    return Reading(left, right, ready, angle, call, headline, detail, basis)
