"""Replay de áudio gravado em tempo real: blocos de 10 s -> whisper -> voz -> LLM -> placar.json.

Simula o ao vivo: o bloco [s, s+10] só é processado quando o relógio
de parede chega a s+10 (dividido pela velocidade). Mede atraso por etapa.
"""

from __future__ import annotations

import json
import time
from pathlib import Path
from typing import Any

import numpy as np

from placar.audio import chunk_windows, cut_chunk
from placar.board import Board
from placar.llm.router import ProviderRouter
from placar.retrieve import Retriever
from placar.stages import process_utterance
from placar.transcribe import FasterWhisperTranscriber, dedupe_overlap


def load_profiles(voices: Path, names: list[str]) -> dict[str, np.ndarray]:
    return {n: np.load(voices / f"{n}.npy") for n in names if (voices / f"{n}.npy").exists()}


def label(vec: np.ndarray, profiles: dict[str, np.ndarray], threshold: float) -> tuple[str, dict[str, float]]:
    scores = {n: round(float(vec @ p), 3) for n, p in profiles.items()}
    best = max(scores, key=scores.get) if scores else "unknown"
    return (best if scores and scores[best] >= threshold else "unknown"), scores


def run(
    wav: Path,
    *,
    out: Path,
    router: ProviderRouter,
    retriever: Retriever,
    candidatos: dict[str, str],          # slot -> nome exibido
    slot_of_voice: dict[str, str],       # perfil de voz -> slot ("1","2") ou "other"
    voices: Path,
    whisper_model: str = "small",
    speed: float = 1.0,
    threshold: float = 0.35,
    chunk_s: float = 10.0,
    overlap_s: float = 2.0,
    debate_id: str = "teste-dev",
    video_id: str = "",
    transcriber: Any = None,
    offset_s: float = 0.0,
    turn_max_s: float = 45.0,
    max_llm_calls: int = 0,
) -> dict[str, Any]:
    """turn_max_s: junta segmentos seguidos do mesmo candidato num turno
    (uma chamada de classificação por turno, não por frase). max_llm_calls:
    teto de chamadas do roteador (0 = sem teto); estourou, só conta tempo."""
    import soundfile as sf
    from placar.speaker_ecapa import embed  # noqa: carregamento preguiçoso do torch

    duration = sf.info(str(wav)).duration
    profiles = load_profiles(voices, list(slot_of_voice))
    stt = transcriber or FasterWhisperTranscriber(model_name=whisper_model)
    if isinstance(stt, FasterWhisperTranscriber):
        stt.transcribe(_silence(out))  # aquece o modelo fora do relógio
    embed(np.zeros(16000, dtype="float32"))
    origin = int(time.time() * 1000)
    board = Board(debate_id=debate_id, candidatos=candidatos, origin_ms=origin,
                  video={"id": video_id, "ao_vivo": True, "inicio": 0, "t0": origin, "comeco": origin},
                  aviso="Teste em modo dev. Não é o placar publicado.")
    out.mkdir(parents=True, exist_ok=True)
    transcript, chunks = [], []
    wall0 = time.perf_counter()
    last_voice = "unknown"
    prev_tail = ""
    turn: dict[str, Any] | None = None
    llm_turns: list[dict[str, Any]] = []
    budget_hit = False

    def flush() -> float:
        nonlocal turn, budget_hit
        if not turn:
            return 0.0
        t0 = time.perf_counter()
        calls_before = len([r for r in router.history if r.ok or r.error])
        if max_llm_calls and calls_before >= max_llm_calls:
            budget_hit = True
            if turn["slot"] in board.nomes:
                board.add_time(turn["slot"], "outro", turn["dur_s"])
        else:
            process_utterance(board, {"t_ms": origin + int(turn["t_s"] * 1000), "quem": turn["slot"],
                                      "dur_s": turn["dur_s"], "text": turn["text"]}, router, retriever)
        ms = (time.perf_counter() - t0) * 1000
        if turn["slot"] in board.nomes:
            llm_turns.append({**turn, "llm_ms": round(ms), "speech_end_to_board_s": round(time.perf_counter() - wall0 - turn["end_audio_s"] / (speed or 1), 2) if speed else None})
        turn = None
        return ms
    windows = chunk_windows(duration, chunk_s=chunk_s, overlap_s=overlap_s)
    for index, (start, length) in enumerate(windows):
        ready_at = (start + length) / speed if speed > 0 else 0
        wait = ready_at - (time.perf_counter() - wall0)
        if wait > 0:
            time.sleep(wait)
        t_ready = time.perf_counter()
        c0 = time.perf_counter()
        dest = cut_chunk(str(wav), out / "chunks" / f"chunk_{index:04d}.wav", start_s=start, duration_s=length)
        capture_ms = (time.perf_counter() - c0) * 1000
        c0 = time.perf_counter()
        segments = stt.transcribe(dest)
        stt_ms = (time.perf_counter() - c0) * 1000
        audio, _sr = sf.read(str(dest), dtype="float32")
        spk_ms = llm_ms = 0.0
        new = 0
        for seg in segments:
            # Cada bloco é dono de [início + sobreposição/2, fim - sobreposição/2]:
            # um segmento só sai no bloco que contém o seu meio. Assim a fala
            # na sobreposição de 2 s não aparece duas vezes.
            mid = (seg.start_s + seg.end_s) / 2
            own_from = overlap_s / 2 if index > 0 else -1.0
            own_to = length - overlap_s / 2 if index < len(windows) - 1 else length + 1.0
            if not (own_from <= mid < own_to):
                continue
            text = dedupe_overlap(prev_tail, seg.text) if index > 0 and seg.start_s < overlap_s + 0.5 else seg.text
            if not text:
                continue
            prev_tail = text
            new += 1
            c0 = time.perf_counter()
            piece = audio[int(seg.start_s * 16000): int(seg.end_s * 16000)]
            if len(piece) >= 16000:
                voice, scores = label(embed(piece), profiles, threshold)
            else:
                voice, scores = last_voice, {}
            last_voice = voice
            spk_ms += (time.perf_counter() - c0) * 1000
            slot = slot_of_voice.get(voice, "other")
            t_abs = start + seg.start_s
            transcript.append({"t_s": round(offset_s + t_abs, 2), "dur_s": round(seg.end_s - seg.start_s, 2),
                               "voz": voice, "slot": slot, "scores": scores, "text": text})
            if turn and (turn["slot"] != slot or turn["dur_s"] >= turn_max_s):
                llm_ms += flush()
            if turn is None:
                turn = {"t_s": t_abs, "slot": slot, "dur_s": 0.0, "text": "", "chunk": index}
            turn["dur_s"] += seg.end_s - seg.start_s
            turn["end_audio_s"] = start + seg.end_s
            turn["text"] = (turn["text"] + " " + text).strip()
        (out / "placar.json").write_text(json.dumps(board.snapshot(), ensure_ascii=False, indent=2), encoding="utf-8")
        done = time.perf_counter()
        stt_name = getattr(stt, "last_provider", "") or getattr(stt, "name", "local")
        chunks.append({"chunk": index, "stt": stt_name, "start_s": start, "len_s": length, "segments": new,
                       "capture_ms": round(capture_ms), "stt_ms": round(stt_ms), "speaker_ms": round(spk_ms),
                       "llm_ms": round(llm_ms), "delay_after_chunk_end_s": round(done - t_ready, 2),
                       "lag_vs_wallclock_s": round(done - wall0 - ready_at, 2)})
        print(json.dumps(chunks[-1]), flush=True)
    flush()
    (out / "placar.json").write_text(json.dumps(board.snapshot(), ensure_ascii=False, indent=2), encoding="utf-8")
    (out / "events.jsonl").write_text("".join(json.dumps(e, ensure_ascii=False) + "\n" for e in board.events), encoding="utf-8")
    report = {"llm_turns": llm_turns, "llm_budget_hit": budget_hit, "audio_s": duration, "whisper_model": whisper_model, "speed": speed, "chunks": chunks,
              "llm_calls": [vars(r) if hasattr(r, "__dict__") else str(r) for r in router.history]}
    (out / "transcript.json").write_text(json.dumps(transcript, ensure_ascii=False, indent=2), encoding="utf-8")
    (out / "latency_report.json").write_text(json.dumps(report, ensure_ascii=False, indent=2, default=str), encoding="utf-8")
    return report


def _silence(out: Path) -> Path:
    import soundfile as sf
    out.mkdir(parents=True, exist_ok=True)
    p = out / "_warm.wav"
    sf.write(str(p), np.zeros(16000, dtype="float32"), 16000)
    return p
