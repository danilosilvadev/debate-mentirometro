"""Claude Code em modo headless.

Documentação consultada em 2026-10-21 (code.claude.com/docs/en/headless):

- Uma chamada: `claude -p PROMPT --output-format json --json-schema SCHEMA --model haiku`.
  O stdout é um objeto com `result` e, quando o schema fecha, `structured_output`.
- Sessão persistente, para não pagar a partida do processo a cada fala:
  `claude -p --input-format stream-json --output-format stream-json --verbose`.
  Cada linha não vazia no stdin é uma mensagem JSON. Linha em branco é ignorada.
  Um turno do usuário é
  `{"type":"user","message":{"role":"user","content":[{"type":"text","text":"..."}]}}`.
  O turno termina numa linha `{"type":"result", ...}`.
- `--permission-mode dontAsk` impede o processo de esperar um humano.
- `--model haiku` (ou um id completo) escolhe o modelo. Haiku 5.5 é o alvo
  da classificação ao vivo; o alias `haiku` acompanha o Haiku da assinatura.
- A cada N falas o processo é encerrado e outro começa, para o contexto
  não acumular o debate inteiro.
"""

from __future__ import annotations

import json
import os
import subprocess
import threading
import time
from typing import Any

from placar.llm.base import (
    CliFailure,
    LlmRequest,
    ProviderError,
    RateLimitFailure,
    TimeoutFailure,
    ProviderUnavailable,
)

_LIMIT_MARKERS = (
    "usage limit",
    "rate limit",
    "too many requests",
    "hit your limit",
    "you've hit your",
    "out of extra usage",
    "429",
)

_USER_ENVELOPE = {
    "type": "user",
    "parent_tool_use_id": None,
}


class ClaudeCliProvider:
    name = "claude-cli"

    def __init__(
        self,
        *,
        binary: str = "claude",
        model: str = "haiku",
        session_chunks: int = 8,
        popen: Any = None,
        persistent: bool = True,
    ) -> None:
        self.binary = binary
        self.model = model
        self.session_chunks = max(1, session_chunks)
        self._popen = popen or subprocess.Popen
        self.persistent = persistent
        self._proc: Any = None
        self._turns = 0
        # Binário ausente: lembra e não tenta mais nesta execução.
        self.unavailable = False

    def close(self) -> None:
        proc = self._proc
        self._proc = None
        self._turns = 0
        if proc is None:
            return
        try:
            if proc.stdin:
                proc.stdin.close()
        except Exception:
            pass
        try:
            proc.kill()
        except Exception:
            pass

    def generate(self, request: LlmRequest, timeout_s: float) -> str:
        if self.unavailable:
            raise ProviderUnavailable(f"Claude CLI não encontrado ({self.binary}).")
        if self.persistent:
            try:
                return self._session_turn(request, timeout_s)
            except ProviderUnavailable:
                self.close()
                raise
            except CliFailure:
                self.close()
                return self._oneshot(request, timeout_s)
            except ProviderError:
                self.close()
                raise
        return self._oneshot(request, timeout_s)

    def _oneshot(self, request: LlmRequest, timeout_s: float) -> str:
        prompt = (
            f"{request.system}\n\n"
            "Responda apenas com o objeto JSON pedido, sem cercas de markdown.\n\n"
            f"{request.user}"
        )
        args = [
            self.binary,
            "-p",
            prompt,
            "--output-format",
            "json",
            "--json-schema",
            json.dumps(request.schema, ensure_ascii=False),
            "--model",
            self.model,
            "--permission-mode",
            "dontAsk",
            "--max-turns",
            # Saída estruturada gasta 2 turnos internos (chamada da ferramenta + fim). Com 1, ~40% das
            # chamadas terminavam em error_max_turns (exit 1). Com 3 foram 16/16 ok.
            "3",
        ]
        try:
            proc = self._popen(
                args,
                stdin=subprocess.DEVNULL,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
            )
        except FileNotFoundError as exc:
            self.unavailable = True
            raise ProviderUnavailable(f"Claude CLI não encontrado ({self.binary}).") from exc
        try:
            stdout, stderr = proc.communicate(timeout=timeout_s)
        except subprocess.TimeoutExpired as exc:
            proc.kill()
            raise TimeoutFailure(
                f"Claude CLI passou de {timeout_s:.0f}s."
            ) from exc
        # Só procura marcador de limite quando o CLI falhou: o JSON de sucesso traz durações, custos e
        # ids onde "429" aparece por acaso (cerca de 3% das respostas), e isso abria o circuit breaker.
        if proc.returncode not in (0, None):
            if _limited(f"{stdout}\n{stderr}"):
                raise RateLimitFailure("Claude CLI sinalizou limite de uso da assinatura.")
            raise CliFailure(stderr.strip() or f"claude saiu com código {proc.returncode}.")
        return _payload_text(stdout)

    def _session_turn(self, request: LlmRequest, timeout_s: float) -> str:
        if self._proc is None or self._turns >= self.session_chunks:
            self.close()
            self._start_session(request.system)
        message = {
            **_USER_ENVELOPE,
            "message": {
                "role": "user",
                "content": [
                    {
                        "type": "text",
                        "text": (
                            "Responda apenas com o objeto JSON do schema pedido, "
                            "sem markdown.\n"
                            f"SCHEMA: {json.dumps(request.schema, ensure_ascii=False)}\n"
                            f"TAREFA: {request.task}\n"
                            f"{request.user}"
                        ),
                    }
                ],
            },
        }
        try:
            self._proc.stdin.write(json.dumps(message, ensure_ascii=False) + "\n")
            self._proc.stdin.flush()
        except Exception as exc:
            self.close()
            raise CliFailure(f"Sessão do Claude CLI caiu ao escrever: {exc}") from exc
        line = _readline_until_result(self._proc, timeout_s)
        self._turns += 1
        return _payload_text(line)


    def _start_session(self, system: str) -> None:
        args = [
            self.binary,
            "-p",
            "--input-format",
            "stream-json",
            "--output-format",
            "stream-json",
            "--verbose",
            "--model",
            self.model,
            "--permission-mode",
            "dontAsk",
            "--append-system-prompt",
            system
            + " Não use ferramentas. Responda só com JSON válido para o schema da mensagem.",
        ]
        try:
            self._proc = self._popen(
                args,
                stdin=subprocess.PIPE,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                bufsize=1,
            )
        except FileNotFoundError as exc:
            self.unavailable = True
            raise ProviderUnavailable(f"Claude CLI não encontrado ({self.binary}).") from exc
        self._turns = 0


