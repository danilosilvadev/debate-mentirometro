-- D1 (SQLite) — destino final das inscrições, atrás do Worker. Também é o schema do SQLite local.
CREATE TABLE IF NOT EXISTS subscribers (
  id INTEGER PRIMARY KEY,
  email TEXT,
  whatsapp_e164 TEXT,
  consent_email INTEGER NOT NULL DEFAULT 0,
  consent_whatsapp INTEGER NOT NULL DEFAULT 0,
  consent_text_version TEXT NOT NULL,
  created_at TEXT NOT NULL,
  ip_hash TEXT,
  source TEXT NOT NULL,
  debate TEXT NOT NULL DEFAULT 'globo-2026-10-23',
  reminded_email_at TEXT,
  reminded_whatsapp_at TEXT,
  CHECK (email IS NOT NULL OR whatsapp_e164 IS NOT NULL)
);
CREATE UNIQUE INDEX IF NOT EXISTS subscribers_email_uq ON subscribers(debate, lower(email)) WHERE email IS NOT NULL;
CREATE UNIQUE INDEX IF NOT EXISTS subscribers_wa_uq ON subscribers(debate, whatsapp_e164) WHERE whatsapp_e164 IS NOT NULL;
