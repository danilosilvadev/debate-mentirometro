#!/usr/bin/env python3
"""Envia o lembrete do debate para os inscritos (e-mail e WhatsApp). Padrão: --dry-run (não envia nada).

Fonte: Supabase (private.subscribers) via REST com SUPABASE_SERVICE_ROLE_KEY, ou --csv para testes.
WhatsApp: WhatsApp Cloud API, mensagem de TEMPLATE aprovado (obrigatório fora da janela de 24 h).
E-mail: provedor plugável (Resend por padrão; troque em send_email).

Env (só com --send):
  SUPABASE_URL, SUPABASE_SERVICE_ROLE_KEY
  WA_PHONE_NUMBER_ID, WA_TOKEN, WA_TEMPLATE (ex.: lembrete_debate), WA_LANG (pt_BR)
  RESEND_API_KEY, EMAIL_FROM
"""
import argparse, csv, json, os, sys, urllib.request

LIVE_URL = os.environ.get("LIVE_URL", "https://danilosilvadev.github.io/debate-mentirometro/?live=1")
SUBJECT = "Começa já: debate da Globo checado ao vivo"
BODY = "O debate do 2º turno na TV Globo começa às 21h20 (Brasília). Assista com checagem ao vivo: {url}\n\nPara cancelar, responda SAIR."

def post(url, headers, body):
    req = urllib.request.Request(url, json.dumps(body).encode(), {**headers, "Content-Type": "application/json"}, method="POST")
    with urllib.request.urlopen(req, timeout=20) as r: return r.status

def load(args):
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
    return post("https://api.resend.com/emails", {"Authorization": f"Bearer {os.environ['RESEND_API_KEY']}"},
                {"from": os.environ["EMAIL_FROM"], "to": [to], "subject": SUBJECT, "text": BODY.format(url=LIVE_URL)})

def truthy(v): return v in (True, "true", "t", "1", 1)

def plan(rows):
    out = []
    for r in rows:
        if r.get("email") and truthy(r.get("email_consent")) and not r.get("reminded_email_at"): out.append(("email", r["email"]))
        if r.get("whatsapp") and truthy(r.get("whatsapp_consent")) and not r.get("reminded_whatsapp_at"): out.append(("whatsapp", r["whatsapp"]))
    return out

def mask(x): return x[:2] + "***" + x[-4:]

def main(argv=None):
    ap = argparse.ArgumentParser(); ap.add_argument("--debate", default="globo-2026-10-23"); ap.add_argument("--csv")
    ap.add_argument("--send", action="store_true", help="envia de verdade (sem isto é dry-run)")
    a = ap.parse_args(argv); jobs = plan(load(a)); ok = fail = 0
    for ch, to in jobs:
        if not a.send: print(f"[dry-run] {ch} -> {mask(to)}"); continue
        try: (send_wa if ch == "whatsapp" else send_email)(to); ok += 1
        except Exception as e: fail += 1; print(f"falhou {ch} {mask(to)}: {e}", file=sys.stderr)
    print(json.dumps({"total": len(jobs), "enviados": ok, "falhas": fail, "dry_run": not a.send}))
    return 0

if __name__ == "__main__": sys.exit(main())
