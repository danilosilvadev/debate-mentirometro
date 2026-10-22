import json
import wave
from pathlib import Path

import pytest

from placar.audio import BYTES_PER_S, windows_from_stream, ytdlp_pipe_args
from placar.config import Settings
from placar.llm.base import LlmRequest, ProviderUnavailable
from placar.llm.claude_cli import ClaudeCliProvider
from placar.llm.router import ProviderRouter
from placar.transcribe import (
    FallbackTranscriber,
    GroqWhisperTranscriber,
    SttError,
    TranscriptSegment,
    build_transcriber,
    dedupe_overlap,
)


def _wav(tmp_path: Path) -> Path:
    path = tmp_path / "a.wav"
    with wave.open(str(path), "wb") as handle:
        handle.setnchannels(1)
        handle.setsampwidth(2)
        handle.setframerate(16000)
        handle.writeframes(b"\0\0" * 16000)
    return path


def test_groq_parses_verbose_json(tmp_path):
    seen = {}

    def post(url, body, headers, timeout_s):
        seen.update(url=url, headers=headers, body=body)
        return 200, json.dumps({"segments": [{"start": 0.0, "end": 1.5, "text": " Boa noite. "}]})

    stt = GroqWhisperTranscriber(api_key="k", post=post)
    out = stt.transcribe(_wav(tmp_path))
    assert out == [TranscriptSegment(0.0, 1.5, "Boa noite.")]
    assert seen["url"].endswith("/audio/transcriptions")
    assert b"whisper-large-v3-turbo" in seen["body"] and b"verbose_json" in seen["body"]
    assert seen["headers"]["Authorization"] == "Bearer k"
    assert "User-Agent" in seen["headers"]


def test_groq_error_raises(tmp_path):
    stt = GroqWhisperTranscriber(api_key="k", post=lambda *a: (429, "rate"))
    with pytest.raises(SttError):
        stt.transcribe(_wav(tmp_path))
    with pytest.raises(SttError):
        GroqWhisperTranscriber(api_key="").transcribe(_wav(tmp_path))


class _Fake:
    name = "fake"

    def __init__(self, fail=False):
        self.fail = fail
        self.calls = 0

    def transcribe(self, path):
        self.calls += 1
        if self.fail:
            raise SttError("timeout")
        return [TranscriptSegment(0, 1, "ok")]


def test_fallback_to_local_on_error(tmp_path):
    primary, local = _Fake(fail=True), _Fake()
    stt = FallbackTranscriber(primary, local)
    assert stt.transcribe(_wav(tmp_path))[0].text == "ok"
    assert stt.last_provider == "local" and local.calls == 1 and stt.failures == 1
    ok = FallbackTranscriber(_Fake(), local)
    ok.transcribe(_wav(tmp_path))
    assert ok.last_provider == "fake"


def test_build_transcriber_selects_groq():
    stt = build_transcriber(Settings(stt_provider="groq", groq_key="k"))
    assert isinstance(stt, FallbackTranscriber)
    assert isinstance(stt.primary, GroqWhisperTranscriber)
    assert not isinstance(build_transcriber(Settings()), FallbackTranscriber)


def test_dedupe_overlap():
    prev = "o eleitor tem de ver os concorrentes frente a frente."
    assert dedupe_overlap(prev, "correntes frente a frente e comparar") == "e comparar"
    assert dedupe_overlap("uma tradição de", "uma tradição de décadas") == "décadas"
    assert dedupe_overlap("abc", "nada a ver") == "nada a ver"


class _Ok:
    name = "openrouter"

    def generate(self, request, timeout_s):
        return json.dumps({"tipo": "outro"})


def test_missing_claude_binary_is_skipped_after_first_call():
    def popen(*a, **k):
        raise FileNotFoundError("claude")

    cli = ClaudeCliProvider(binary="nope", popen=popen)
    router = ProviderRouter([cli, _Ok()], retries=1)
    schema = {"type": "object", "properties": {"tipo": {"type": "string"}}, "required": ["tipo"]}
    req = LlmRequest(task="classify", system="s", user="u", schema=schema)
    router.complete(req)
    router.complete(req)
    cli_calls = [r for r in router.history if r.provider == "claude-cli"]
    assert len(cli_calls) == 1  # sem retentativa e sem tentar de novo depois
    assert "claude-cli" in router.unavailable
    with pytest.raises(ProviderUnavailable):
        cli.generate(req, 1)


def test_windows_from_stream_overlap():
    blocks = [b"\1" * BYTES_PER_S] * 20
    wins = list(windows_from_stream(iter(blocks), chunk_s=10, overlap_s=2))
    assert [w[0] for w in wins] == [0.0, 8.0, 16.0]
    assert all(len(w[1]) == 10 * BYTES_PER_S for w in wins[:2])


def test_ytdlp_pipe_resumes_from_offset():
    args = ytdlp_pipe_args("u", 125)
    assert "-o" in args and args[args.index("-o") + 1] == "-"
    assert "*125-inf" in args


def test_router_enforces_wall_clock_timeout():
    import time as _t

    class Slow:
        name = "slow"
        timeout_s = 0.2

        def generate(self, request, timeout_s):
            _t.sleep(2)
            return "{}"

    router = ProviderRouter([Slow(), _Ok()], retries=0)
    schema = {"type": "object", "properties": {"tipo": {"type": "string"}}, "required": ["tipo"]}
    started = _t.perf_counter()
    out = router.complete(LlmRequest(task="classify", system="s", user="u", schema=schema))
    assert out.provider == "openrouter"
    assert _t.perf_counter() - started < 1.5
