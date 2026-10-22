"""Busca SearXNG, Groq LLM, segundo modelo, texto de revisão neutro, prompts."""

import json

from placar.board import Board
from placar.config import Settings
from placar.llm.base import LlmRequest
from placar.llm.groq_llm import GROQ_CHAT_URL, GroqLlmProvider
from placar.llm.openrouter import _retry_after
from placar.llm.router import ProviderRouter
from placar.retrieve import Evidence, Retriever
from placar.turns import DIVERGE_TEXT, REVIEW_TEXT, SYSTEM_TURN, process_turn

SEARX = {"results": [
    {"title": "Blog", "url": "https://blog.example.com/x", "content": "nada"},
    {"title": "IBGE PIB 2010", "url": "https://agenciadenoticias.ibge.gov.br/a", "content": "PIB 7,5%"},
    {"title": "G1", "url": "https://g1.globo.com/b", "content": "PIB cresceu 7,5%"},
]}


class FakeDdg:
    def __init__(self):
        self.calls = 0

    def search(self, query, timeout_s=8.0):
        self.calls += 1
        return [Evidence("DDG", "https://aosfatos.org/z", "t", "duckduckgo")]


def test_searx_primary_trusted_first_no_ddg():
    ddg = FakeDdg()
    r = Retriever(Settings(searxng_url="http://s", ddg_enabled=True),
                  http=lambda url, t: (200, json.dumps(SEARX)), ddg=ddg)
    found = r.search("PIB 2010")
    assert [e.url for e in found] == ["https://agenciadenoticias.ibge.gov.br/a", "https://g1.globo.com/b"]
    assert all(e.origem == "searxng" for e in found)
    assert ddg.calls == 0 and r.searx_requests == 1


def test_searx_down_falls_back_to_ddg():
    def boom(url, t):
        raise OSError("connection refused")

    ddg = FakeDdg()
    r = Retriever(Settings(searxng_url="http://s", ddg_enabled=True), http=boom, ddg=ddg)
    found = r.search("PIB 2010")
    assert ddg.calls == 1 and found[0].origem == "duckduckgo" and r.searx_failures == 1


def test_groq_provider_posts_to_groq_with_user_agent_and_lenient_schema():
    seen = {}

    def transport(req, timeout_s):
        seen["url"], seen["ua"] = req.full_url, req.get_header("User-agent")
        seen["body"] = json.loads(req.data)
        return 200, json.dumps({"choices": [{"message": {"content": '{"a": 1}'}}]})

    p = GroqLlmProvider(api_key="k", model="openai/gpt-oss-120b", transport=transport)
    out = p.generate(LlmRequest("t", "s", "u", {"type": "object"}), 5)
    assert out == '{"a": 1}' and seen["url"] == GROQ_CHAT_URL
    assert "urllib" not in (seen["ua"] or "urllib")
    assert seen["body"]["response_format"]["json_schema"]["strict"] is False
    assert seen["body"]["reasoning_effort"] == "low"


def test_retry_after_parse():
    assert _retry_after("Please try again in 2.5s. Need more") == 2.5
    assert _retry_after("try again in 450ms") == 0.45
    assert _retry_after("try again in 1m3s") == 63
    assert _retry_after("nope") is None


class Prov:
    def __init__(self, name, replies):
        self.name, self.replies, self.calls = name, replies, []

    def generate(self, request, timeout_s):
        self.calls.append(request)
        reply = self.replies[request.task]
        return json.dumps(reply, ensure_ascii=False)


TURN = {"tom": "balanco", "itens": [{"tipo": "afirmacao_checavel", "titulo": "PIB cresceu 10,5% em 2010",
        "citacao": "esse país cresceu 10,5% em 2010", "categoria": "economia", "busca": "PIB 2010"}]}


def _setup(judge, verify):
    first = Prov("groq", {"classify_turn": TURN, "judge": judge, "verify": judge})
    second = Prov("groq_verify", {"classify_turn": TURN, "judge": verify, "verify": verify})
    router = ProviderRouter([first, second], retries=0)
    router.verify_order = ["groq_verify", "openrouter"]
    retr = Retriever(Settings(searxng_url="http://s"), http=lambda u, t: (200, json.dumps(SEARX)))
    board = Board(debate_id="t", candidatos={"1": "Lula", "2": "B"}, origin_ms=0, video={}, aviso="")
    return board, router, retr, first, second


def _claim(board):
    return board.snapshot()["fatos"][0]["declaracoes"][0]


FALSO = {"veredito": "falso", "motivo": "IBGE: 7,5%.", "fonte_url": "https://g1.globo.com/b"}


