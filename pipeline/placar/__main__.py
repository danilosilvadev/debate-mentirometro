"""Linha de comando: replay, serve, live."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from placar.config import Settings
from placar.replay import build_router, load_script, replay, write_outputs
from placar.retrieve import Retriever


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="placar", description="Pipeline do Placar da Verdade")
    sub = parser.add_subparsers(dest="cmd", required=True)

    replay_cmd = sub.add_parser("replay", help="Roda um roteiro ou áudio gravado")
    replay_cmd.add_argument("--script", type=Path, required=True)
    replay_cmd.add_argument("--out", type=Path, default=Path("out"))
    replay_cmd.add_argument("--speed", type=float, default=1.0, help="1 = tempo real; 0 = o mais rápido")
    replay_cmd.add_argument("--mock", action="store_true", help="Provedores fictícios, sem rede nem CLI")

    serve_cmd = sub.add_parser("serve", help="Publica placar.json nesta máquina")
    serve_cmd.add_argument("--dir", type=Path, default=Path("out"))
    serve_cmd.add_argument("--host", default="")
    serve_cmd.add_argument("--port", type=int, default=0)

    live_cmd = sub.add_parser("live", help="Corta um ao vivo do YouTube em blocos de 10 s")
    live_cmd.add_argument("--url", default="")
    live_cmd.add_argument("--out", type=Path, default=Path("out/chunks"))
    live_cmd.add_argument("--seconds", type=float, default=30.0)
    live_cmd.add_argument("--source", default="", help="ffmpeg direto (rádio/TV/arquivo) em vez do yt-dlp")
    live_cmd.add_argument("--retries", type=int, default=5)

    run_cmd = sub.add_parser("run", help="Pipeline completo ao vivo: captura, STT, voz, LLM, placar.json")
    run_cmd.add_argument("--url", default="", help="Página do YouTube (yt-dlp)")
    run_cmd.add_argument("--source", default="", help="ffmpeg direto (rádio/TV/arquivo/dispositivo)")
    run_cmd.add_argument("--wav", type=Path, default=None, help="Áudio gravado, tocado no relógio (teste)")
    run_cmd.add_argument("--out", type=Path, default=Path("out"))
    run_cmd.add_argument("--start", type=float, default=0.0, help="Segundo inicial (só VOD)")
    run_cmd.add_argument("--seconds", type=float, default=0.0, help="Para depois de N s (0 = até acabar)")
    run_cmd.add_argument("--realtime", action="store_true", help="Segura o VOD no relógio real")
    run_cmd.add_argument("--a", default="Candidato A:", help="Nome exibido:perfil de voz do slot 1")
    run_cmd.add_argument("--b", default="Candidato B:", help="Nome exibido:perfil de voz do slot 2")
    run_cmd.add_argument("--others", default="", help="Perfis de voz de mediadores, separados por vírgula")
    run_cmd.add_argument("--voices", type=Path, default=Path(__file__).resolve().parent.parent / "voices")
    run_cmd.add_argument("--threshold", type=float, default=0.45)
    run_cmd.add_argument("--debate-id", default="debate")
    run_cmd.add_argument("--video-id", default="")
    run_cmd.add_argument("--speed", type=float, default=1.0, help="Só com --wav: 1 = tempo real, 2 = dobro")
    run_cmd.add_argument("--mock", action="store_true", help="LLM fictício (sem rede)")
    run_cmd.add_argument("--retries", type=int, default=5)

    args = parser.parse_args(argv)
    if args.cmd == "run":
        return _run(args)
    if args.cmd == "replay":
        return _replay(args)
    if args.cmd == "serve":
        return _serve(args)
    return _live(args)


def _replay(args: argparse.Namespace) -> int:
    script = load_script(args.script)
    if args.mock:
        from placar.mockllm import mock_router

        router = mock_router()
    else:
        router = build_router(Settings.from_env())
    snapshot, events, report = replay(
        script,
        router,
        Retriever(Settings()),
        speed=args.speed,
    )
    write_outputs(args.out, snapshot, events, report)
    json.dump(report.as_dict(), sys.stdout, ensure_ascii=False, indent=2)
    sys.stdout.write("\n")
    return 0


def _serve(args: argparse.Namespace) -> int:
    from placar.serve import serve

    settings = Settings.from_env()
    serve(args.dir, args.host or settings.host, args.port or settings.port)
    return 0


def _live(args: argparse.Namespace) -> int:
    import wave

    from placar.audio import stream_pcm, windows_from_stream

    settings = Settings.from_env()
    args.out.mkdir(parents=True, exist_ok=True)
    blocks = stream_pcm(args.url, source=args.source, retries=args.retries)
    count = 0
    for start, pcm in windows_from_stream(
        blocks, chunk_s=settings.chunk_seconds, overlap_s=settings.chunk_overlap_seconds
    ):
        if start >= args.seconds:
            break
        dest = args.out / f"chunk_{count:04d}.wav"
        with wave.open(str(dest), "wb") as handle:
            handle.setnchannels(1)
            handle.setsampwidth(2)
            handle.setframerate(16000)
            handle.writeframes(pcm)
        print(f"bloco {count} {start:.1f}s +{len(pcm) / 32000:.1f}s", flush=True)
        count += 1
    print(f"{count} blocos em {args.out}", flush=True)
    return 0


def _run(args: argparse.Namespace) -> int:
    import logging

    from placar.audio_replay import live_chunks, run
    from placar.transcribe import build_transcriber

    logging.basicConfig(level=logging.WARNING, format="%(asctime)s %(name)s %(message)s")
    settings = Settings.from_env()
    if args.mock:
        from placar.mockllm import mock_router

        router = mock_router()
    else:
        router = build_router(settings)
    candidatos, slot_of_voice = {}, {}
    for slot, spec in (("1", args.a), ("2", args.b)):
        name, _, voice = spec.partition(":")
        candidatos[slot] = name.strip() or f"Candidato {'A' if slot == '1' else 'B'}"
        if voice.strip():
            slot_of_voice[voice.strip()] = slot
    for voice in filter(None, (v.strip() for v in args.others.split(","))):
        slot_of_voice[voice] = "other"
    source = None
    if args.wav is None:
        if not (args.url or args.source):
            print("Informe --url, --source ou --wav.", file=sys.stderr)
            return 2
        source = live_chunks(args.url, args.out, source=args.source, retries=args.retries,
                             chunk_s=settings.chunk_seconds, overlap_s=settings.chunk_overlap_seconds,
                             max_seconds=args.seconds, start_s=args.start, realtime=args.realtime)
    report = run(args.wav or Path("-"), out=args.out, router=router, retriever=Retriever(settings),
                 candidatos=candidatos, slot_of_voice=slot_of_voice, voices=args.voices,
                 whisper_model=settings.whisper_model, threshold=args.threshold,
                 chunk_s=settings.chunk_seconds, overlap_s=settings.chunk_overlap_seconds,
                 debate_id=args.debate_id, video_id=args.video_id,
                 transcriber=build_transcriber(settings), offset_s=args.start, chunk_source=source,
                 speed=args.speed)
    from placar.replay_data import write as write_replay

    write_replay(args.out, offset_s=args.start)  # itens: t relativo ao início do áudio; transcript já em s do vídeo
    print(json.dumps({"turns": len(report["llm_turns"]), "chunks": len(report["chunks"])}), flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