def _limited(text: str) -> bool:
    folded = text.lower()
    return any(marker in folded for marker in _LIMIT_MARKERS)


def _payload_text(stdout: str) -> str:
    raw = stdout.strip()
    if not raw:
        raise CliFailure("Claude CLI não devolveu saída.")
    # Sessão: a linha result. One-shot: o objeto inteiro.
    try:
        data = json.loads(raw)
    except json.JSONDecodeError as exc:
        if _limited(raw):
            raise RateLimitFailure("Claude CLI sinalizou limite de uso.") from exc
        return raw
    if isinstance(data, dict):
        if data.get("is_error") or str(data.get("subtype", "")).startswith("error"):
            message = str(data.get("result") or data.get("errors") or "erro no claude")
            if _limited(message):
                raise RateLimitFailure(message)
            raise CliFailure(message)
        structured = data.get("structured_output")
        if isinstance(structured, dict):
            return json.dumps(structured, ensure_ascii=False)
        result = data.get("result")
        if isinstance(result, str) and result.strip():
            return result
    return raw


def _readline_until_result(proc: Any, timeout_s: float) -> str:
    holder: dict[str, str] = {}
    error: dict[str, BaseException] = {}

    def read() -> None:
        try:
            while True:
                line = proc.stdout.readline()
                if line == "":
                    error["empty"] = CliFailure("Sessão do Claude CLI fechou a saída.")
                    return
                stripped = line.strip()
                if not stripped:
                    continue
                try:
                    event = json.loads(stripped)
                except json.JSONDecodeError:
                    continue
                if isinstance(event, dict) and event.get("type") == "result":
                    holder["line"] = stripped
                    return
        except Exception as exc:
            error["read"] = exc

    worker = threading.Thread(target=read, daemon=True)
    worker.start()
    worker.join(timeout_s)
    if worker.is_alive():
        try:
            proc.kill()
        except Exception:
            pass
        raise TimeoutFailure(f"Sessão do Claude CLI passou de {timeout_s:.0f}s.")
    if "empty" in error:
        raise error["empty"]
    if "read" in error:
        raise CliFailure(str(error["read"]))
    if "line" not in holder:
        raise CliFailure("Sessão do Claude CLI não devolveu result.")
    return holder["line"]


