"""Replay de um debate gravado, em velocidade real ou acelerado, com relatório."""

from __future__ import annotations

import json
import time
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any, Callable

from placar.board import Board
from placar.config import Settings
from placar.llm.router import ProviderRouter
from placar.retrieve import Retriever
from placar.stages import StageTiming, process_utterance


@dataclass
class ReplayReport:
    debate_id: str
    utterances: int
    audio_span_s: float
    wall_s: float
    speed: float
    failover_pct: float
    provider_counts: dict[str, int]
    stage_ms: dict[str, float]
    calls: int
    failures: int
    notes: list[str] = field(default_factory=list)

    def as_dict(self) -> dict[str, Any]:
        return asdict(self)


def replay(
    script: dict[str, Any],
    llm: ProviderRouter,
    retriever: Retriever,
    *,
    speed: float = 1.0,
    sleeper: Callable[[float], None] = time.sleep,
    clock_ms: Callable[[], int] | None = None,
) -> tuple[dict[str, Any], list[dict[str, Any]], ReplayReport]:
    meta = script["candidatos"]
    nomes = {slot: body["nome"] for slot, body in meta.items()}
    origin = int(script.get("origin_ms") or script.get("video", {}).get("t0") or 0)
    video = script.get("video") or {
        "id": script.get("video_id") or "",
        "ao_vivo": True,
        "inicio": 0,
        "t0": origin,
        "comeco": origin,
    }
    board = Board(
        debate_id=str(script.get("debate_id") or "replay"),
        candidatos=nomes,
        origin_ms=origin,
        video=dict(video),
        aviso=str(script.get("aviso") or "Replay do pipeline. Não é o placar publicado."),
        clock_ms=clock_ms or (lambda: int(time.time() * 1000)),
    )
    utterances = sorted(script.get("utterances") or [], key=lambda item: item["t_ms"])
    timings: list[StageTiming] = []
    wall_started = time.perf_counter()
    previous = int(utterances[0]["t_ms"]) if utterances else 0
    for utterance in utterances:
        t_ms = int(utterance["t_ms"])
        gap_s = max(0.0, (t_ms - previous) / 1000)
        previous = t_ms
        if speed > 0 and gap_s:
            sleeper(gap_s / speed)
        timings.append(process_utterance(board, utterance, llm, retriever))
    if script.get("encerrado"):
        board.finish(
            proximo=script["encerrado"].get("proximo", ""),
            texto=script["encerrado"].get("texto", ""),
        )
    else:
        board.video = {**board.video, "ao_vivo": False}
    snapshot = board.snapshot()
    wall_s = time.perf_counter() - wall_started
    span = 0.0
    if utterances:
        span = (int(utterances[-1]["t_ms"]) - int(utterances[0]["t_ms"])) / 1000
    report = _report(board.debate_id, timings, llm, wall_s, span, speed, len(utterances))
    return snapshot, board.events, report


def _report(
    debate_id: str,
    timings: list[StageTiming],
    llm: ProviderRouter,
    wall_s: float,
    span_s: float,
    speed: float,
    utterances: int,
) -> ReplayReport:
    def stats(name: str) -> dict[str, float]:
        values = [getattr(item, name) for item in timings if getattr(item, name) > 0]
        if not values:
            return {"mean": 0.0, "max": 0.0, "n": 0}
        return {
            "mean": round(sum(values) / len(values), 3),
            "max": round(max(values), 3),
            "n": len(values),
        }

    counts: dict[str, int] = {}
    for record in llm.history:
        if record.ok:
            counts[record.provider] = counts.get(record.provider, 0) + 1
    tasks = [record for record in llm.history if record.ok or record.error]
    # Uma tarefa "passou de provedor" quando o sucesso não foi o primeiro
    # da cadeia, ou quando não houve sucesso.
    successes = [record for record in llm.history if record.ok]
    failovers = sum(1 for record in successes if record.failover)
    failed_tasks = 0
    # Conta falhas de provedor que não foram a tentativa vencedora.
    failures = sum(1 for record in llm.history if not record.ok)
    if successes:
        failover_pct = round(100 * failovers / len(successes), 1)
    else:
        failover_pct = 100.0 if llm.history else 0.0
    notes = []
    if not any(item.verify_ms for item in timings):
        notes.append("Nenhuma fala passou pelo segundo modelo.")
    return ReplayReport(
        debate_id=debate_id,
        utterances=utterances,
        audio_span_s=round(span_s, 3),
        wall_s=round(wall_s, 3),
        speed=speed,
        failover_pct=failover_pct,
        provider_counts=counts,
        stage_ms={
            "classify": stats("classify_ms"),
            "retrieve": stats("retrieve_ms"),
            "judge": stats("judge_ms"),
            "verify": stats("verify_ms"),
        },
        calls=len(tasks),
        failures=failures + failed_tasks,
        notes=notes,
    )


