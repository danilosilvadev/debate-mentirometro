#!/usr/bin/env python3
"""Fonte padrão: $PLACAR_DATA_DIR/subscribers.sqlite (padrão ~/.local/share/placar; tools/subscribers/sync_sqlite.py).
Envia o lembrete do debate para os inscritos (e-mail e WhatsApp). Padrão: --dry-run (não envia nada).

Fonte: Supabase (private.subscribers) via REST com SUPABASE_SERVICE_ROLE_KEY, ou --csv para testes.
WhatsApp: WhatsApp Cloud API, mensagem de TEMPLATE aprovado (obrigatório fora da janela de 24 h).
E-mail: provedor plugável (Resend por padrão; troque em send_email).

Env (só com --send):
  SUPABASE_URL, SUPABASE_SERVICE_ROLE_KEY
  WA_PHONE_NUMBER_ID, WA_TOKEN, WA_TEMPLATE (ex.: lembrete_debate), WA_LANG (pt_BR)
  RESEND_API_KEY, EMAIL_FROM
"""
import argparse, csv, json, os, pathlib, sqlite3, sys, time, urllib.request

DATA_DIR = pathlib.Path(os.environ.get("PLACAR_DATA_DIR", pathlib.Path.home() / ".local/share/placar"))

LIVE_URL = os.environ.get("LIVE_URL", "https://danilosilvadev.github.io/debate-mentirometro/?live=1")
SUBJECT = "Começa já: debate da Globo checado ao vivo"
BODY = "O debate do 2º turno na TV Globo começa às 21h20 (Brasília). Assista com checagem ao vivo: {url}\n\nPara não receber mais, responda este e-mail com SAIR."

def post(url, headers, body):
    req = urllib.request.Request(url, json.dumps(body).encode(), {**headers, "Content-Type": "application/json"}, method="POST")
    with urllib.request.urlopen(req, timeout=20) as r: return r.status

def load(args):
    if args.csv: args.sqlite = None
    if args.sqlite:
        import sqlite3; con = sqlite3.connect(args.sqlite); con.row_factory = sqlite3.Row
        return [{"email": r["email"], "whatsapp": r["whatsapp_e164"], "email_consent": bool(r["consent_email"]),
                 "whatsapp_consent": bool(r["consent_whatsapp"]), "reminded_email_at": r["reminded_email_at"],
                 "reminded_whatsapp_at": r["reminded_whatsapp_at"]}
                for r in con.execute("SELECT * FROM subscribers WHERE debate = ?", (args.debate,))]
    if args.csv:
        with open(args.csv) as f: return list(csv.DictReader(f))
    url = os.environ["SUPABASE_URL"].rstrip("/"); key = os.environ["SUPABASE_SERVICE_ROLE_KEY"]
    q = f"{url}/rest/v1/subscribers?debate=eq.{args.debate}&select=id,email,whatsapp,email_consent,whatsapp_consent,reminded_email_at,reminded_whatsapp_at"
    req = urllib.request.Request(q, headers={"apikey": key, "Authorization": f"Bearer {key}", "Accept-Profile": "private"})
    with urllib.request.urlopen(req, timeout=20) as r: return json.load(r)

def send_wa(to):
    pid, tok = os.environ["WA_PHONE_NUMBER_ID"], os.environ["WA_TOKEN"]
    return post(f"https://graph.facebook.com/v21.0/{pid}/messages", {"Authorization": f"Bearer {tok}"}, {
        "messaging_product": "whatsapp", "to": to.lstrip("+"), "type": "template",
        "template": {"name": os.environ.get("WA_TEMPLATE", "lembrete_debate"), "language": {"code": os.environ.get("WA_LANG", "pt_BR")},
                     "components": [{"type": "body", "parameters": [{"type": "text", "text": LIVE_URL}]}]}})

def send_email(to):
    reply = os.environ.get("EMAIL_REPLY_TO") or os.environ["EMAIL_FROM"]
    body = {"from": os.environ["EMAIL_FROM"], "to": [to], "subject": SUBJECT, "text": BODY.format(url=LIVE_URL),
            "reply_to": reply, "headers": {"List-Unsubscribe": f"<mailto:{reply.split('<')[-1].rstrip('>')}?subject=SAIR>"}}
    return post("https://api.resend.com/emails", {"Authorization": f"Bearer {os.environ['RESEND_API_KEY']}"}, body)

def truthy(v): return v in (True, "true", "t", "1", 1)

def plan(rows):
    out = []
    for r in rows:
        if r.get("email") and truthy(r.get("email_consent")) and not r.get("reminded_email_at"): out.append(("email", r["email"]))
        if r.get("whatsapp") and truthy(r.get("whatsapp_consent")) and not r.get("reminded_whatsapp_at"): out.append(("whatsapp", r["whatsapp"]))
    return out

def mark(db, ch, to):
    """Grava que o lembrete saiu, para um segundo --send não repetir."""
    col, key = ("reminded_email_at", "email") if ch == "email" else ("reminded_whatsapp_at", "whatsapp_e164")
    con = sqlite3.connect(db); con.execute(f"UPDATE subscribers SET {col}=datetime('now') WHERE {key}=?", (to,)); con.commit(); con.close()

def mask(x): return x[:2] + "***" + x[-4:]

def main(argv=None):
    ap = argparse.ArgumentParser(); ap.add_argument("--debate", default="globo-2026-10-23"); ap.add_argument("--csv")
    ap.add_argument("--sqlite", default=None if os.environ.get("NO_SQLITE") else str(DATA_DIR / "subscribers.sqlite"), help="padrão: SQLite sincronizado")
    ap.add_argument("--send", action="store_true", help="envia de verdade (sem isto é dry-run)")
    ap.add_argument("--only", choices=("email", "whatsapp"), help="só um canal")
    ap.add_argument("--limit", type=int, default=0, help="no máximo N envios nesta rodada (0 = todos)")
    ap.add_argument("--sleep", type=float, default=float(os.environ.get("SEND_SLEEP_S", "0.6")), help="pausa entre envios (limite de taxa do provedor)")
    ap.add_argument("--to", help="teste: manda UMA mensagem a este e-mail e sai, sem marcar ninguém")
    a = ap.parse_args(argv)
    if a.to:
        print(json.dumps({"teste": mask(a.to), "status": send_email(a.to)})); return 0
    jobs = plan(load(a))
    if a.only: jobs = [j for j in jobs if j[0] == a.only]
    if a.limit: jobs = jobs[:a.limit]
    ok = fail = 0
    for ch, to in jobs:
        if not a.send: print(f"[dry-run] {ch} -> {mask(to)}"); continue
        try:
            (send_wa if ch == "whatsapp" else send_email)(to); ok += 1
            if a.sqlite and not a.csv: mark(a.sqlite, ch, to)
        except Exception as e: fail += 1; print(f"falhou {ch} {mask(to)}: {e}", file=sys.stderr)
        time.sleep(a.sleep)
    print(json.dumps({"total": len(jobs), "enviados": ok, "falhas": fail, "dry_run": not a.send}))
    return 1 if fail and not ok else 0

if __name__ == "__main__": sys.exit(main())
