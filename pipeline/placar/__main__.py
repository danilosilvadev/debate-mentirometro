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

    args = parser.parse_args(argv)
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


if __name__ == "__main__":
    raise SystemExit(main())
