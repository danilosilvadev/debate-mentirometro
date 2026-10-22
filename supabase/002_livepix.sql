-- Super chat via LivePix: o pagamento acontece só na página da LivePix. O navegador não cria mais
-- super chats; quem grava é a Edge Function livepix-webhook (service role), já moderado.
drop function if exists public.create_superchat(text, text, int, text, text, text);
alter table public.superchats add column if not exists livepix_id text unique;
alter table public.superchats drop constraint if exists superchats_valor_centavos_check;
alter table public.superchats add constraint superchats_valor_centavos_check check (valor_centavos between 100 and 10000000);
