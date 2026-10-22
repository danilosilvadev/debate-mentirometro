"""Eventos do público (votos, super chats aprovados) gravados no Supabase durante o ao vivo
→ `eventos` no replay.json, no tempo do vídeo.

    PLACAR_MOD_TOKEN_FILE=... SUPABASE_URL=... SUPABASE_KEY=... \
        python -m placar.events_export <out_dir> <debate_key>
    python -m placar.events_export <out_dir> --mock     # dados simulados, rotulados

Mapeamento: segundo do vídeo = replay.inicio + (instante - video.t0) / 1000.
"""

from __future__ import annotations

import json
import random
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


def to_video(at_epoch_s: float, t0_ms: int, inicio: float) -> float:
    return round(inicio + (at_epoch_s * 1000 - t0_ms) / 1000, 1)


def bucket_votes(votos: list[dict[str, Any]], t0_ms: int, inicio: float, fim: float) -> list[dict[str, Any]]:
    """Agrupa por segundo e lado (o replay não precisa de cada clique)."""
    out: dict[tuple[float, str], int] = {}
    for v in votos:
        s = float(int(to_video(v["at"], t0_ms, inicio)))
        if inicio <= s <= fim:
            out[(s, v["side"])] = out.get((s, v["side"]), 0) + int(v["n"])
    return [{"s": s, "side": side, "n": n} for (s, side), n in sorted(out.items())]


def build_events(raw: dict[str, Any], replay: dict[str, Any]) -> dict[str, Any]:
    t0 = int(replay["video"]["t0"])
    inicio = float(replay["replay"]["inicio"])
    fim = float(replay["replay"]["fim"])
    chats = [{"s": to_video(c["at"], t0, inicio), "nome": c["nome"], "mensagem": c["mensagem"],
              "valor_centavos": c["valor_centavos"], "teste": bool(c.get("teste"))} for c in raw.get("superchats") or []]
    return {"simulado": False, "votos": bucket_votes(raw.get("votos") or [], t0, inicio, fim),
            "superchats": [c for c in chats if inicio <= c["s"] <= fim]}


def mock_events(replay: dict[str, Any], seed: int = 7) -> dict[str, Any]:
    """Torcida e super chats fictícios para testar o replay. Sempre rotulados como simulados."""
    rnd = random.Random(seed)
    inicio, fim = float(replay["replay"]["inicio"]), float(replay["replay"]["fim"])
    claims = [c for g in replay.get("fatos") or [] for c in g.get("declaracoes") or []]
    votos = []
    for s in range(int(inicio), int(fim)):
        for side in ("1", "2"):
            # mais torcida logo depois das checagens daquele lado
            boost = sum(1 for c in claims if c.get("quem") == side and 0 <= s - (c.get("vv") or c.get("vs") or -99) < 8)
            n = sum(1 for _ in range(3 + 6 * boost) if rnd.random() < 0.18)
            if n:
                votos.append({"s": float(s), "side": side, "n": n})
    msgs = ["Que debate! Boa checagem 👏", "Fontes na tela ajudam muito.", "Quero ver a checagem dos números!",
            "Mandando um abraço de Recife!", "Placar justo, parabéns ao projeto."]
    chats = []
    for i, m in enumerate(msgs):
        s = round(inicio + (fim - inicio) * (i + 1) / (len(msgs) + 1), 1)
        chats.append({"s": s, "nome": f"Teste {i + 1}", "mensagem": m, "valor_centavos": [500, 1000, 2000, 5000, 1000][i], "teste": True})
    return {"simulado": True, "aviso": "Eventos simulados para teste do replay.", "votos": votos, "superchats": chats}


def fetch_raw(debate: str, replay: dict[str, Any]) -> dict[str, Any]:
    import os

    from placar.superchat import Rpc

    token = Path(os.environ["PLACAR_MOD_TOKEN_FILE"]).read_text().strip()
    rpc = Rpc(os.environ["SUPABASE_URL"], os.environ["SUPABASE_KEY"])
    t0 = int(replay["video"]["t0"]) / 1000
    span = float(replay["replay"]["fim"]) - float(replay["replay"]["inicio"])
    iso = lambda x: datetime.fromtimestamp(x, tz=timezone.utc).isoformat()  # noqa: E731
    return rpc.call("export_events", {"p_token": token, "p_debate": debate, "p_desde": iso(t0 - 60), "p_ate": iso(t0 + span + 600)})


def main(argv: list[str]) -> int:
    out = Path(argv[0])
    path = out / "replay.json"
    replay = json.loads(path.read_text(encoding="utf-8"))
    replay["eventos"] = mock_events(replay) if argv[1] == "--mock" else build_events(fetch_raw(argv[1], replay), replay)
    path.write_text(json.dumps(replay, ensure_ascii=False), encoding="utf-8")
    ev = replay["eventos"]
    print(json.dumps({"votos": sum(v["n"] for v in ev["votos"]), "superchats": len(ev["superchats"]), "simulado": ev["simulado"]}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
