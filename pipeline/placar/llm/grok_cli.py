"""Grok CLI (conta xAI do usuário, logada no box) em modo headless, só texto.

    grok -p PROMPT --system-prompt-override SYS --tools '' --disable-web-search --no-subagents \
         --max-turns 1 --permission-mode dontAsk --output-format json --json-schema SCHEMA

`--tools ''` tira as ferramentas e `dontAsk` nega qualquer pedido de ferramenta sem esperar
humano (nunca usamos --always-approve). Saída: objeto com `structuredOutput` (ou `text`).
Medido em 22/10/2026: 3–5 s por chamada, ~12,8 mil tokens de entrada (prompt do agente),
~US$ 0,03 por chamada. Limite de processos paralelos para não sobrecarregar o box.
"""

from __future__ import annotations

import json
import os
import shutil
import subprocess
import tempfile
import threading

from placar.llm.base import CliFailure, LlmRequest, ProviderUnavailable, RateLimitFailure, TimeoutFailure

_LIMIT = ("rate limit", "too many requests", "429", "usage limit", "quota", "credits")


class GrokCliProvider:
    name = "grok_cli"

    def __init__(self, *, binary: str = "grok", model: str = "", parallel: int = 3, runner=None) -> None:
        self.binary = binary
        self.model = model
        # o prompt de classificação leva 15-20 s no grok; 20 s derrubava metade dos turnos (eval Band)
        self.timeout_s = float(os.environ.get("GROK_CLI_TIMEOUT_S", "40"))
        self._sem = threading.BoundedSemaphore(max(1, parallel))
        self._run = runner or subprocess.run
        self._cwd = tempfile.mkdtemp(prefix="placar-grok-")  # pasta vazia: nada do repo no contexto
        self.unavailable = runner is None and shutil.which(binary) is None

    def _args(self, request: LlmRequest) -> list[str]:
        sys_prompt = (request.system or "") + "\nNunca use ferramentas. Responda só o JSON pedido."
        args = [self.binary, "-p", request.user, "--system-prompt-override", sys_prompt, "--tools", "",
                "--disable-web-search", "--no-subagents", "--max-turns", "1", "--permission-mode", "dontAsk",
                "--output-format", "json"]
        if request.schema:
            args += ["--json-schema", json.dumps(request.schema, ensure_ascii=False)]
        # Padrão do grok (grok-4.7, raciocínio alto) levou até 90 s por chamada e derrubou metade dos
        # turnos no eval Band (22/10). Medido: build-fast+low 8 s, 4.7+low 16 s, com o mesmo resultado.
        fast = request.task in ("classify_turn", "classify")
        model = self.model or (os.environ.get("GROK_CLI_FAST_MODEL", "grok-4.7-build-fast") if fast
                               else os.environ.get("GROK_CLI_JUDGE_MODEL", "grok-4.7"))
        if model:
            args += ["-m", model]
        effort = os.environ.get("GROK_CLI_EFFORT", "low")
        if effort:
            args += ["--reasoning-effort", effort]
        return args

    def generate(self, request: LlmRequest, timeout_s: float) -> str:
        if self.unavailable:
            raise ProviderUnavailable(f"Grok CLI não encontrado ({self.binary}).")
        limit = min(timeout_s, self.timeout_s) if timeout_s else self.timeout_s
        if not self._sem.acquire(timeout=limit):
            raise TimeoutFailure("grok_cli: todos os processos ocupados.")
        try:
            try:
                proc = self._run(self._args(request), capture_output=True, text=True, timeout=limit, cwd=self._cwd,
                                 env={**os.environ, "NO_COLOR": "1"})
            except subprocess.TimeoutExpired as exc:
                raise TimeoutFailure(f"grok_cli passou de {limit:.0f}s.") from exc
        finally:
            self._sem.release()
        err = (proc.stderr or "").lower()
        if proc.returncode != 0:
            if any(m in err for m in _LIMIT):
                raise RateLimitFailure("grok_cli: limite de uso.")
            raise CliFailure(f"grok_cli saiu com {proc.returncode}: {(proc.stderr or '')[:120]}")
        try:
            data = json.loads(proc.stdout)
        except json.JSONDecodeError as exc:
            raise CliFailure("grok_cli: saída não é JSON.") from exc
        out = data.get("structuredOutput")
        return json.dumps(out, ensure_ascii=False) if out is not None else str(data.get("text") or "")
