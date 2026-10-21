"""Extrai e conserta JSON de resposta de modelo antes de validar o schema."""

from __future__ import annotations

import json
import re
from typing import Any

import jsonschema


class InvalidJson(Exception):
    def __init__(self, message: str) -> None:
        super().__init__(message)
        self.message = message


_FENCE = re.compile(r"```(?:json)?\s*(.*?)```", re.DOTALL | re.IGNORECASE)


def extract_json(text: str) -> Any:
    raw = text.strip()
    fenced = _FENCE.search(raw)
    if fenced:
        raw = fenced.group(1).strip()
    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        pass
    start = raw.find("{")
    end = raw.rfind("}")
    if start >= 0 and end > start:
        try:
            return json.loads(raw[start : end + 1])
        except json.JSONDecodeError as exc:
            raise InvalidJson(f"JSON inválido: {exc}") from exc
    raise InvalidJson("A resposta não contém um objeto JSON.")


def _drop_unknown(data: Any, schema: dict) -> Any:
    if not isinstance(data, dict) or schema.get("type") != "object":
        return data
    props = schema.get("properties") or {}
    if schema.get("additionalProperties") is False:
        data = {key: value for key, value in data.items() if key in props}
    for key, sub in props.items():
        if key in data and isinstance(sub, dict):
            data[key] = _drop_unknown(data[key], sub)
    return data


def _fill_defaults(data: dict, schema: dict) -> dict:
    props = schema.get("properties") or {}
    for key, sub in props.items():
        if key in data or not isinstance(sub, dict):
            continue
        if "default" in sub:
            data[key] = sub["default"]
        elif (
            sub.get("type") == "string"
            and key not in schema.get("required", [])
            and "enum" not in sub
        ):
            data[key] = ""
    return data


def validate(data: Any, schema: dict) -> dict:
    if not isinstance(data, dict):
        raise InvalidJson("O JSON precisa ser um objeto.")
    repaired = _fill_defaults(_drop_unknown(dict(data), schema), schema)
    try:
        jsonschema.validate(repaired, schema)
    except jsonschema.ValidationError as exc:
        raise InvalidJson(exc.message) from exc
    return repaired


def parse_model_json(text: str, schema: dict) -> dict:
    return validate(extract_json(text), schema)
