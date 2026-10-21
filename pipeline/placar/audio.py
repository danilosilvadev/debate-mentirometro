"""Áudio: yt-dlp + ffmpeg em janelas de 10 s com 2 s de sobreposição."""

from __future__ import annotations

import shutil
import subprocess
from pathlib import Path


def chunk_windows(
    duration_s: float, *, chunk_s: float = 10.0, overlap_s: float = 2.0
) -> list[tuple[float, float]]:
    if duration_s <= 0:
        return []
    step = chunk_s - overlap_s
    if step <= 0:
        raise ValueError("A sobreposição precisa ser menor que o tamanho do bloco.")
    windows: list[tuple[float, float]] = []
    start = 0.0
    while start < duration_s - 1e-6:
        length = min(chunk_s, duration_s - start)
        windows.append((round(start, 3), round(length, 3)))
        if start + length >= duration_s - 1e-6:
            break
        start += step
    return windows


def ytdlp_url_args(page_url: str) -> list[str]:
    return ["yt-dlp", "-g", "-f", "ba/b", "--no-playlist", page_url]


def ffmpeg_chunk_args(
    source: str, dest: str, *, start_s: float, duration_s: float
) -> list[str]:
    return [
        "ffmpeg",
        "-hide_banner",
        "-loglevel",
        "error",
        "-ss",
        f"{start_s:.3f}",
        "-t",
        f"{duration_s:.3f}",
        "-i",
        source,
        "-ac",
        "1",
        "-ar",
        "16000",
        "-y",
        dest,
    ]


def resolve_audio_url(page_url: str) -> str:
    if shutil.which("yt-dlp") is None:
        raise RuntimeError("yt-dlp não está instalado.")
    completed = subprocess.run(
        ytdlp_url_args(page_url),
        check=False,
        capture_output=True,
        text=True,
    )
    if completed.returncode != 0:
        raise RuntimeError(completed.stderr.strip() or "yt-dlp falhou.")
    url = completed.stdout.strip().splitlines()[-1]
    if not url:
        raise RuntimeError("yt-dlp não devolveu uma URL de áudio.")
    return url


def cut_chunk(
    source: str, dest: Path, *, start_s: float, duration_s: float
) -> Path:
    if shutil.which("ffmpeg") is None:
        raise RuntimeError("ffmpeg não está instalado.")
    dest.parent.mkdir(parents=True, exist_ok=True)
    completed = subprocess.run(
        ffmpeg_chunk_args(source, str(dest), start_s=start_s, duration_s=duration_s),
        check=False,
        capture_output=True,
        text=True,
    )
    if completed.returncode != 0:
        raise RuntimeError(completed.stderr.strip() or "ffmpeg falhou.")
    return dest
