#!/usr/bin/env python3
"""Cadastra a voz de uma pessoa a partir de um trecho público do YouTube.

uso: enroll_voice.py <nome> <url> [inicio_s fim_s]

Baixa só o trecho (yt-dlp --download-sections), gera o embedding ECAPA
(speechbrain, CPU) em janelas de 3 s, e acumula em voices/<nome>.npy
(média normalizada de todos os clipes) + voices/<nome>.json com as fontes.
"""
from __future__ import annotations

import json
import subprocess
import sys
import tempfile
from pathlib import Path

import numpy as np

VOICES = Path(__file__).resolve().parents[1] / "voices"
_MODEL = None


def model():
    global _MODEL
    if _MODEL is None:
        from speechbrain.inference.speaker import EncoderClassifier
        _MODEL = EncoderClassifier.from_hparams(
            source="speechbrain/spkrec-ecapa-voxceleb",
            savedir=str(Path.home() / ".cache/placar/ecapa"),
            run_opts={"device": "cpu"},
        )
    return _MODEL


def load_wav(path: Path) -> np.ndarray:
    import soundfile as sf
    data, sr = sf.read(str(path), dtype="float32")
    if data.ndim > 1:
        data = data.mean(axis=1)
    assert sr == 16000, sr
    return data


def embed(audio: np.ndarray) -> np.ndarray:
    import torch
    with torch.no_grad():
        vec = model().encode_batch(torch.from_numpy(audio).unsqueeze(0)).squeeze().numpy()
    return vec / (np.linalg.norm(vec) + 1e-9)


def embed_windows(audio: np.ndarray, win_s: float = 3.0) -> list[np.ndarray]:
    n = int(win_s * 16000)
    out = []
    for i in range(0, len(audio) - n + 1, n):
        piece = audio[i : i + n]
        if np.sqrt((piece**2).mean()) > 0.005:  # pula silêncio
            out.append(embed(piece))
    return out


def fetch(url: str, start: float, end: float, dest: Path) -> Path:
    raw = dest.with_suffix(".raw")
    subprocess.run(
        ["yt-dlp", "-q", "--remote-components", "ejs:github", "-f", "ba/b",
         "--download-sections", f"*{start}-{end}", "-o", str(raw) + ".%(ext)s", url],
        check=True,
    )
    src = next(raw.parent.glob(raw.name + ".*"))
    subprocess.run(["ffmpeg", "-loglevel", "error", "-y", "-i", str(src), "-ac", "1",
                    "-ar", "16000", str(dest)], check=True)
    return dest


def main() -> int:
    if len(sys.argv) not in (3, 5):
        print(__doc__)
        return 2
    name, url = sys.argv[1], sys.argv[2]
    start, end = (float(sys.argv[3]), float(sys.argv[4])) if len(sys.argv) == 5 else (60.0, 105.0)
    VOICES.mkdir(exist_ok=True)
    with tempfile.TemporaryDirectory() as tmp:
        wav = fetch(url, start, end, Path(tmp) / "clip.wav")
        vecs = embed_windows(load_wav(wav))
    if not vecs:
        print("nenhuma fala no trecho")
        return 1
    clip = np.mean(vecs, axis=0)
    clip /= np.linalg.norm(clip)
    consist = float(np.mean([v @ clip for v in vecs]))
    meta_path = VOICES / f"{name}.json"
    meta = json.loads(meta_path.read_text()) if meta_path.exists() else {"name": name, "clips": []}
    meta["clips"].append({"url": url, "start_s": start, "end_s": end, "windows": len(vecs),
                          "self_consistency": round(consist, 3), "embedding": clip.round(6).tolist()})
    prof = np.mean([np.array(c["embedding"]) for c in meta["clips"]], axis=0)
    prof /= np.linalg.norm(prof)
    np.save(VOICES / f"{name}.npy", prof)
    meta_path.write_text(json.dumps(meta, ensure_ascii=False))
    others = [c for c in meta["clips"][:-1]]
    cross = [round(float(np.array(c["embedding"]) @ clip), 3) for c in others]
    if cross and min(cross) < 0.4:
        print(f"AVISO: este clipe parece outra voz (cosseno {min(cross)}). Confira e remova de voices/{name}.json.", file=sys.stderr)
    print(json.dumps({"name": name, "windows": len(vecs), "self_consistency": round(consist, 3),
                      "sim_to_previous_clips": cross}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
