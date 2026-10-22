"""Fila + workers para as etapas de LLM. O laço de áudio só enfileira.

Fila LIFO: com a cota apertada, o turno mais novo vai primeiro (é o que a legenda mostra).
Turno que esperou mais que `stale_s` desde o fim da fala chega marcado `stale`: a legenda
já não o mostraria em 15 s, então não gasta cota.
"""

from __future__ import annotations

import os
import queue
import threading
import time
from typing import Any, Callable

STALE_S = float(os.environ.get("PLACAR_STALE_S", "90"))


class LlmWorker:
    def __init__(self, fn: Callable[[dict[str, Any]], Any], *, workers: int = 2, stale_s: float | None = None,
                 clock: Callable[[], float] = time.perf_counter) -> None:
        self._fn = fn
        self._clock = clock
        self.stale_s = STALE_S if stale_s is None else stale_s
        self._q: "queue.LifoQueue[dict[str, Any] | None]" = queue.LifoQueue()
        self._lock = threading.Lock()
        self.done: list[dict[str, Any]] = []
        self.pending = 0
        self._threads = [threading.Thread(target=self._loop, name=f"llm-{i}", daemon=True) for i in range(workers)]
        for t in self._threads:
            t.start()

    def submit(self, job: dict[str, Any]) -> None:
        job = {**job, "queued_at": self._clock()}
        with self._lock:
            self.pending += 1
        self._q.put(job)

    def _loop(self) -> None:
        while True:
            job = self._q.get()
            if job is None:
                return
            self._run(job)

    def _run(self, job: dict[str, Any]) -> None:
        started = self._clock()
        end = job.get("speech_end_wall")
        if self.stale_s > 0 and end is not None and started - end > self.stale_s:
            job = {**job, "stale": True}
        try:
            result = self._fn(job)
            error = ""
        except Exception as exc:  # noqa: BLE001 - um turno ruim não derruba o pool
            result, error = None, repr(exc)
        finished = self._clock()
        with self._lock:
            self.pending -= 1
            self.done.append({"job": job, "result": result, "error": error,
                              "queue_wait_s": round(started - job["queued_at"], 3),
                              "run_s": round(finished - started, 3), "finished_at": finished})

    def drain(self, timeout_s: float | None = None) -> None:
        # Espera a fila esvaziar, depois encerra as threads.
        deadline = None if timeout_s is None else time.monotonic() + timeout_s
        while True:
            with self._lock:
                if self.pending == 0:
                    break
            if deadline is not None and time.monotonic() > deadline:
                break
            time.sleep(0.05)
        for _ in self._threads:
            self._q.put(None)
        for t in self._threads:
            t.join(timeout=1)