def effort_popen(effort: str | None = None, base: Any = None):
    """Popen que acrescenta --effort (menos tokens de raciocínio) e não grava sessão em disco."""
    level = effort if effort is not None else os.environ.get("CLAUDE_EFFORT", "low")
    popen = base or subprocess.Popen

    def make(args, **kwargs):
        extra = ["--no-session-persistence"]
        if level:
            extra = ["--effort", level] + extra
        return popen(list(args) + extra, **kwargs)

    return make


class ClaudeSessionPool:
    """Sessões persistentes do Claude CLI, mantidas quentes (sem os 4-7 s de partida a cada chamada).

    O prompt de sistema fica fixo na sessão, então cada tarefa (classificar, julgar, confirmar) tem a sua
    lista de sessões. Uma sessão atende uma chamada por vez; chamadas simultâneas usam outras sessões do
    mesmo papel, até `size`. Sessão que falha é descartada e recriada. Cada papel (`name`) é um provedor
    separado no roteador: o confirmador cego nunca divide sessão com o juiz.
    """

    def __init__(self, *, name: str = "claude-cli", binary: str = "claude", model: str = "haiku", size: int = 2,
                 session_chunks: int = 8, effort: str | None = None, popen: Any = None) -> None:
        self.name = name
        self.binary = binary
        self.model = model
        self.size = max(1, size)
        self.session_chunks = session_chunks
        self._popen = popen or effort_popen(effort)
        self._free: dict[str, list[ClaudeCliProvider]] = {}
        self._made: dict[str, int] = {}
        self._cv = threading.Condition()
        self.unavailable = False

    @staticmethod
    def _key(request: LlmRequest) -> str:
        return f"{request.task}|{hash(request.system)}"

    def _acquire(self, key: str, timeout_s: float) -> "ClaudeCliProvider":
        deadline = time.monotonic() + timeout_s
        with self._cv:
            while True:
                free = self._free.setdefault(key, [])
                if free:
                    return free.pop()
                if self._made.get(key, 0) < self.size:
                    self._made[key] = self._made.get(key, 0) + 1
                    return ClaudeCliProvider(binary=self.binary, model=self.model, session_chunks=self.session_chunks,
                                             persistent=True, popen=self._popen)
                remaining = deadline - time.monotonic()
                if remaining <= 0:
                    raise TimeoutFailure("Nenhuma sessão do Claude CLI ficou livre a tempo.")
                self._cv.wait(remaining)

    def _release(self, key: str, session: "ClaudeCliProvider", broken: bool) -> None:
        with self._cv:
            if broken:
                session.close()
                self._made[key] = max(0, self._made.get(key, 1) - 1)
            else:
                self._free.setdefault(key, []).append(session)
            self._cv.notify()

    def generate(self, request: LlmRequest, timeout_s: float) -> str:
        if self.unavailable:
            raise ProviderUnavailable(f"Claude CLI não encontrado ({self.binary}).")
        key = self._key(request)
        session = self._acquire(key, timeout_s)
        broken = True
        try:
            out = session.generate(request, timeout_s)
            broken = False
            return out
        except ProviderUnavailable:
            self.unavailable = True
            raise
        finally:
            self._release(key, session, broken)

    def warm(self, requests: list[LlmRequest], timeout_s: float = 90.0) -> int:
        """Abre as sessões antes do debate (a primeira chamada de uma sessão leva ~13 s). Devolve quantas abriram."""
        done: list[int] = []

        def one(req: LlmRequest) -> None:
            try:
                self.generate(req, timeout_s)
                done.append(1)
            except ProviderError:
                pass

        threads = [threading.Thread(target=one, args=(r,), daemon=True) for r in requests for _ in range(self.size)]
        for t in threads:
            t.start()
        for t in threads:
            t.join(timeout_s + 5)
        return len(done)

    def close(self) -> None:
        with self._cv:
            for sessions in self._free.values():
                for session in sessions:
                    session.close()
            self._free.clear()
            self._made.clear()
