-- Landing de inscrição: lembretes por e-mail e/ou WhatsApp. PII fica em private.subscribers
-- (anon não lê). anon só chama subscribe() e lê o contador public.subscriber_count.
create schema if not exists private;
create table if not exists private.subscribers (
  id bigserial primary key,
  debate text not null,
  email text check (email is null or (char_length(email) <= 254 and email ~* '^[^@\s]+@[^@\s]+\.[a-z]{2,}$')),
  whatsapp text check (whatsapp is null or whatsapp ~ '^\+55[1-9][0-9]9?[0-9]{8}$'),
  email_consent boolean not null default false,
  whatsapp_consent boolean not null default false,
  consent_text text not null,
  client_id text, ip text,
  at timestamptz not null default now(),
  reminded_email_at timestamptz, reminded_whatsapp_at timestamptz,
  check (email is not null or whatsapp is not null)
);
create unique index if not exists subscribers_email_uq on private.subscribers (debate, lower(email)) where email is not null;
create unique index if not exists subscribers_wa_uq on private.subscribers (debate, whatsapp) where whatsapp is not null;
create index if not exists subscribers_ip_at on private.subscribers (ip, at);
alter table private.subscribers enable row level security;

create table if not exists public.subscriber_count (debate text primary key, n bigint not null default 0, updated_at timestamptz not null default now());
alter table public.subscriber_count enable row level security;
drop policy if exists "contador publico" on public.subscriber_count;
create policy "contador publico" on public.subscriber_count for select to anon, authenticated using (true);

create or replace function public.subscribe(p_debate text, p_email text, p_whatsapp text,
  p_email_consent boolean, p_whatsapp_consent boolean, p_consent_text text, p_client text)
returns json language plpgsql security definer set search_path = public, private as $$
declare v_ip text := private.client_ip(); v_email text := nullif(lower(trim(coalesce(p_email,''))), '');
  v_wa text := nullif(regexp_replace(coalesce(p_whatsapp,''), '[^0-9+]', '', 'g'), ''); v_new boolean := false; v_id bigint; n_ip int;
begin
  if char_length(coalesce(p_debate,'')) not between 3 and 64 or char_length(coalesce(p_consent_text,'')) not between 10 and 600 then
    raise exception 'inscricao invalida'; end if;
  if v_email is not null and not p_email_consent then v_email := null; end if;
  if v_wa is not null and not p_whatsapp_consent then v_wa := null; end if;
  if v_email is null and v_wa is null then return json_build_object('ok', false, 'erro', 'consentimento'); end if;
  if v_email is not null and (char_length(v_email) > 254 or v_email !~* '^[^@\s]+@[^@\s]+\.[a-z]{2,}$') then
    return json_build_object('ok', false, 'erro', 'email'); end if;
  if v_wa is not null and v_wa !~ '^\+55[1-9][0-9]9?[0-9]{8}$' then return json_build_object('ok', false, 'erro', 'whatsapp'); end if;
  select count(*) into n_ip from private.subscribers where ip = v_ip and v_ip <> '' and at > now() - interval '1 minute';
  if n_ip >= 20 then return json_build_object('ok', false, 'erro', 'devagar'); end if;
  -- dedupe: casa por e-mail ou WhatsApp e completa a linha existente
  select id into v_id from private.subscribers where debate = p_debate
    and ((v_email is not null and lower(email) = v_email) or (v_wa is not null and whatsapp = v_wa)) limit 1;
  if v_id is null then
    insert into private.subscribers(debate, email, whatsapp, email_consent, whatsapp_consent, consent_text, client_id, ip)
      values (p_debate, v_email, v_wa, v_email is not null, v_wa is not null, p_consent_text, left(p_client, 64), v_ip);
    v_new := true;
    insert into public.subscriber_count(debate, n) values (p_debate, 1)
      on conflict (debate) do update set n = subscriber_count.n + 1, updated_at = now();
  else
    begin
      update private.subscribers set
        email = coalesce(email, v_email), email_consent = email_consent or v_email is not null,
        whatsapp = coalesce(whatsapp, v_wa), whatsapp_consent = whatsapp_consent or v_wa is not null
        where id = v_id;
    exception when unique_violation then null; end;
  end if;
  return json_build_object('ok', true, 'novo', v_new,
    'total', (select n from public.subscriber_count where debate = p_debate));
end $$;
revoke all on function public.subscribe(text,text,text,boolean,boolean,text,text) from public;
grant execute on function public.subscribe(text,text,text,boolean,boolean,text,text) to anon, authenticated;
