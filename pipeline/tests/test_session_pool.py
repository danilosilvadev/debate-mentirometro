"""Pool de sessões do Claude CLI e confirmador cego em paralelo."""
import json
import threading
import time

from placar.llm.base import LlmRequest, ProviderError
from placar.llm.claude_cli import ClaudeSessionPool, effort_popen
from placar.llm.router import ProviderRouter

SCHEMA = {"type": "object"}


class FakeProc:
    """Processo falso no modo stream-json: devolve uma linha `result` por mensagem recebida."""
    started = 0

    def __init__(self, args, **kw):
        FakeProc.started += 1
        self.args = args
        self.reply = threading.Semaphore(0)
        self.stdin = self
        self.stdout = self
        self.stderr = self
        self.returncode = None

    def write(self, line):
        self.reply.release()

    def flush(self):
        pass

    def close(self):
        pass

    def readline(self):
        self.reply.acquire(timeout=5)
        time.sleep(0.05)
        return json.dumps({"type": "result", "subtype": "success", "is_error": False, "result": '{"ok": true}'}) + "\n"

    def kill(self):
        pass


def req(task="judge", system="s"):
    return LlmRequest(task=task, system=system, user="u", schema=SCHEMA)


def test_sessions_are_reused_not_restarted():
    FakeProc.started = 0
    pool = ClaudeSessionPool(name="claude-cli", size=2, popen=FakeProc)
    for _ in range(5):
        assert json.loads(pool.generate(req(), 5)) == {"ok": True}
    assert FakeProc.started == 1  # uma sessão quente atendeu as 5 chamadas


def test_parallel_calls_use_separate_sessions_up_to_size():
    FakeProc.started = 0
    pool = ClaudeSessionPool(name="claude-cli", size=2, popen=FakeProc)
    out = []
    ts = [threading.Thread(target=lambda: out.append(pool.generate(req(), 5))) for _ in range(4)]
    [t.start() for t in ts]; [t.join() for t in ts]
    assert len(out) == 4 and FakeProc.started == 2  # nunca passa de `size` sessões por tarefa


def test_each_task_has_its_own_session_because_the_system_prompt_is_fixed():
    FakeProc.started = 0
    pool = ClaudeSessionPool(name="claude-cli", size=1, popen=FakeProc)
    pool.generate(req("classify_turn", "A"), 5); pool.generate(req("judge", "B"), 5)
    assert FakeProc.started == 2


def test_effort_flag_is_added():
    seen = []
    effort_popen("low", base=lambda args, **kw: seen.append(args))(["claude", "-p"])
    assert "--effort" in seen[0] and "low" in seen[0] and "--no-session-persistence" in seen[0]


def test_verify_only_pool_is_reserved_for_verify_and_excluded_from_judging():
    judge = ClaudeSessionPool(name="claude-cli", popen=FakeProc); verify = ClaudeSessionPool(name="claude-verify", popen=FakeProc)
    router = ProviderRouter([judge, verify], retries=0, timeout_s=5)
    router.verify_only = {"claude-verify"}
    assert router.complete(req("judge")).provider == "claude-cli"
    assert router.complete(req("verify")).provider == "claude-verify"
    assert router.complete(req("classify_turn")).provider == "claude-cli"


def test_pool_failure_discards_session_and_next_call_recovers():
    FakeProc.started = 0
    calls = {"n": 0}

    class Flaky(FakeProc):
        def readline(self):
            calls["n"] += 1
            if calls["n"] == 1:
                return ""  # sessão fechou a saída
            return super().readline()

    pool = ClaudeSessionPool(name="claude-cli", size=1, popen=Flaky)
    try:
        pool.generate(req(), 5)
    except Exception:  # noqa: BLE001 - o processo falso não tem o caminho one-shot; só importa o descarte
        pass
    assert json.loads(pool.generate(req(), 5)) == {"ok": True}
