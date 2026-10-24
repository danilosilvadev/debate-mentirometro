"""Testes do envio de lembretes: marcação, dedupe, filtros e dry-run. Sem rede, sem segredos."""
import importlib.util, json, pathlib, sqlite3, sys

ROOT = pathlib.Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "tools/subscribers"))


def load(name, path):
    spec = importlib.util.spec_from_file_location(name, ROOT / path); mod = importlib.util.module_from_spec(spec); spec.loader.exec_module(mod); return mod


def make_db(tmp_path, rows):
    db = tmp_path / "s.sqlite"; con = sqlite3.connect(db)
    con.executescript((ROOT / "cloudflare/d1/0001_subscribers.sql").read_text())
    for i, (email, wa, ce, cw, rem) in enumerate(rows, 1):
        con.execute("INSERT INTO subscribers(id,email,whatsapp_e164,consent_email,consent_whatsapp,consent_text_version,created_at,source,reminded_email_at) VALUES(?,?,?,?,?,'v','2026-10-23','supabase',?)", (i, email, wa, ce, cw, rem))
    con.commit(); con.close(); return str(db)


ROWS = [("a@x.com", None, 1, 0, None), ("b@x.com", "+5511912345678", 1, 1, None), ("c@x.com", None, 0, 0, None) if False else ("c@x.com", None, 1, 0, "2026-10-23 20:00:00"), (None, "+5511999998888", 0, 1, None)]


def test_send_marks_and_second_run_sends_nothing(tmp_path, monkeypatch, capsys):
    sr = load("sr", "tools/reminders/send_reminders.py"); sent = []
    monkeypatch.setattr(sr, "send_email", lambda to: sent.append(("email", to))); monkeypatch.setattr(sr, "send_wa", lambda to: sent.append(("wa", to)))
    monkeypatch.setattr(sr.time, "sleep", lambda s: None)
    db = make_db(tmp_path, ROWS)
    assert sr.main(["--sqlite", db, "--send", "--sleep", "0"]) == 0
    assert sorted(sent) == [("email", "a@x.com"), ("email", "b@x.com"), ("wa", "+5511912345678"), ("wa", "+5511999998888")]  # c já recebeu
    sent.clear(); sr.main(["--sqlite", db, "--send", "--sleep", "0"])
    assert sent == []  # dedupe: nada é reenviado


def test_consent_is_required(tmp_path):
    sr = load("sr2", "tools/reminders/send_reminders.py")
    rows = [{"email": "n@x.com", "email_consent": 0, "whatsapp": "+5511912345678", "whatsapp_consent": 0}]
    assert sr.plan(rows) == []


def test_dry_run_sends_nothing_and_marks_nothing(tmp_path, monkeypatch, capsys):
    sr = load("sr3", "tools/reminders/send_reminders.py")
    monkeypatch.setattr(sr, "send_email", lambda to: (_ for _ in ()).throw(AssertionError("não pode enviar")))
    db = make_db(tmp_path, ROWS); sr.main(["--sqlite", db])
    out = capsys.readouterr().out; assert "dry-run" in out and '"dry_run": true' in out
    assert sqlite3.connect(db).execute("SELECT count(*) FROM subscribers WHERE reminded_email_at IS NOT NULL").fetchone()[0] == 1


def test_only_and_limit(tmp_path, monkeypatch):
    sr = load("sr4", "tools/reminders/send_reminders.py"); sent = []
    monkeypatch.setattr(sr, "send_email", lambda to: sent.append(to)); monkeypatch.setattr(sr, "send_wa", lambda to: sent.append(to))
    monkeypatch.setattr(sr.time, "sleep", lambda s: None)
    db = make_db(tmp_path, ROWS); sr.main(["--sqlite", db, "--send", "--only", "email", "--limit", "1"])
    assert len(sent) == 1 and "@" in sent[0]


def test_email_has_reply_to_and_unsubscribe(monkeypatch):
    sr = load("sr5", "tools/reminders/send_reminders.py"); got = {}
    monkeypatch.setattr(sr, "post", lambda url, h, body: got.update(body) or 200)
    monkeypatch.setenv("RESEND_API_KEY", "k"); monkeypatch.setenv("EMAIL_FROM", "Placar <oi@placar.test>"); monkeypatch.setenv("EMAIL_REPLY_TO", "sair@placar.test")
    sr.send_email("x@y.com")
    assert got["reply_to"] == "sair@placar.test" and "mailto:sair@placar.test" in got["headers"]["List-Unsubscribe"] and "SAIR" in got["text"]


def test_sync_upsert_is_idempotent_and_deletes_removed(tmp_path):
    ss = load("ss", "tools/subscribers/sync_sqlite.py"); con = ss.open_db(str(tmp_path / "d" / "s.sqlite"))
    row = lambda i, e: {"id": i, "debate": "globo-2026-10-23", "email": e, "whatsapp": None, "email_consent": True, "whatsapp_consent": False, "consent_text": "consinto em receber", "at": "2026-10-23T10:00:00Z", "ip_hash": None}
    ss.upsert(con, [row(1, "a@x.com"), row(2, "b@x.com")]); ss.upsert(con, [row(1, "a@x.com"), row(2, "b@x.com")])
    assert con.execute("SELECT count(*) FROM subscribers").fetchone()[0] == 2
    ss.upsert(con, [row(1, "a@x.com")])  # id 2 apagado na origem (LGPD)
    assert con.execute("SELECT count(*) FROM subscribers").fetchone()[0] == 1
