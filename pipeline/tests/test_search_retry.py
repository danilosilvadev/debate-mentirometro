"""SearXNG vazio (motores suspensos): uma segunda tentativa e cache por consulta."""
import json

from placar.config import Settings
from placar.retrieve import Retriever


def make(responses):
    calls = []

    def http(url, timeout_s):
        calls.append(url)
        return 200, json.dumps({"results": responses[min(len(calls) - 1, len(responses) - 1)]})

    r = Retriever(Settings(searxng_url="http://x"), http=http)
    r.searx_retry_s = 0
    return r, calls


GOOD = [{"url": "https://g1.globo.com/a", "title": "t", "content": "c"}]


def test_empty_then_ok_is_retried_once():
    r, calls = make([[], GOOD])
    assert [e.url for e in r.search("pib 2024")] == ["https://g1.globo.com/a"]
    assert len(calls) == 2 and r.searx_empty == 1


def test_good_result_is_cached():
    r, calls = make([GOOD])
    r.search("PIB  2024"); r.search("pib 2024")
    assert len(calls) == 1  # mesma consulta (caixa/espaços), sem nova busca


def test_still_empty_after_retry_is_not_cached():
    r, calls = make([[], [], GOOD])
    assert r.search("lei antifacção") == []
    assert [e.url for e in r.search("lei antifacção")] == ["https://g1.globo.com/a"]
