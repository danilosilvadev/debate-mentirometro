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
