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


# --- Captura sturdier: yt-dlp -> stdout -> ffmpeg -> PCM 16 kHz ---------------
# O caminho antigo (yt-dlp -g + ffmpeg na URL do googlevideo) leva 403 do
# YouTube com frequência. Aqui o próprio yt-dlp baixa (com os cabeçalhos e
# desafios certos) e entrega os bytes num pipe; o ffmpeg só decodifica.
# Alternativas sem YouTube: feed de TV/rádio (Rádio Bandeirantes, BandNews FM
# têm stream HTTP/Icecast), placa de captura HDMI ou o áudio do sistema; todas
# entram com `ffmpeg -i <fonte>` no lugar do yt-dlp (veja --source).

SAMPLE_RATE = 16000
BYTES_PER_S = SAMPLE_RATE * 2  # s16le mono


def ytdlp_pipe_args(page_url: str, start_s: float = 0.0) -> list[str]:
    args = ["yt-dlp", "-q", "--no-playlist", "-f", "ba/b", "-o", "-"]
    if start_s > 0:
        args += ["--download-sections", f"*{start_s:.0f}-inf"]
    return args + [page_url]


def ffmpeg_pcm_args(source: str = "pipe:0") -> list[str]:
    return ["ffmpeg", "-hide_banner", "-loglevel", "error", "-i", source,
            "-ac", "1", "-ar", str(SAMPLE_RATE), "-f", "s16le", "pipe:1"]


def stream_pcm(page_url: str = "", *, source: str = "", start_s: float = 0.0,
               retries: int = 5, backoff_s: float = 2.0, popen=None, sleep=None):
    """Gera blocos de bytes PCM. Reabre a captura até `retries` vezes se cair.

    `source` (URL de rádio/TV, arquivo, dispositivo) pula o yt-dlp.
    Em VOD a reconexão retoma do ponto já lido; em ao vivo, da borda ao vivo.
    """
    import time as _time

    popen = popen or subprocess.Popen
    sleep = sleep or _time.sleep
    read_bytes = 0
    failures = 0
    while True:
        offset = start_s + read_bytes / BYTES_PER_S
        if source:
            procs = [popen(ffmpeg_pcm_args(source), stdout=subprocess.PIPE, stderr=subprocess.DEVNULL)]
        else:
            yt = popen(ytdlp_pipe_args(page_url, offset), stdout=subprocess.PIPE, stderr=subprocess.DEVNULL)
            ff = popen(ffmpeg_pcm_args(), stdin=yt.stdout, stdout=subprocess.PIPE, stderr=subprocess.DEVNULL)
            procs = [yt, ff]
        out = procs[-1].stdout
        got = False
        while True:
            block = out.read(BYTES_PER_S)
            if not block:
                break
            got = True
            failures = 0
            read_bytes += len(block)
            yield block
        codes = [p.wait() for p in procs]
        if all(c == 0 for c in codes) and got:
            return  # fim normal (VOD acabou)
        failures += 1
        if failures > retries:
            raise RuntimeError(f"captura caiu {failures} vezes seguidas (códigos {codes}).")
        sleep(backoff_s * failures)


def windows_from_stream(blocks, *, chunk_s: float = 10.0, overlap_s: float = 2.0):
    """Recorta o PCM contínuo em janelas (início_s, bytes) com sobreposição."""
    size = int(chunk_s * BYTES_PER_S)
    step = int((chunk_s - overlap_s) * BYTES_PER_S)
    buf = b""
    start = 0
    for block in blocks:
        buf += block
        while len(buf) >= size:
            yield start / BYTES_PER_S, buf[:size]
            buf = buf[step:]
            start += step
    if len(buf) > int(overlap_s * BYTES_PER_S):
        yield start / BYTES_PER_S, buf
