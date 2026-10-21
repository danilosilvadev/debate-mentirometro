"""Quem fala: cosseno entre o embedding do trecho e duas amostras de voz."""

from __future__ import annotations

import math


def cosine(left: list[float], right: list[float]) -> float:
    if len(left) != len(right) or not left:
        return 0.0
    dot = sum(a * b for a, b in zip(left, right))
    norm_l = math.sqrt(sum(a * a for a in left))
    norm_r = math.sqrt(sum(b * b for b in right))
    if norm_l == 0 or norm_r == 0:
        return 0.0
    return dot / (norm_l * norm_r)


def match_speaker(
    embedding: list[float] | None,
    enrolled: dict[str, list[float]],
    *,
    threshold: float = 0.55,
    fallback: str = "other",
) -> str:
    """Devolve o id do candidato (`1`/`2`) ou `other` (mediador, plateia)."""
    if not embedding or not enrolled:
        return fallback
    best_id = fallback
    best = threshold
    for slot, sample in enrolled.items():
        score = cosine(embedding, sample)
        if score >= best:
            best = score
            best_id = slot
    return best_id
