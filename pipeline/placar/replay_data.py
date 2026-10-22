"""Dados de replay: cada item do placar ganha `vs` (segundo do vídeo-fonte em que a frase
foi dita) e o arquivo leva as falas transcritas (`linhas`) para a legenda.

O site, em ?replay=<id>, mostra só o que tem `vs` <= tempo atual do player.
"""

from __future__ import annotations

import json
import re
import unicodedata
from pathlib import Path
from typing import Any


def _words(text: str) -> list[str]:
    folded = unicodedata.normalize("NFKD", text.lower())
    folded = "".join(c for c in folded if not unicodedata.combining(c))
    return re.findall(r"[a-z0-9]+", folded)


def _match(quote: str, lines: list[dict[str, Any]], lo: float, hi: float) -> float | None:
    """Segundo (fim da fala) da linha que mais contém as palavras da citação, dentro do turno."""
    target = set(_words(quote))
    if not target:
        return None
    best_end, best_score = None, 0.0
    window = [ln for ln in lines if lo - 1 <= ln["s"] <= hi]
    for i, line in enumerate(window):
        options = [(len(target & set(_words(line["text"]))) / len(target), line["e"])]
        if i + 1 < len(window):  # citação que atravessa dois segmentos: conta no fim do segundo
            nxt = window[i + 1]
            joined = set(_words(line["text"] + " " + nxt["text"]))
            options.append((len(target & joined) / len(target) - 1e-6, nxt["e"]))
        for score, end in options:
            if score > best_score + 1e-9:
                best_end, best_score = end, score
    if best_end is None or best_score < 0.4:
        return None
    return round(best_end, 1)


def build(snapshot: dict[str, Any], transcript: list[dict[str, Any]], *, offset_s: float = 0.0,
          turn_max_s: float = 60.0) -> dict[str, Any]:
    t0 = int((snapshot.get("video") or {}).get("t0") or 0)
    lines = [{"s": round(x["t_s"], 2), "e": round(x["t_s"] + x["dur_s"], 2), "quem": x.get("slot", "other"),
              "voz": x.get("voz", ""), "text": x["text"]} for x in transcript]
    out = json.loads(json.dumps(snapshot))

    def place(item: dict[str, Any], quote: str) -> None:
        start = offset_s + (int(item["t"]) - t0) / 1000 if t0 else offset_s
        vs = _match(quote, lines, start, start + turn_max_s)
        item["vs"] = vs if vs is not None else round(start, 1)

    for group in out.get("fatos") or []:
        for claim in group.get("declaracoes") or []:
            place(claim, claim.get("literal") or claim.get("afirmacao") or "")
    for prop in out.get("propostas") or []:
        place(prop, prop.get("explicacao") or prop.get("titulo") or "")
    for atk in out.get("ataques") or []:
        quote = re.search(r"“(.*)”", atk.get("resumo") or "")
        place(atk, quote.group(1) if quote else atk.get("resumo") or "")
    out["replay"] = {"video": (snapshot.get("video") or {}).get("id", ""), "inicio": offset_s,
                     "fim": lines[-1]["e"] if lines else offset_s}
    out["linhas"] = lines
    return out


def write(out_dir: Path, *, offset_s: float = 0.0) -> Path:
    snapshot = json.loads((out_dir / "placar.json").read_text(encoding="utf-8"))
    transcript = json.loads((out_dir / "transcript.json").read_text(encoding="utf-8"))
    data = build(snapshot, transcript, offset_s=offset_s)
    dest = out_dir / "replay.json"
    dest.write_text(json.dumps(data, ensure_ascii=False), encoding="utf-8")
    return dest


if __name__ == "__main__":  # python -m placar.replay_data <out_dir> [offset_s]
    import sys

    print(write(Path(sys.argv[1]), offset_s=float(sys.argv[2]) if len(sys.argv) > 2 else 0.0))
