"""Dev rápido: roda placar.turns.process_turn (código do worktree WT) direto nos turnos
salvos (stt/jobs.jsonl, vindos do SQLite; nada retranscrito). usage: turn_eval.py NAME WT [tune|held|all]
env PLACAR_BANK_EXCLUDE etc. Pontuação com score.py (velocidade 1, t0=0)."""
import json, os, sys, threading, time
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
name, wt, part = sys.argv[1], sys.argv[2], (sys.argv[3] if len(sys.argv) > 3 else "tune")
sys.path.insert(0, f"{wt}/pipeline")
from placar.config import Settings
from placar.replay import build_router
from placar.retrieve import Retriever
from placar.board import Board
from placar.turns import process_turn
E = Path("/workspace/data/eval"); out = E / "runs" / name; out.mkdir(parents=True, exist_ok=True)
jobs = [json.loads(l) for l in open(E / "stt/jobs.jsonl")]
lo, hi = {"tune": (0, 3300), "held": (3300, 1e9), "all": (0, 1e9)}[part]
jobs = [j for j in jobs if lo <= j["t_s"] < hi and j["quem"] in ("1", "2")]
s = Settings.from_env(); router = build_router(s); retr = Retriever(s)
board = Board(debate_id="band-2026-10-18", candidatos={"1": "Lula", "2": "Flávio Bolsonaro"}, origin_ms=0, video={"t0": 0}, aviso="")
lock = threading.Lock(); log = []
def run(j):
    t = {**j, "t_ms": int(j["t_s"] * 1000)}; t.pop("clock", None)
    t0 = time.time()
    try:
        r = process_turn(board, t, router, retr, lock=lock)
        rec = {"t_s": j["t_s"], "quem": j["quem"], "items": r.items, "error": r.error, "verdicts": r.verdicts, "s": round(time.time()-t0, 1), "text": j["text"][:300]}
    except Exception as e:
        rec = {"t_s": j["t_s"], "quem": j["quem"], "exc": repr(e)[:200], "text": j["text"][:300]}
    with lock: log.append(rec)
with ThreadPoolExecutor(int(os.environ.get("DEV_PAR", "4"))) as ex:
    list(ex.map(run, jobs))
snap = board.snapshot(); snap["video"] = {**snap.get("video", {}), "t0": 0}
(out / "placar.json").write_text(json.dumps(snap, ensure_ascii=False))
(out / "turns.json").write_text(json.dumps(sorted(log, key=lambda x: x["t_s"]), ensure_ascii=False, indent=1))
print(name, "done", len(jobs), flush=True)
