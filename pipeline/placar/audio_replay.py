"""Replay de áudio gravado em tempo real: blocos de 10 s -> whisper -> voz -> LLM -> placar.json.

Simula o ao vivo: o bloco [s, s+10] só é processado quando o relógio
de parede chega a s+10 (dividido pela velocidade). Mede atraso por etapa.
"""

from __future__ import annotations

import json
import re
import time
from pathlib import Path
from typing import Any

import numpy as np

from placar.audio import chunk_windows, cut_chunk
from placar.board import Board
from placar.llm.router import ProviderRouter
from placar.retrieve import Retriever
import threading

from placar.turns import process_turn
from placar.worker import LlmWorker
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
    turn_max_s: float = 14.0,
    turn_min_s: float = 5.0,
    number_stt: Any = None,
    crosstalk_margin: float = 0.04,
    max_llm_calls: int = 0,
    llm_workers: int = int(__import__("os").environ.get("PLACAR_LLM_WORKERS", "4")),
    max_claims_per_turn: int = 3,
    chunk_source: Any = None,
    silence_flush_s: float = 3.0,
) -> dict[str, Any]:
    """turn_max_s: junta segmentos seguidos do mesmo candidato num turno
    (uma chamada de classificação por turno, não por frase). max_llm_calls:
    teto de chamadas do roteador (0 = sem teto); estourou, só conta tempo."""
    import soundfile as sf
    from placar.speaker_ecapa import embed  # noqa: carregamento preguiçoso do torch

    duration = sf.info(str(wav)).duration if chunk_source is None else 0.0
    profiles = load_profiles(voices, list(slot_of_voice))
    stt = transcriber or FasterWhisperTranscriber(model_name=whisper_model)
    if isinstance(stt, FasterWhisperTranscriber):
        stt.transcribe(_silence(out))  # aquece o modelo fora do relógio
    embed(np.zeros(16000, dtype="float32"))
    if __import__("os").environ.get("PLACAR_OFFICIAL", "1") != "0":
        from placar import official  # séries do BC/IBGE em segundo plano, antes da 1ª fala
        threading.Thread(target=official.warm, daemon=True).start()
    origin = int(time.time() * 1000)
    board = Board(debate_id=debate_id, candidatos=candidatos, origin_ms=origin,
                  video={"id": video_id, "ao_vivo": True, "inicio": 0, "t0": origin, "comeco": origin},
                  aviso="Teste em modo dev. Não é o placar publicado.")
    numfix: list[dict[str, Any]] = []
    crosstalk: list[dict[str, Any]] = []
    out.mkdir(parents=True, exist_ok=True)
    transcript, chunks = [], []
    wall0 = time.perf_counter()
    last_voice = "unknown"
    prev_tail = ""
    turn: dict[str, Any] | None = None
    llm_turns: list[dict[str, Any]] = []
    budget_hit = False

    lock = threading.Lock()
    write_lock = threading.Lock()

    def now_v() -> float:
        return round(offset_s + (time.perf_counter() - wall0) * (speed or 1), 1)

    def write_board() -> None:
        with lock:
            snap = board.snapshot()
        # vários threads escrevem (laço principal e juízes): arquivo temporário por thread
        tmp = out / f"placar.json.{threading.get_ident()}.tmp"
        tmp.write_text(json.dumps(snap, ensure_ascii=False, indent=2), encoding="utf-8")
        with write_lock:
            tmp.replace(out / "placar.json")

    def can_call() -> bool:
        nonlocal budget_hit
        used = len([r for r in router.history if r.provider != "claude-cli"])
        if max_llm_calls and used >= max_llm_calls:
            budget_hit = True
            return False
        return True

    def run_turn(job: dict[str, Any]) -> Any:
        return process_turn(board, job, router, retriever, lock=lock, on_change=write_board,
                            max_claims=max_claims_per_turn, can_call=can_call)

    worker = LlmWorker(run_turn, workers=llm_workers)

    def flush() -> float:
        nonlocal turn
        if not turn:
            return 0.0
        t0 = time.perf_counter()
        if turn["slot"] in board.nomes:
            worker.submit({"t_ms": origin + int(turn["t_s"] * 1000), "quem": turn["slot"],
                           "dur_s": turn["dur_s"], "text": turn["text"], "t_s": turn["t_s"],
                           "antes": _context_before(transcript, offset_s + turn["t_s"]),
                           "clock": turn.get("clock"), "end_v": round(offset_s + turn["end_audio_s"], 1),
                           "speech_end_wall": turn.get("end_wall", wall0 + turn["end_audio_s"] / (speed or 1))})
        turn = None
        return (time.perf_counter() - t0) * 1000

    if chunk_source is None:
        windows = chunk_windows(duration, chunk_s=chunk_s, overlap_s=overlap_s)
        last_index = len(windows) - 1

        def _file_chunks():
            for index, (start, length) in enumerate(windows):
                ready_at = (start + length) / speed if speed > 0 else 0
                wait = ready_at - (time.perf_counter() - wall0)
                if wait > 0:
                    time.sleep(wait)
                c0 = time.perf_counter()
                dest = cut_chunk(str(wav), out / "chunks" / f"chunk_{index:04d}.wav", start_s=start, duration_s=length)
                yield index, start, length, dest, ready_at, (time.perf_counter() - c0) * 1000

        source = _file_chunks()
    else:
        last_index = -1  # ao vivo: não se sabe qual é o último bloco
        source = chunk_source
    for index, start, length, dest, ready_at, capture_ms in source:
        t_ready = time.perf_counter()
        if ready_at is None:  # ao vivo: o bloco acabou de chegar
            ready_at = t_ready - wall0
        c0 = time.perf_counter()
        segments = stt.transcribe(dest)
        if number_stt is not None and any(has_number(x.text) for x in segments):
            try:
                segments, fixes = reconcile_numbers(segments, number_stt.transcribe(dest))
                for fx in fixes:
                    numfix.append({"t_s": round(offset_s + start + fx["start_s"], 1), **fx})
            except Exception as exc:  # noqa: BLE001 - segunda passada é opcional
                numfix.append({"t_s": round(offset_s + start, 1), "erro": str(exc)[:120]})
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
            own_to = length - overlap_s / 2 if index != last_index else length + 1.0
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
                # Trecho curto/ruidoso abaixo do limiar: se o mais parecido é quem
                # já estava falando, continua com ele (no teste: 6 de 147, todos certos).
                if voice == "unknown" and scores:
                    best = max(scores, key=scores.get)
                    if best == last_voice and scores[best] >= threshold - 0.15:
                        voice = best
            else:
                voice, scores = last_voice, {}
            if is_crosstalk(scores, threshold, crosstalk_margin, slot_of_voice):
                # Dois rostos de voz quase empatados: fala sobreposta. Não atribui a ninguém.
                crosstalk.append({"t_s": round(offset_s + start + seg.start_s, 1), "scores": scores, "text": text})
                transcript.append({"t_s": round(offset_s + start + seg.start_s, 2), "dur_s": round(seg.end_s - seg.start_s, 2),
                                   "voz": "sobreposta", "slot": "sobreposta", "scores": scores, "text": text})
                spk_ms += (time.perf_counter() - c0) * 1000
                continue
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
            turn["end_wall"] = t_ready  # chegada do bloco: mede atraso real mesmo se a captura atrasar
            turn["clock"] = (t_ready, offset_s + start + length, speed or 1)
            turn["text"] = (turn["text"] + " " + text).strip()
            # Frase completa e turno já com alguns segundos: manda já (afirmação em até ~15 s).
            if turn["dur_s"] >= turn_min_s and turn["text"].rstrip().endswith((".", "?", "!")):
                llm_ms += flush()
        # turno que já passou de turn_max_s, ou cuja voz calou há mais de
        # `silence_flush_s` no fim do bloco, sai sem esperar a próxima fala
        if turn and (turn["dur_s"] >= turn_max_s
                     or (start + length) - turn["end_audio_s"] >= silence_flush_s):
            llm_ms += flush()
        write_board()
        done = time.perf_counter()
        stt_name = getattr(stt, "last_provider", "") or getattr(stt, "name", "local")
        chunks.append({"chunk": index, "stt": stt_name, "start_s": start, "len_s": length, "segments": new,
                       "capture_ms": round(capture_ms), "stt_ms": round(stt_ms), "speaker_ms": round(spk_ms),
                       "llm_ms": round(llm_ms), "delay_after_chunk_end_s": round(done - t_ready, 2),
                       "lag_vs_wallclock_s": round(done - wall0 - ready_at, 2)})
        print(json.dumps(chunks[-1]), flush=True)
    flush()
    worker.drain()
    write_board()
    for item in worker.done:
        job, res = item["job"], item["result"]
        llm_turns.append({"quem": job["quem"], "t_s": round(offset_s + job["t_s"], 1), "dur_s": round(job["dur_s"], 1),
                          "queue_wait_s": item["queue_wait_s"], "run_s": item["run_s"],
                          "speech_end_to_items_s": round(item["finished_at"] - job["speech_end_wall"], 2),
                          "classify_ms": round(res.classify_ms) if res else None,
                          "retrieve_ms": [round(x) for x in res.retrieve_ms] if res else [],
                          "judge_ms": [round(x) for x in res.judge_ms] if res else [],
                          "verify_ms": [round(x) for x in res.verify_ms] if res else [],
                          "verdicts": res.verdicts if res else [],
                          "items": res.items if res else 0, "error": (res.error if res else item["error"]),
                          "text": job["text"]})
    (out / "events.jsonl").write_text("".join(json.dumps(e, ensure_ascii=False) + "\n" for e in board.events), encoding="utf-8")
    report = {"numeros_conferidos": numfix, "fala_sobreposta": crosstalk, "llm_turns": llm_turns, "llm_budget_hit": budget_hit, "audio_s": duration, "whisper_model": whisper_model, "speed": speed, "chunks": chunks,
              "retrieval_requests": getattr(getattr(retriever, "_ddg", None), "requests", 0),
              "searx_requests": getattr(retriever, "searx_requests", 0),
              "searx_failures": getattr(retriever, "searx_failures", 0),
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


def live_chunks(url: str, out: Path, *, source: str | None = None, retries: int = 3,
                chunk_s: float = 10.0, overlap_s: float = 2.0, max_seconds: float = 0.0,
                start_s: float = 0.0, realtime: bool = False):
    """Captura ao vivo (yt-dlp | ffmpeg ou --source) -> blocos wav, no formato de run(chunk_source=...)."""
    import wave

    from placar.audio import stream_pcm, windows_from_stream

    folder = out / "chunks"
    folder.mkdir(parents=True, exist_ok=True)
    blocks = _drained(stream_pcm(url, source=source or "", retries=retries, start_s=start_s))
    wall0 = time.perf_counter()
    for index, (start, pcm) in enumerate(windows_from_stream(blocks, chunk_s=chunk_s, overlap_s=overlap_s)):
        if max_seconds and start >= max_seconds:
            break
        if realtime:  # VOD baixa mais rápido que o ao vivo: segura até a hora real do bloco
            wait = start + len(pcm) / 32000 - (time.perf_counter() - wall0)
            if wait > 0:
                time.sleep(wait)
        c0 = time.perf_counter()
        dest = folder / f"chunk_{index:04d}.wav"
        with wave.open(str(dest), "wb") as handle:
            handle.setnchannels(1)
            handle.setsampwidth(2)
            handle.setframerate(16000)
            handle.writeframes(pcm)
        yield index, start, len(pcm) / 32000, dest, None, (time.perf_counter() - c0) * 1000


def _drained(blocks, max_bytes: int = 32000 * 60 * 30):
    """Lê a captura numa thread e guarda numa fila.

    Sem isto, quando o processamento (ou o --realtime) segura o consumo, o pipe
    enche, o yt-dlp/ffmpeg para de ler o googlevideo, a conexão cai e o VOD
    "acaba" no meio (visto no teste: parou em 128 s de 460 s).
    """
    import queue

    q: "queue.Queue[Any]" = queue.Queue(maxsize=max(1, max_bytes // 32000))
    done = object()

    def pump():
        try:
            for block in blocks:
                q.put(block)
        except BaseException as exc:  # noqa: BLE001 - repassa ao consumidor
            q.put(exc)
        q.put(done)

    threading.Thread(target=pump, daemon=True, name="captura").start()
    while True:
        item = q.get()
        if item is done:
            return
        if isinstance(item, BaseException):
            raise item
        yield item


def _context_before(transcript: list[dict[str, Any]], t_s: float, max_chars: int = 500) -> str:
    """Falas logo antes do turno (de qualquer pessoa): resolve 'ele', 'isso' e o tema."""
    lines = [x for x in transcript if x["t_s"] < t_s - 0.05][-8:]
    text = " ".join(f"[{x.get('voz', '?')}] {x['text']}" for x in lines)
    return text[-max_chars:]


_NUM_RE = re.compile(r"\d|\b(?:mil|milh|bilh|trilh|por cento|dez|vinte|trinta|cem)\w*", re.I)


def has_number(text: str) -> bool:
    return bool(_NUM_RE.search(text or ""))


_MAG_RE = re.compile(r"\b(mil|milh\w*|bilh\w*|trilh\w*|por cento|%)", re.I)


def magnitudes(text: str) -> set[str]:
    """Ordem de grandeza falada: '270 milhões' x '270 bilhões' tem o mesmo dígito."""
    out = set()
    for m in _MAG_RE.findall(text or ""):
        m = m.lower()
        out.add("%" if m in ("%", "por cento") else m[:4])
    return out


def reconcile_numbers(primary, secondary):
    """Segunda transcrição (modelo maior) para blocos com números. Para cada segmento
    do primário com número, pega o segmento do secundário que mais se sobrepõe no tempo;
    se os números diferem, fica o texto do secundário e registra a divergência."""
    from placar.claim_bank import numbers
    from placar.transcribe import TranscriptSegment

    out, fixes = [], []
    for seg in primary:
        if not has_number(seg.text):
            out.append(seg)
            continue
        best, best_ov = None, 0.0
        for alt in secondary:
            ov = min(seg.end_s, alt.end_s) - max(seg.start_s, alt.start_s)
            if ov > best_ov:
                best, best_ov = alt, ov
        if best is None or best_ov < 0.3 * (seg.end_s - seg.start_s):
            out.append(seg)
            continue
        a, b = numbers(seg.text) | magnitudes(seg.text), numbers(best.text) | magnitudes(best.text)
        if a != b and numbers(best.text):
            fixes.append({"start_s": round(seg.start_s, 1), "turbo": seg.text, "v3": best.text,
                          "num_turbo": sorted(a), "num_v3": sorted(b)})
            out.append(TranscriptSegment(start_s=seg.start_s, end_s=seg.end_s, text=best.text))
        else:
            out.append(seg)
    return out, fixes


def is_crosstalk(scores: dict[str, float], threshold: float, margin: float, slot_of_voice: dict[str, str]) -> bool:
    """Os dois perfis mais parecidos, de pessoas diferentes (ao menos um candidato),
    ambos perto do limiar e separados por menos de `margin`."""
    if len(scores) < 2:
        return False
    (v1, s1), (v2, s2) = sorted(scores.items(), key=lambda kv: -kv[1])[:2]
    slots = {slot_of_voice.get(v1, "other"), slot_of_voice.get(v2, "other")}
    if slots == {"other"} or len(slots) < 2:
        return False
    return s2 >= threshold - 0.05 and (s1 - s2) < margin
