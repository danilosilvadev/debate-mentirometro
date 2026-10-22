#!/usr/bin/env python3
"""Copia private.subscribers (Supabase) para um SQLite local, com upsert idempotente.

Lê via RPC public.export_subscribers protegida por segredo (só o hash fica no banco).
Segredo: arquivo SUBSCRIBERS_EXPORT_SECRET_FILE (padrão /workspace/data/.export_secret, chmod 600).
Saída: SUBSCRIBERS_DB (padrão /workspace/data/subscribers.sqlite, chmod 600). Nunca vai para o git.
"""
import hashlib, json, os, sqlite3, sys, urllib.request, pathlib

ROOT = pathlib.Path(__file__).resolve().parents[2]
DB = os.environ.get("SUBSCRIBERS_DB", "/workspace/data/subscribers.sqlite")
SECRET_FILE = os.environ.get("SUBSCRIBERS_EXPORT_SECRET_FILE", "/workspace/data/.export_secret")
URL = os.environ.get("SUPABASE_URL", "https://igpkunwxmtopdqtbsuso.supabase.co")
KEY = os.environ.get("SUPABASE_ANON_KEY", "sb_publishable_KdJP5K5oLFPEZfkaYv81pw_OjdZ_5aR")  # publicável
SCHEMA = (ROOT / "cloudflare/d1/0001_subscribers.sql").read_text()

def fetch(secret):
    req = urllib.request.Request(f"{URL}/rest/v1/rpc/export_subscribers", json.dumps({"p_secret": secret}).encode(),
        {"apikey": KEY, "Authorization": f"Bearer {KEY}", "Content-Type": "application/json"}, method="POST")
    with urllib.request.urlopen(req, timeout=30) as r: return json.load(r)

def open_db(path=DB):
    os.makedirs(os.path.dirname(path), mode=0o700, exist_ok=True)
    old = os.umask(0o077); con = sqlite3.connect(path); os.umask(old); os.chmod(path, 0o600)
    con.executescript(SCHEMA); return con

def upsert(con, rows):
    for r in rows:
        if isinstance(r, str): r = json.loads(r)
        ver = "sha256:" + hashlib.sha256((r.get("consent_text") or "").encode()).hexdigest()[:12]
        con.execute("""INSERT INTO subscribers(id,email,whatsapp_e164,consent_email,consent_whatsapp,consent_text_version,created_at,ip_hash,source,debate,reminded_email_at,reminded_whatsapp_at)
          VALUES(?,?,?,?,?,?,?,?,'supabase',?,?,?)
          ON CONFLICT(id) DO UPDATE SET email=excluded.email, whatsapp_e164=excluded.whatsapp_e164, consent_email=excluded.consent_email,
            consent_whatsapp=excluded.consent_whatsapp, consent_text_version=excluded.consent_text_version,
            reminded_email_at=coalesce(subscribers.reminded_email_at, excluded.reminded_email_at),
            reminded_whatsapp_at=coalesce(subscribers.reminded_whatsapp_at, excluded.reminded_whatsapp_at)""",
          (r["id"], r.get("email"), r.get("whatsapp"), int(bool(r.get("email_consent"))), int(bool(r.get("whatsapp_consent"))), ver,
           r["at"], r.get("ip_hash"), r.get("debate") or "globo-2026-10-23", r.get("reminded_email_at"), r.get("reminded_whatsapp_at")))
    # remove o que foi apagado na origem (pedido de exclusão LGPD)
    ids = [ (json.loads(r) if isinstance(r, str) else r)["id"] for r in rows ]
    if ids: con.execute(f"DELETE FROM subscribers WHERE source='supabase' AND id NOT IN ({','.join('?'*len(ids))})", ids)
    else: con.execute("DELETE FROM subscribers WHERE source='supabase'")
    con.commit()

def main():
    secret = pathlib.Path(SECRET_FILE).read_text().strip()
    rows = fetch(secret); con = open_db(); upsert(con, rows)
    n = con.execute("SELECT count(*) FROM subscribers").fetchone()[0]
    print(json.dumps({"synced": len(rows), "total_local": n}))

if __name__ == "__main__": sys.exit(main())
