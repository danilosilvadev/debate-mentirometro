from placar.audio_replay import magnitudes, reconcile_numbers
from placar.board import Board
from placar.transcribe import TranscriptSegment as S
from placar.turns import is_duplicate, is_garbled


def test_reconcile_fixes_magnitude_word():
    out, fixes = reconcile_numbers([S(0, 4, "nós fizemos 270 milhões de redes")],
                                   [S(0, 4, "nós fizemos 270 bilhões de reservas")])
    assert "bilhões" in out[0].text and fixes
    assert magnitudes("11 trilhões e 3%") == {"tril", "%"}


def test_garbled_quote_not_in_turn_is_dropped():
    turn = "ele já foi presa da Taubea e não deu certo"
    assert is_garbled({"titulo": "Lula foi preso em Taubaté", "citacao": "Lula foi preso em Taubaté"}, turn)
    assert is_garbled({"titulo": "PIB cresceu 9%", "citacao": "ele já foi presa da Taubea"}, turn)
    ok = "bancarizamos 22 milhões de brasileiros"
    assert not is_garbled({"titulo": "22 milhões bancarizados", "citacao": ok}, ok)


def test_duplicate_same_speaker():
    b = Board(debate_id="t", candidatos={"1": "Lula", "2": "B"}, origin_ms=0, video={}, aviso="")
    c = b.open_claim(quem="1", tema="x", afirmacao="Flávio comprou casa de 10 milhões",
                     contexto="", literal="comprou a casa de 10 milhões e pagou à vista", t_ms=1000)
    c["_banco_frase"] = "casa de 10 milhões"
    assert is_duplicate(b, "1", 60000, "casa", "x", banco="casa de 10 milhões")
    assert is_duplicate(b, "1", 60000, "Flávio comprou casa de 10 milhões", "comprou uma casa de 10 milhões")
    assert not is_duplicate(b, "2", 60000, "Flávio comprou casa de 10 milhões", "")


def test_official_evidence_offline(monkeypatch):
    from placar import official
    monkeypatch.setattr(official, "_CACHE", {})
    def fake(url, timeout_s=6.0):
        if "bcdata.sgs.3546" in url and "2009" in url:
            return [{"data": "01/12/2010", "valor": "288575"}]
        if "bcdata" in url:
            return []
        raise AssertionError(url)
    monkeypatch.setattr(official, "_get", fake)
    ev = official.official_evidence("nós fizemos 270 bilhões de reservas")
    assert ev and "288,6 bilhões" in ev[0].trecho and ev[0].url.startswith("https://api.bcb.gov.br")
    assert official.official_evidence("não tem número aqui") == []


def test_factcheck_rating_in_snippet_and_graceful():
    import json
    from placar.config import Settings
    from placar.retrieve import Retriever
    body = {"claims": [{"text": "PIB cresceu 7,5%", "claimant": "Lula", "claimReview": [
        {"publisher": {"name": "Aos Fatos"}, "url": "https://www.aosfatos.org/x", "title": "t", "textualRating": "Verdadeiro"}]}]}
    r = Retriever(Settings(factcheck_key="k"), http=lambda u, t: (200, json.dumps(body)))
    ev = r._factcheck("pib", 5)
    assert "Verdadeiro" in ev[0].trecho and "languageCode=pt&" in "languageCode=pt&"
    def boom(u, t):
        raise OSError("rede")
    assert Retriever(Settings(factcheck_key="k"), http=boom)._factcheck("pib", 5) == []
