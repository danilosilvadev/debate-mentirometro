"""Transcrições guardadas uma vez só, em SQLite (uma linha por fala).

Chave: (debate_id, chunk, seg). Cada bloco é gravado assim que transcrito; um bloco
já presente é reaproveitado (sem STT nem identificação de voz de novo). Replays e
avaliações leem daqui. Caminho: PLACAR_TRANSCRIPTS_DB (padrão /workspace/data/transcripts.sqlite)."""
from __future__ import annotations

import json
import os
import sqlite3
import threading
import time
from pathlib import Path
from typing import Any

SCHEMA = """
CREATE TABLE IF NOT EXISTS chunks(
  debate_id TEXT, chunk INTEGER, start_s REAL, len_s REAL, stt_model TEXT, number_model TEXT,
  number_text TEXT, source TEXT, created REAL, PRIMARY KEY(debate_id, chunk));
CREATE TABLE IF NOT EXISTS utterances(
  debate_id TEXT, chunk INTEGER, seg INTEGER, t_start REAL, t_end REAL, rel_start REAL, rel_end REAL,
  speaker TEXT, slot TEXT, confidence REAL, scores TEXT, text TEXT, text_first_pass TEXT, owned INTEGER,
  PRIMARY KEY(debate_id, chunk, seg));
"""


def default_path() -> Path:
    return Path(os.environ.get("PLACAR_TRANSCRIPTS_DB", "/workspace/data/transcripts.sqlite"))


class TranscriptDB:
    def __init__(self, path: Path | str | None = None) -> None:
        self.path = Path(path or default_path())
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self._lock = threading.Lock()
        self.con = sqlite3.connect(str(self.path), check_same_thread=False, timeout=30)
        self.con.execute("PRAGMA journal_mode=WAL")
        self.con.executescript(SCHEMA)
        self.reused = self.written = 0

    def has(self, debate_id: str, chunk: int) -> bool:
        with self._lock:
            return self.con.execute("SELECT 1 FROM chunks WHERE debate_id=? AND chunk=?",
                                    (debate_id, chunk)).fetchone() is not None

    def chunk_rows(self, debate_id: str, chunk: int) -> list[dict[str, Any]]:
        with self._lock:
            cur = self.con.execute("SELECT * FROM utterances WHERE debate_id=? AND chunk=? ORDER BY seg",
                                   (debate_id, chunk))
            cols = [c[0] for c in cur.description]
            return [dict(zip(cols, r)) for r in cur.fetchall()]

    def put_chunk(self, debate_id: str, chunk: int, *, start_s: float, len_s: float, rows: list[dict[str, Any]],
                  stt_model: str = "", number_model: str = "", number_text: str = "", source: str = "stt") -> None:
        """Idempotente: regrava o bloco inteiro numa transação."""
        with self._lock, self.con:
            self.con.execute("DELETE FROM utterances WHERE debate_id=? AND chunk=?", (debate_id, chunk))
            for i, r in enumerate(rows):
                self.con.execute(
                    "INSERT INTO utterances VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
                    (debate_id, chunk, i, r["t_start"], r["t_end"], r["rel_start"], r["rel_end"], r.get("speaker"),
                     r.get("slot"), r.get("confidence"), json.dumps(r.get("scores") or {}), r["text"],
                     r.get("text_first_pass"), int(r.get("owned", 1))))
            self.con.execute("INSERT OR REPLACE INTO chunks VALUES(?,?,?,?,?,?,?,?,?)",
                             (debate_id, chunk, start_s, len_s, stt_model, number_model, number_text, source, time.time()))

    def stats(self, debate_id: str) -> dict[str, int]:
        with self._lock:
            n = self.con.execute("SELECT count(*) FROM chunks WHERE debate_id=?", (debate_id,)).fetchone()[0]
            u = self.con.execute("SELECT count(*) FROM utterances WHERE debate_id=?", (debate_id,)).fetchone()[0]
        return {"chunks": n, "utterances": u}

    def utterances(self, debate_id: str) -> list[dict[str, Any]]:
        with self._lock:
            cur = self.con.execute("SELECT * FROM utterances WHERE debate_id=? AND owned=1 ORDER BY t_start", (debate_id,))
            cols = [c[0] for c in cur.description]
            return [dict(zip(cols, r)) for r in cur.fetchall()]
