"""Correções de QA manual revisadas, aplicadas ao replay gravado (nunca ao vivo).

    python -m placar.qa_apply <out_dir> placar/data/qa/<debate>.json

Cada item: {"id": "c12" | "match": {"literal": "trecho", "quem": "1"}, "set": {"veredito", "motivo",
"fonte": {"titulo","url"}, "afirmacao"?, "quem"?}, "remover"?: true, "nota": "por que"}.
A afirmação corrigida recebe `corrigido = {"antes": <veredito do pipeline>, "por": "qa_manual", "nota"}`
e o site mostra "Corrigido na revisão humana". Itens sem correspondência fazem o comando falhar.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path


def _find(claims, item):
    if item.get("id"):
        return [c for c in claims if c.get("id") == item["id"]]
    m = item["match"]
    lit = m["literal"].lower()
    return [c for c in claims if lit in (c.get("literal", "") + " " + c.get("afirmacao", "")).lower()
            and (not m.get("quem") or c["quem"] == m["quem"])]


def apply(data: dict, items: list[dict]) -> list[str]:
    claims = [c for f in data["fatos"] for c in f["declaracoes"]]
    missing = []
    for item in items:
        hits = _find(claims, item)
        if not hits:
            missing.append(item.get("id") or item["match"]["literal"])
            continue
        for c in hits:
            if item.get("remover"):
                c["_remover"] = True
                continue
            before = c["veredito"]
            for k, v in (item.get("set") or {}).items():
                c[k] = v
            c["corrigido"] = {"antes": before, "por": "qa_manual", "nota": item.get("nota", "")}
    for f in data["fatos"]:
        f["declaracoes"] = [c for c in f["declaracoes"] if not c.get("_remover")]
    data["fatos"] = [f for f in data["fatos"] if f["declaracoes"]]
    for k, cand in data.get("candidatos", {}).items():
        for v in ("verdadeiro", "impreciso", "falso", "sem_dados"):
            cand[v] = sum(1 for f in data["fatos"] for c in f["declaracoes"] if c["quem"] == k and c["veredito"] == v)
    data["qa"] = {"correcoes_manuais": sum(1 for f in data["fatos"] for c in f["declaracoes"]
                                           if (c.get("corrigido") or {}).get("por") == "qa_manual"),
                  "removidas": sum(1 for i in items if i.get("remover"))}
    return missing


def main(out_dir: str, qa_file: str) -> None:
    items = json.loads(Path(qa_file).read_text(encoding="utf-8"))["itens"]
    for name in ("replay.json", "placar.json"):
        p = Path(out_dir) / name
        if not p.exists():
            continue
        data = json.loads(p.read_text(encoding="utf-8"))
        missing = apply(data, items)
        if missing:
            raise SystemExit(f"{name}: sem correspondência para {missing}")
        p.write_text(json.dumps(data, ensure_ascii=False), encoding="utf-8")
        print(name, data["qa"])


if __name__ == "__main__":
    main(sys.argv[1], sys.argv[2])
