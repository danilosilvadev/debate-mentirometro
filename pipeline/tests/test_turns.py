import json
import time

import pytest

from placar.board import Board
from placar.jsonrepair import InvalidJson, parse_model_json
from placar.llm.router import ProviderRouter
from placar.retrieve import DuckDuckGoHtml, Evidence, parse_ddg
from placar.schemas import TURN_SCHEMA
from placar.turns import process_turn
from placar.worker import LlmWorker


class Scripted:
    name = "openrouter"

    def __init__(self, answers):
        self.answers = answers
        self.tasks = []

    def generate(self, request, timeout_s):
        self.tasks.append(request.task)
        return json.dumps(self.answers[request.task], ensure_ascii=False)


class FakeRetriever:
    def __init__(self, found):
        self.found = found

    def search(self, query, timeout_s=8.0):
        return self.found


TURN = {
    "tom": "proposta",
    "itens": [
        {"tipo": "proposta", "titulo": "Ministério da Segurança", "citacao": "eu criarei o Ministério da Segurança Pública", "categoria": "seguranca"},
        {"tipo": "ataque", "titulo": "Estados fracassaram", "citacao": "os estados fracassaram", "categoria": "seguranca"},
        {"tipo": "afirmacao_checavel", "titulo": "22 milhões bancarizados", "citacao": "bancarizamos 22 milhões de brasileiros", "categoria": "economia", "busca": "bancarização 22 milhões"},
    ],
}


def board():
    return Board(debate_id="t", candidatos={"1": "Lula", "2": "Flávio"}, origin_ms=0)


def test_turn_schema_validates_list_and_rejects_bad_tipo():
    assert parse_model_json(json.dumps(TURN), TURN_SCHEMA)["itens"][2]["tipo"] == "afirmacao_checavel"
    bad = {"tom": "outro", "itens": [{"tipo": "defesa", "titulo": "x", "citacao": "x", "categoria": "outro"}]}
    with pytest.raises(InvalidJson):
        parse_model_json(json.dumps(bad), TURN_SCHEMA)


def test_process_turn_one_classify_call_and_judges_with_sources():
    ev = [Evidence("Agência Brasil", "https://agenciabrasil.ebc.com.br/x", "22 milhões", "duckduckgo")]
    prov = Scripted({"classify_turn": TURN, "judge": {"veredito": "verdadeiro", "motivo": "confere", "fonte_url": "https://agenciabrasil.ebc.com.br/x", "fonte_titulo": "AB"}})
    b = board()
    res = process_turn(b, {"quem": "1", "text": "texto", "t_ms": 1, "dur_s": 30}, ProviderRouter([prov]), FakeRetriever(ev))
    assert prov.tasks == ["classify_turn", "judge"]
    assert res.items == 3
    assert b.propostas[0]["titulo"] == "Ministério da Segurança"
    assert "os estados fracassaram" in b.ataques[0]["resumo"]
    claim = b.claims[0]
    assert claim["literal"] == "bancarizamos 22 milhões de brasileiros"
    assert claim["veredito"] == "verdadeiro" and claim["fonte"]["url"].startswith("https://agenciabrasil")


def test_falso_without_second_provider_stays_em_revisao():
    ev = [Evidence("g1", "https://g1.globo.com/a", "x", "duckduckgo")]
    prov = Scripted({"classify_turn": TURN, "judge": {"veredito": "falso", "motivo": "não", "fonte_url": "https://inventada.com"}})
    b = board()
    process_turn(b, {"quem": "1", "text": "t", "t_ms": 1}, ProviderRouter([prov]), FakeRetriever(ev))
    assert b.claims[0]["veredito"] == "em_revisao"
    assert b.claims[0]["fonte"]["url"] == "https://g1.globo.com/a"  # URL fora da lista é trocada


def test_no_sources_means_sem_dados_without_judge_call():
    prov = Scripted({"classify_turn": TURN})
    b = board()
    process_turn(b, {"quem": "1", "text": "t", "t_ms": 1}, ProviderRouter([prov]), FakeRetriever([]))
    assert prov.tasks == ["classify_turn"] and b.claims[0]["veredito"] == "sem_dados"


def test_budget_blocks_calls():
    prov = Scripted({"classify_turn": TURN})
    b = board()
    res = process_turn(b, {"quem": "1", "text": "t", "t_ms": 1, "dur_s": 5}, ProviderRouter([prov]), FakeRetriever([]), can_call=lambda: False)
    assert prov.tasks == [] and res.error


def test_worker_does_not_block_submitter():
    w = LlmWorker(lambda job: time.sleep(0.3), workers=2)
    t0 = time.perf_counter()
    for i in range(3):
        w.submit({"i": i})
    assert time.perf_counter() - t0 < 0.1
    w.drain()
    assert len(w.done) == 3


DDG_HTML = """
<div class="result results_links results_links_deep web-result">
<a rel="nofollow" class="result__a" href="//duckduckgo.com/l/?uddg=https%3A%2F%2Fg1.globo.com%2Fnoticia&amp;rut=x">Título <b>G1</b></a>
<a class="result__snippet" href="x">Trecho <b>útil</b></a></div>
<div class="result results_links results_links_deep web-result">
<a rel="nofollow" class="result__a" href="https://spam.example.com/">Spam</a>
<a class="result__snippet" href="x">nada</a></div>
"""


def test_ddg_parse_whitelist_cache_and_rate_limit(tmp_path):
    assert parse_ddg(DDG_HTML)[0] == Evidence("Título G1", "https://g1.globo.com/noticia", "Trecho útil", "duckduckgo")
    calls, sleeps, now = [], [], [100.0]
    ddg = DuckDuckGoHtml(post=lambda q, t: (calls.append(q), (200, DDG_HTML))[1], min_interval_s=2.0,
                         cache_path=tmp_path / "c.json", clock=lambda: now[0], sleep=sleeps.append)
    first = ddg.search("pergunta a")
    assert [e.url for e in first] == ["https://g1.globo.com/noticia"]  # spam fora
    assert "site:aosfatos.org" in calls[0]
    ddg.search("pergunta a")
    assert len(calls) == 1  # cache
    ddg.search("pergunta b")
    assert sleeps and sleeps[0] == pytest.approx(2.0)
    assert json.loads((tmp_path / "c.json").read_text())
