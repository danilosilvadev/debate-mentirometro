"""Servidor local do placar.json. O app aponta PLACAR_BASE para esta origem."""

from __future__ import annotations

import json
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any
from urllib.parse import urlparse


def response_for(directory: Path, path: str) -> tuple[int, str, bytes]:
    name = urlparse(path).path
    if name in ("/", "/placar.json"):
        target = directory / "placar.json"
        content_type = "application/json; charset=utf-8"
    elif name == "/events.jsonl":
        target = directory / "events.jsonl"
        content_type = "application/x-ndjson; charset=utf-8"
    else:
        return 404, "text/plain; charset=utf-8", b"nao encontrado"
    if not target.is_file():
        return 404, "text/plain; charset=utf-8", b"arquivo ainda nao existe"
    return 200, content_type, target.read_bytes()


def make_handler(directory: Path) -> type[BaseHTTPRequestHandler]:
    root = directory

    class Handler(BaseHTTPRequestHandler):
        def do_GET(self) -> None:  # noqa: N802
            status, content_type, body = response_for(root, self.path)
            self.send_response(status)
            self.send_header("Content-Type", content_type)
            self.send_header("Cache-Control", "public, max-age=3")
            self.send_header("Access-Control-Allow-Origin", "*")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)

        def do_OPTIONS(self) -> None:  # noqa: N802
            self.send_response(204)
            self.send_header("Access-Control-Allow-Origin", "*")
            self.send_header("Access-Control-Allow-Methods", "GET, OPTIONS")
            self.end_headers()

        def log_message(self, fmt: str, *args: Any) -> None:
            return

    return Handler


def serve(directory: Path, host: str, port: int) -> None:
    directory.mkdir(parents=True, exist_ok=True)
    if not (directory / "placar.json").is_file():
        (directory / "placar.json").write_text(
            json.dumps({"atualizado": 0, "candidatos": {}, "fatos": [], "propostas": [], "ataques": [], "linha": {}}),
            encoding="utf-8",
        )
    httpd = ThreadingHTTPServer((host, port), make_handler(directory))
    print(f"placar em http://{host}:{port}/placar.json", flush=True)
    httpd.serve_forever()