def load_script(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def write_outputs(
    directory: Path,
    snapshot: dict[str, Any],
    events: list[dict[str, Any]],
    report: ReplayReport,
) -> None:
    directory.mkdir(parents=True, exist_ok=True)
    (directory / "placar.json").write_text(
        json.dumps(snapshot, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    (directory / "events.jsonl").write_text(
        "".join(json.dumps(event, ensure_ascii=False) + "\n" for event in events),
        encoding="utf-8",
    )
    (directory / "replay_report.json").write_text(
        json.dumps(report.as_dict(), ensure_ascii=False, indent=2), encoding="utf-8"
    )


def build_router(settings: Settings) -> ProviderRouter:
    from placar.llm.anthropic_api import AnthropicApiProvider
    from placar.llm.claude_cli import ClaudeCliProvider
    from placar.llm.gemini import GeminiProvider
    from placar.llm.openrouter import OpenRouterProvider

    providers = []
    for name in settings.providers:
        if name == "claude_cli":
            providers.append(
                ClaudeCliProvider(
                    binary=settings.claude_bin,
                    model=settings.claude_model,
                    session_chunks=settings.session_chunks,
                )
            )
        elif name == "openrouter":
            openrouter = OpenRouterProvider(
                api_key=settings.openrouter_key,
                model=settings.openrouter_model,
            )
            openrouter.timeout_s = settings.openrouter_timeout_s
            providers.append(openrouter)
        elif name == "groq" and settings.groq_key:
            from placar.llm.groq_llm import GroqLlmProvider

            groq = GroqLlmProvider(api_key=settings.groq_key, model=settings.groq_llm_model)
            groq.timeout_s = settings.groq_llm_timeout_s
            providers.append(groq)
        elif name == "anthropic" and settings.anthropic_key:
            providers.append(
                AnthropicApiProvider(
                    api_key=settings.anthropic_key, model=settings.anthropic_model
                )
            )
        elif name == "gemini" and settings.gemini_key:
            providers.append(
                GeminiProvider(api_key=settings.gemini_key, model=settings.gemini_model)
            )
    if settings.groq_key and "groq_verify" in settings.verify_providers:
        # Fica no fim da fila: só entra em classificação se todos os outros caírem.
        from placar.llm.groq_llm import GroqLlmProvider

        verifier = GroqLlmProvider(api_key=settings.groq_key, model=settings.groq_verify_model,
                                   name="groq_verify")
        verifier.timeout_s = settings.groq_llm_timeout_s
        providers.append(verifier)
    if not providers:
        raise RuntimeError("Nenhum provedor de LLM configurado.")
    router = ProviderRouter(
        providers,
        retries=settings.retries,
        breaker_threshold=settings.breaker_threshold,
        breaker_cooldown_s=settings.breaker_cooldown_s,
        timeout_s=settings.claude_timeout_s,
    )
    router.verify_order = list(settings.verify_providers)
    return router
