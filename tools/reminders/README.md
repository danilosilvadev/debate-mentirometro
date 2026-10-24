# Lembretes (e-mail + WhatsApp)

`python3 send_reminders.py --csv sample.csv` → dry-run (padrão, não envia). `--send` envia de verdade.

Fonte real: `private.subscribers` (migração `supabase/003_subscribers.sql`). O schema `private` não é exposto
pela API; para ler, exporte via SQL (`copy (select ...) to stdout csv header`) e use `--csv`, ou exponha `private`
só para a service role. Nunca use a chave service role no navegador.

O que o dono precisa providenciar:
- **WhatsApp Cloud API**: conta Meta Business verificada, app no developers.facebook.com com o produto WhatsApp,
  um número de telefone dedicado (não pode estar no app WhatsApp comum), token permanente de System User,
  e um **template aprovado** (categoria Utility/Marketing, pt_BR), p.ex. `lembrete_debate`:
  "O debate da Globo começa às 21h20. Assista com checagem ao vivo: {{1}}. Responda SAIR para parar."
  Env: `WA_PHONE_NUMBER_ID`, `WA_TOKEN`, `WA_TEMPLATE`, `WA_LANG=pt_BR`. Mensagens de template são cobradas por conversa pela Meta.
- **E-mail**: conta num provedor (Resend, SES, Brevo…) com domínio verificado (SPF/DKIM). Env: `RESEND_API_KEY`, `EMAIL_FROM`.


## Noite do debate: e-mail (passo a passo)

Uma vez (antes):
1. Resend (ou outro): crie a conta, verifique o domínio de envio (registros DNS SPF/DKIM) e gere a chave de API.
2. `~/.config/placar/env` (chmod 600, fora do git): `RESEND_API_KEY=...`, `EMAIL_FROM="Placar da Verdade <oi@seudominio.com>"`, `EMAIL_REPLY_TO=sair@seudominio.com` (caixa que você lê: quem responde SAIR cai aqui).
3. Segredo de exportação: `mkdir -p ~/.local/share/placar && openssl rand -hex 24 > ~/.local/share/placar/.export_secret && chmod 600 ~/.local/share/placar/.export_secret`,
   depois `sha256sum ~/.local/share/placar/.export_secret` (só o hash, sem o espaço e o nome do arquivo) e, no SQL Editor do Supabase:
   `insert into private.config(k,v) values ('export_secret_sha256','<hash>') on conflict (k) do update set v=excluded.v;`

Na hora (cerca de 30 min antes, 20h50):
```bash
set -a; . ~/.config/placar/env; set +a
python3 tools/subscribers/sync_sqlite.py                    # puxa os inscritos para o SQLite local
python3 tools/reminders/send_reminders.py --to voce@seuemail.com   # teste: UMA mensagem, só para você
python3 tools/reminders/send_reminders.py --only email      # dry-run: mostra quem receberia
python3 tools/reminders/send_reminders.py --only email --send   # envia; marca quem recebeu, então rodar de novo não repete
```
`--limit N` envia só N por vez; `--sleep S` ajusta a pausa entre envios (o provedor limita a taxa). Confira também o limite diário do seu plano.
Testes: `python3 -m pytest tools/reminders`.
