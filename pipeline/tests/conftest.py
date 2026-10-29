
import pytest


@pytest.fixture(autouse=True)
def _no_claim_bank(monkeypatch, request):
    """Testes de juiz não devem bater no banco de checagens (há teste próprio do banco)."""
    from placar import turns
    if "uses_bank" in request.keywords:
        monkeypatch.setattr(turns, "_BANK", None)
        monkeypatch.setenv("PLACAR_BANK", "1")
    else:
        monkeypatch.setattr(turns, "_BANK", turns.ClaimBank([]))


@pytest.fixture(autouse=True)
def _offline_support(monkeypatch):
    from placar import support
    monkeypatch.setattr(support, "FETCH", lambda url: "")


@pytest.fixture(autouse=True)
def _short_turns_ok(monkeypatch):
    from placar import turns
    monkeypatch.setattr(turns, "MIN_WORDS", 0)
