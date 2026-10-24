# Inscritos → SQLite (LGPD)

PII nunca é publicada: o site só lê `public.subscriber_count`.

- `sync_sqlite.py`: puxa `private.subscribers` via RPC `export_subscribers` (protegida por segredo; só o sha256 fica no
  banco em `private.config`) e faz upsert idempotente em `$PLACAR_DATA_DIR/subscribers.sqlite (padrão ~/.local/share/placar)` (chmod 600, fora do git).
  Linhas apagadas na origem são apagadas no SQLite. IP vira `ip_hash` (sha256).
- `sync_loop.sh`: roda a cada 5 min (`nohup tools/subscribers/sync_loop.sh >> ~/.local/share/placar/sync.log 2>&1 &`).
- Schema = `cloudflare/d1/0001_subscribers.sql`, o mesmo do D1 de destino. Quando houver `CLOUDFLARE_API_TOKEN`,
  um Worker grava direto no D1 e a landing aponta `LANDING_SUBSCRIBE_URL`/`LANDING_COUNT_URL` para ele.
- Trocar o segredo: gere um novo em `$PLACAR_DATA_DIR/.export_secret` e grave o sha256 em `private.config`
  (`export_secret_sha256`) via SQL; nunca no git.
- `tools/reminders/send_reminders.py` lê este SQLite por padrão (dry-run por padrão).
