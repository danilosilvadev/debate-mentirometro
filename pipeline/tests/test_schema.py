import json

import jsonschema
import pytest

from placar.jsonrepair import InvalidJson, parse_model_json
from placar.schemas import CLASSIFY_SCHEMA, EVENT_SCHEMA, JUDGE_SCHEMA, PLACAR_SCHEMA


def test_aceita_json_dentro_de_cerca_markdown():
    raw = """claro
```json
{"tipo": "ataque", "tema": "conduta", "extra": 1}
```
"""
    data = parse_model_json(raw, CLASSIFY_SCHEMA)
    assert data["tipo"] == "ataque"
    assert "extra" not in data


def test_rejeita_veredito_fora_do_enum():
    with pytest.raises(InvalidJson):
        parse_model_json('{"veredito": "talvez", "motivo": "x"}', JUDGE_SCHEMA)


def test_evento_exige_seq_e_tipo():
    event = {
        "v": 1,
        "debate_id": "sintetico-2026",
        "seq": 1,
        "t": 1700000000000,
        "type": "ataque.created",
        "quem": "2",
        "payload": {"resumo": "x"},
    }
    jsonschema.validate(event, EVENT_SCHEMA)
    broken = dict(event)
    broken["type"] = "outra.coisa"
    with pytest.raises(jsonschema.ValidationError):
        jsonschema.validate(broken, EVENT_SCHEMA)


def test_placar_minimo_fecha_o_schema():
    body = {
        "atualizado": 1,
        "candidatos": {"1": {"nome": "Lula"}},
        "fatos": [],
        "propostas": [],
        "ataques": [],
        "linha": {},
    }
    jsonschema.validate(body, PLACAR_SCHEMA)
    json.dumps(body)
