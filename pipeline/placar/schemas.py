"""Schemas do JSON que o app já lê, do evento e das respostas do modelo."""

from __future__ import annotations

VEREDICTO = {
    "type": "string",
    "enum": ["verdadeiro", "impreciso", "falso", "sem_dados", "em_revisao"],
}

CLASSIFY_SCHEMA = {
    "type": "object",
    "additionalProperties": False,
    "required": ["tipo", "tema"],
    "properties": {
        "tipo": {
            "type": "string",
            "enum": [
                "proposta",
                "ataque",
                "afirmacao_checavel",
                "defesa",
                "balanco",
                "outro",
            ],
        },
        "tema": {"type": "string"},
        "titulo": {"type": "string"},
        "explicacao": {"type": "string"},
        "resumo": {"type": "string"},
        "afirmacao": {"type": "string"},
        "contexto": {"type": "string"},
        "tom": {
            "type": "string",
            "enum": ["proposta", "ataque", "defesa", "balanco", "outro"],
        },
    },
}

JUDGE_SCHEMA = {
    "type": "object",
    "additionalProperties": False,
    "required": ["veredito", "motivo"],
    "properties": {
        "veredito": {
            "type": "string",
            "enum": ["verdadeiro", "impreciso", "falso", "sem_dados"],
        },
        "motivo": {"type": "string"},
        "fonte_titulo": {"type": "string"},
        "fonte_url": {"type": "string"},
    },
}

EVENT_TYPES = (
    "claim.created",
    "claim.updated",
    "proposta.created",
    "proposta.incremented",
    "ataque.created",
    "score.updated",
    "debate.status",
)

EVENT_SCHEMA = {
    "type": "object",
    "additionalProperties": False,
    "required": ["v", "debate_id", "seq", "t", "type", "payload"],
    "properties": {
        "v": {"const": 1},
        "debate_id": {"type": "string"},
        "seq": {"type": "integer"},
        "t": {"type": "integer"},
        "type": {"type": "string", "enum": list(EVENT_TYPES)},
        "quem": {"type": "string"},
        "payload": {"type": "object"},
    },
}

PLACAR_SCHEMA = {
    "type": "object",
    "required": [
        "atualizado",
        "candidatos",
        "fatos",
        "propostas",
        "ataques",
        "linha",
    ],
    "properties": {
        "atualizado": {"type": "integer"},
        "video": {"type": "object"},
        "candidatos": {"type": "object"},
        "fatos": {"type": "array"},
        "propostas": {"type": "array"},
        "ataques": {"type": "array"},
        "linha": {"type": "object"},
        "pausado": {"type": "boolean"},
        "encerrado": {"type": ["object", "null"]},
        "aviso": {"type": "string"},
    },
}
