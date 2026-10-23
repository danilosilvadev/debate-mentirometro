import json, sys, unicodedata
from pathlib import Path
E = Path("/workspace/data/eval")
fold = lambda s: unicodedata.normalize("NFKD", (s or "").lower()).encode("ascii", "ignore").decode()
gold = json.load(open("/workspace/debate-mentirometro/pipeline/placar/data/qa/gold-band.json"))["itens"]
jobs = [json.loads(l) for l in open(E / "stt/jobs.jsonl")]
tms = {j["t_ms"]: j["t_s"] for j in jobs}
SLOT = {"lula": "1", "flavio": "2"}; SPLIT = 3300
def has(text, keys): t = fold(text); return all(fold(k) in t for k in keys)
def gold_t(g):
    for j in jobs:
        if j["quem"] == SLOT[g["quem"]] and has(j["text"], g["k"]): return j["t_s"]
    return None
def score(name):
    d = json.load(open(E / "runs" / name / "placar.json"))
    cl = [x for f in d["fatos"] for x in f["declaracoes"]]
    t0 = d["video"]["t0"]; sp = float(__import__("os").environ.get("EVAL_SPEED", "3"))
    for c in cl: c["_ts"] = (c["t"] - t0) / 1000 * sp
    used, rows = set(), []
    for g in gold:
        m = [c for c in cl if c["quem"] == SLOT[g["quem"]] and c["id"] not in used and
             has(f"{c.get('literal','')} {c.get('afirmacao','')}", g["k"])]
        m.sort(key=lambda c: c["_ts"]); c = m[0] if m else None
        if c: used.add(c["id"])
        rows.append((g, c, c["_ts"] if c else gold_t(g)))
    res = {}
    for half, ok in (("tune", lambda t: t is not None and t < SPLIT), ("held", lambda t: t is None or t >= SPLIT), ("all", lambda t: True)):
        R = [r for r in rows if ok(r[2])]
        dec = [r for r in R if r[1] and r[1]["veredito"] in ("verdadeiro", "impreciso", "falso")]
        cor = [r for r in dec if r[1]["veredito"] == r[0]["v"]]
        wf = [r for r in dec if r[1]["veredito"] == "falso" and r[0]["v"] != "falso"]
        res[half] = dict(gold=len(R), matched=sum(1 for r in R if r[1]), decided=len(dec), correct=len(cor),
                         acc=round(len(cor)/len(dec), 3) if dec else None, wrong_falso=len(wf),
                         coverage=round(sum(1 for r in R if r[1])/len(R), 3) if R else None)
    extra = [c for c in cl if c["id"] not in used]
    def _src_ok(c):
        f = c.get("fonte") or {}
        return isinstance(f, dict) and str(f.get("url") or "").startswith(("http://", "https://"))
    res["no_source"] = sum(1 for c in cl if c["veredito"] in ("verdadeiro", "impreciso", "falso") and not _src_ok(c))
    res["unmatched_claims"] = len(extra); res["total_claims"] = len(cl)
    res["by_verdict"] = {v: sum(1 for c in cl if c["veredito"] == v) for v in {c["veredito"] for c in cl}}
    res["errors"] = [(r[0]["g"], r[0]["v"], r[1]["veredito"], (r[1].get("literal") or "")[:80]) for r in rows
                     if r[1] and r[1]["veredito"] in ("verdadeiro","impreciso","falso") and r[1]["veredito"] != r[0]["v"]]
    res["extras"] = [(c["quem"], c["veredito"], round(c["_ts"]), (c.get("literal") or "")[:80]) for c in extra]
    return res
if __name__ == "__main__":
    for n in sys.argv[1:]:
        r = score(n); json.dump(r, open(E / "runs" / n / "score.json", "w"), ensure_ascii=False, indent=1)
        print(n, {k: r[k] for k in ("tune", "held", "all", "total_claims", "unmatched_claims", "by_verdict")})