def test_second_model_confirms_falso_publishes():
    board, router, retr, first, second = _setup(FALSO, FALSO)
    res = process_turn(board, {"quem": "1", "text": "esse país cresceu 10,5% em 2010", "t_ms": 1, "dur_s": 5},
                       router, retr)
    c = _claim(board)
    assert c["veredito"] == "falso" and c["fonte"]["url"] == "https://g1.globo.com/b"
    assert second.calls[-1].task == "verify"
    # o segundo modelo é cego: não vê o veredito do primeiro
    assert "falso" not in second.calls[-1].user
    assert res.verdicts[0]["publicado"] == "falso"


def test_disagreement_stays_em_revisao_without_leaking_first_verdict():
    board, router, retr, *_ = _setup(FALSO, {"veredito": "verdadeiro", "motivo": "ok"})
    process_turn(board, {"quem": "1", "text": "x", "t_ms": 1, "dur_s": 5}, router, retr)
    c = _claim(board)
    assert c["veredito"] == "em_revisao" and c["motivo"] == DIVERGE_TEXT
    assert "falso" not in json.dumps(board.snapshot(), ensure_ascii=False).lower().replace("falso\": 0", "")


def test_degree_disagreement_publishes_milder():
    board, router, retr, *_ = _setup(FALSO, {"veredito": "impreciso", "motivo": "Exagero."})
    process_turn(board, {"quem": "1", "text": "x", "t_ms": 1, "dur_s": 5}, router, retr)
    assert _claim(board)["veredito"] == "impreciso"


def test_no_second_provider_keeps_neutral_review_text():
    first = Prov("groq", {"classify_turn": TURN, "judge": FALSO})
    router = ProviderRouter([first], retries=0)
    retr = Retriever(Settings(searxng_url="http://s"), http=lambda u, t: (200, json.dumps(SEARX)))
    board = Board(debate_id="t", candidatos={"1": "Lula", "2": "B"}, origin_ms=0, video={}, aviso="")
    process_turn(board, {"quem": "1", "text": "x", "t_ms": 1, "dur_s": 5}, router, retr)
    c = _claim(board)
    assert c["veredito"] == "em_revisao" and c["motivo"] == REVIEW_TEXT
    assert "falso" not in c["motivo"] and "_primeiro" not in c


def test_prompt_rules_promise_is_not_claim():
    assert "Promessa NUNCA é afirmacao_checavel" in SYSTEM_TURN
    assert "sem o nome do candidato" in SYSTEM_TURN


def test_settings_default_order_and_claude_skip(monkeypatch):
    monkeypatch.setenv("GROQ_API_KEY", "k")
    monkeypatch.setenv("CLAUDE_BIN", "/nao/existe/claude")
    monkeypatch.delenv("LLM_PROVIDERS", raising=False)
    from placar.replay import build_router

    s = Settings.from_env()
    assert s.providers == ("claude_cli", "groq", "openrouter")
    router = build_router(s)
    names = [p.name for p in router.providers]
    assert names[0] == "claude-cli" and "groq" in names and names[-1] == "groq_verify"
    first = Prov("x", {})
    del first
    # CLI ausente: o roteador pula sem erro e segue para a Groq (sem rede aqui: só checa a ordem)
    assert router.verify_order[0] == "groq_verify"


def test_drained_buffers_and_reraises():
    import pytest

    from placar.audio_replay import _drained

    assert list(_drained(iter([b"a", b"b"]))) == [b"a", b"b"]

    def bad():
        yield b"x"
        raise RuntimeError("caiu")

    gen = _drained(bad())
    assert next(gen) == b"x"
    with pytest.raises(RuntimeError):
        list(gen)


class _Proc:
    def __init__(self, data, code=0):
        import io

        self.stdout = io.BytesIO(data)
        self.code = code

    def wait(self):
        return self.code


def test_stream_pcm_resumes_vod_when_ytdlp_exits_zero_mid_video():
    from placar.audio import BYTES_PER_S, stream_pcm

    feeds = [b"\0" * BYTES_PER_S * 2, b"\1" * BYTES_PER_S, b""]
    offsets = []

    def popen(args, **kw):
        if args[0] == "yt-dlp":
            sect = [a for a in args if a.startswith("*")]
            offsets.append(sect[0] if sect else "0")
            return _Proc(b"")
        return _Proc(feeds.pop(0))

    data = b"".join(stream_pcm("https://y", start_s=10, popen=popen, sleep=lambda s: None))
    assert len(data) == BYTES_PER_S * 3
    assert offsets == ["*10-inf", "*12-inf", "*13-inf"]
