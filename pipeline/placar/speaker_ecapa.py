"""Embedding de voz ECAPA (speechbrain, CPU). Mesmo modelo de scripts/enroll_voice.py."""

from __future__ import annotations

from pathlib import Path

import numpy as np

_MODEL = None


def embed(audio: np.ndarray) -> np.ndarray:
    global _MODEL
    import torch
    if _MODEL is None:
        from speechbrain.inference.speaker import EncoderClassifier
        _MODEL = EncoderClassifier.from_hparams(
            source="speechbrain/spkrec-ecapa-voxceleb",
            savedir=str(Path.home() / ".cache/placar/ecapa"),
            run_opts={"device": "cpu"},
        )
    with torch.no_grad():
        vec = _MODEL.encode_batch(torch.from_numpy(np.ascontiguousarray(audio)).unsqueeze(0)).squeeze().numpy()
    return vec / (np.linalg.norm(vec) + 1e-9)
