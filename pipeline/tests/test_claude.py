import json
import subprocess

from placar.llm.base import RateLimitFailure, TimeoutFailure
from placar.llm.claude_cli import ClaudeCliProvider
from placar.llm.openrouter import OpenRouterProvider
from placar.schemas import CLASSIFY_SCHEMA
from placar.llm.base import LlmRequest


REQUEST = LlmRequest(
    task="classify", system="sistema", user="fala", schema=CLASSIFY_SCHEMA
)


class OneShot:
    def __init__(self, stdout="", stderr="", code=0, explode=False):
        self.stdout = stdout
        self.stderr = stderr
        self.returncode = code
        self.explode = explode
        self.args = None

    def __call__(self, args, **kwargs):
        self.args = args
        self.kwargs = kwargs
        return self

    def communicate(self, timeout=None):
        if self.explode:
            raise subprocess.TimeoutExpired(cmd=self.args, timeout=timeout or 1)
        return self.stdout, self.stderr

    def kill(self):
        self.killed = True


def test_oneshot_pede_json_schema_e_modelo_haiku():
    proc = OneShot(
        stdout=json.dumps(
            {
                "type": "result",
                "subtype": "success",
                "is_error": False,
                "structured_output": {"tipo": "outro", "tema": "geral"},
                "session_id": "sess-1",
            }
        )
    )
    provider = ClaudeCliProvider(model="haiku", popen=proc, persistent=False)
    raw = provider.generate(REQUEST, 5)
    assert "--json-schema" in proc.args
    assert proc.args[proc.args.index("--model") + 1] == "haiku"
    assert "--output-format" in proc.args
    assert "json" in proc.args
    assert json.loads(raw)["tipo"] == "outro"


def test_limite_da_assinatura_vira_rate_limit():
    proc = OneShot(
        stdout=json.dumps(
            {"is_error": True, "subtype": "error_during_execution", "result": "You've hit your limit"}
        )
    )
    provider = ClaudeCliProvider(popen=proc, persistent=False)
    try:
        provider.generate(REQUEST, 5)
        raise AssertionError("deveria limitar")
    except RateLimitFailure:
        pass


def test_timeout_do_cli():
    proc = OneShot(explode=True)
    provider = ClaudeCliProvider(popen=proc, persistent=False)
    try:
        provider.generate(REQUEST, 1)
        raise AssertionError("deveria estourar")
    except TimeoutFailure:
        pass


class SessionProc:
    def __init__(self):
        self.stdin = self
        self.stdout = self
        self.written = []
        self.lines = [
            json.dumps(
                {
                    "type": "result",
                    "subtype": "success",
                    "is_error": False,
                    "result": json.dumps({"tipo": "ataque", "tema": "conduta"}),
                }
            )
            + "\n"
        ]

    def write(self, data):
        self.written.append(data)

    def flush(self):
        return None

    def readline(self):
        if not self.lines:
            return ""
        return self.lines.pop(0)

    def kill(self):
        self.killed = True

    def __call__(self, args, **kwargs):
        self.args = args
        return self


def test_sessao_stream_json_reaproveita_o_processo():
    proc = SessionProc()
    provider = ClaudeCliProvider(model="haiku", popen=proc, persistent=True, session_chunks=4)
    provider.generate(REQUEST, 2)
    assert "--input-format" in proc.args
    assert "stream-json" in proc.args
    assert proc.written
    assert json.loads(proc.written[0])["type"] == "user"
    # Segunda fala: mesma sessão, sem novo processo. O fake só tem uma linha,
    # então recolocamos a resposta.
    proc.lines.append(proc.lines and "" or json.dumps({
        "type": "result",
        "subtype": "success",
        "is_error": False,
        "result": json.dumps({"tipo": "outro", "tema": "geral"}),
    }) + "\n")
    provider.generate(REQUEST, 2)
    assert provider._turns == 2


def test_openrouter_manda_bearer_e_modelo_free():
    seen = {}

    def transport(request, timeout_s):
        seen["url"] = request.full_url
        seen["auth"] = request.headers["Authorization"]
        seen["body"] = json.loads(request.data.decode())
        return 200, json.dumps(
            {"choices": [{"message": {"content": json.dumps({"tipo": "outro", "tema": "x"})}}]}
        )

    provider = OpenRouterProvider(
        api_key="test-key",
        model="meta-llama/llama-3.3-70b-instruct:free",
        transport=transport,
    )
    raw = provider.generate(REQUEST, 5)
    assert seen["auth"] == "Bearer test-key"
    assert seen["body"]["model"].endswith(":free")
    assert seen["body"]["response_format"]["type"] == "json_schema"
    assert "outro" in raw
