"""Fila + pool de workers para as etapas de LLM. O laço de áudio só enfileira."""

from __future__ import annotations

import concurrent.futures
import threading
import time
from typing import Any, Callable


class LlmWorker:
    def __init__(self, fn: Callable[[dict[str, Any]], Any], *, workers: int = 2) -> None:
        self._fn = fn
        self._pool = concurrent.futures.ThreadPoolExecutor(max_workers=workers, thread_name_prefix="llm")
        self._lock = threading.Lock()
        self.done: list[dict[str, Any]] = []
        self.pending = 0

    def submit(self, job: dict[str, Any]) -> None:
        job = {**job, "queued_at": time.perf_counter()}
        with self._lock:
            self.pending += 1
        self._pool.submit(self._run, job)

    def _run(self, job: dict[str, Any]) -> None:
        started = time.perf_counter()
        try:
            result = self._fn(job)
            error = ""
        except Exception as exc:  # noqa: BLE001 - um turno ruim não derruba o pool
            result, error = None, repr(exc)
        finished = time.perf_counter()
        with self._lock:
            self.pending -= 1
            self.done.append({"job": job, "result": result, "error": error,
                              "queue_wait_s": round(started - job["queued_at"], 3),
                              "run_s": round(finished - started, 3), "finished_at": finished})

    def drain(self, timeout_s: float | None = None) -> None:
        self._pool.shutdown(wait=True)
