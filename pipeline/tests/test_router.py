import json

import pytest

from placar.llm.base import CliFailure, LlmRequest, RateLimitFailure, TimeoutFailure
from placar.llm.router import ProviderRouter
from placar.schemas import CLASSIFY_SCHEMA

REQUEST = LlmRequest(
    task="classify",
    system="sistema",
    user="fala",
    schema=CLASSIFY_SCHEMA,
)
OK = json.dumps({"tipo": "outro", "tema": "geral"})


class Toy:
    def __init__(self, name, behavior):
        self.name = name
        self.behavior = behavior
        self.calls = 0

    def generate(self, request, timeout_s):
        self.calls += 1
        action = self.behavior[min(self.calls - 1, len(self.behavior) - 1)]
        if isinstance(action, Exception):
            raise action
        return action


def test_json_invalido_cai_no_fallback():
    primary = Toy("claude-cli", ["lixo", "ainda lixo"])
    backup = Toy("openrouter", [OK])
    router = ProviderRouter([primary, backup], retries=1, breaker_threshold=5)
    result = router.complete(REQUEST)
    assert result.provider == "openrouter"
    assert result.data["tipo"] == "outro"
    assert any(record.failover and record.ok for record in result.records)
    assert primary.calls == 2


def test_limite_de_uso_abre_o_breaker_e_nao_repete():
    clock = {"t": 0.0}
    primary = Toy("claude-cli", [RateLimitFailure("You've hit your limit")])
    backup = Toy("openrouter", [OK])
    router = ProviderRouter(
        [primary, backup],
        retries=3,
        breaker_threshold=5,
        breaker_cooldown_s=30,
        clock=lambda: clock["t"],
    )
    router.complete(REQUEST)
    assert primary.calls == 1
    assert router.breaker.open_for("claude-cli")
    clock["t"] = 10
    router.complete(REQUEST)
    assert primary.calls == 1
    clock["t"] = 31
    router.complete(REQUEST)
    assert primary.calls == 2


def test_timeout_repete_e_depois_faz_failover():
    primary = Toy("claude-cli", [TimeoutFailure("estourou"), TimeoutFailure("de novo")])
    backup = Toy("openrouter", [OK])
    router = ProviderRouter([primary, backup], retries=1, breaker_threshold=5)
    result = router.complete(REQUEST)
    assert result.provider == "openrouter"
    assert primary.calls == 2


def test_erro_de_cli_no_primeiro_tentativa_recuperada():
    primary = Toy("claude-cli", [CliFailure("caiu"), OK])
    router = ProviderRouter([primary], retries=1, breaker_threshold=5)
    result = router.complete(REQUEST)
    assert result.provider == "claude-cli"
    assert result.records[-1].attempt == 2
    assert result.records[-1].latency_ms >= 0


def test_todos_falham():
    primary = Toy("claude-cli", [CliFailure("caiu")])
    router = ProviderRouter([primary], retries=0, breaker_threshold=5)
    with pytest.raises(Exception, match="falharam"):
        router.complete(REQUEST)
