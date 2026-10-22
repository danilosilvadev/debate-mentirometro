-- Placar da Verdade: votos, e-mails (LGPD), super chats. Tudo via RPC security definer;
-- anon só lê totais e super chats aprovados.
create extension if not exists pgcrypto;
create schema if not exists private;

create table private.config (k text primary key, v text not null);

create table public.vote_totals (side text primary key check (side in ('1','2')), n bigint not null default 0,
  updated_at timestamptz not null default now());
insert into public.vote_totals(side) values ('1'),('2');

create table private.vote_events (id bigserial primary key, debate text not null, side text not null check (side in ('1','2')),
  n int not null check (n between 1 and 20), client_id text not null, ip text, at timestamptz not null default now());
create index on private.vote_events (client_id, at);
create index on private.vote_events (ip, at);
create index on private.vote_events (debate, at);

create table private.emails (email text primary key, consent boolean not null, consent_text text not null,
  social jsonb not null default '{}', client_id text, at timestamptz not null default now());

create table public.superchats (id uuid primary key default gen_random_uuid(), debate text not null,
  nome text not null check (char_length(nome) between 1 and 40),
  mensagem text not null check (char_length(mensagem) between 1 and 140),
  valor_centavos int not null check (valor_centavos between 200 and 100000),
  provider text not null, teste boolean not null default true,
  status text not null default 'pendente' check (status in ('pendente','aprovado','rejeitado')),
  motivo text, client_id text, at timestamptz not null default now(), moderado_at timestamptz);

alter table public.vote_totals enable row level security;
alter table public.superchats enable row level security;
alter table private.vote_events enable row level security;
alter table private.emails enable row level security;
alter table private.config enable row level security;
create policy "totais publicos" on public.vote_totals for select to anon, authenticated using (true);
create policy "superchats aprovados" on public.superchats for select to anon, authenticated using (status = 'aprovado');

create or replace function private.client_ip() returns text language sql stable as $$
  select coalesce(split_part(current_setting('request.headers', true)::json->>'x-forwarded-for', ',', 1), '')
$$;

create or replace function public.cast_vote(p_side text, p_n int, p_client text, p_debate text default 'ao-vivo')
returns json language plpgsql security definer set search_path = public, private as $$
declare c_recent int; ip_recent int; v_ip text := private.client_ip();
begin
  if p_side not in ('1','2') or p_n < 1 or p_n > 20 or char_length(coalesce(p_client,'')) not between 8 and 64 then
    raise exception 'voto invalido';
  end if;
  select coalesce(sum(n),0) into c_recent from private.vote_events where client_id = p_client and at > now() - interval '10 seconds';
  select coalesce(sum(n),0) into ip_recent from private.vote_events where ip = v_ip and v_ip <> '' and at > now() - interval '10 seconds';
  if c_recent + p_n > 30 or ip_recent + p_n > 300 then
    return json_build_object('ok', false, 'erro', 'devagar');
  end if;
  insert into private.vote_events(debate, side, n, client_id, ip) values (p_debate, p_side, p_n, p_client, v_ip);
  update public.vote_totals set n = n + p_n, updated_at = now() where side = p_side;
  return (select json_build_object('ok', true, 'totais', json_object_agg(side, n)) from public.vote_totals);
end $$;

create or replace function public.subscribe_email(p_email text, p_consent boolean, p_consent_text text, p_social jsonb, p_client text)
returns json language plpgsql security definer set search_path = public, private as $$
begin
  if p_email !~* '^[a-z0-9._%+-]+@[a-z0-9.-]+\.[a-z]{2,}$' or char_length(p_email) > 254 then raise exception 'email invalido'; end if;
  if not p_consent then raise exception 'consentimento obrigatorio'; end if;
  insert into private.emails(email, consent, consent_text, social, client_id) values (lower(p_email), true, left(p_consent_text, 500), coalesce(p_social,'{}'), p_client)
  on conflict (email) do update set social = private.emails.social || excluded.social, at = now();
  return json_build_object('ok', true);
end $$;

create or replace function public.create_superchat(p_nome text, p_mensagem text, p_valor int, p_provider text, p_client text, p_debate text default 'ao-vivo')
returns json language plpgsql security definer set search_path = public, private as $$
declare v_id uuid; recent int;
begin
  select count(*) into recent from public.superchats where client_id = p_client and at > now() - interval '1 minute';
  if recent >= 2 then return json_build_object('ok', false, 'erro', 'devagar'); end if;
  if p_provider <> 'mock' then raise exception 'provedor sem confirmacao de pagamento no servidor'; end if;
  insert into public.superchats(debate, nome, mensagem, valor_centavos, provider, teste, client_id)
  values (p_debate, btrim(p_nome), btrim(p_mensagem), p_valor, p_provider, true, p_client) returning id into v_id;
  return json_build_object('ok', true, 'id', v_id);
end $$;

-- Moderação (pipeline com a chave Groq). Token conferido por hash; o token não fica no banco.
create or replace function private.mod_ok(p_token text) returns boolean language sql stable security definer set search_path = private, public, extensions as $$
  select exists(select 1 from private.config where k = 'mod_token_sha256' and v = encode(digest(p_token, 'sha256'), 'hex'))
$$;

create or replace function public.mod_pending(p_token text) returns setof public.superchats
language plpgsql security definer set search_path = public, private as $$
begin
  if not private.mod_ok(p_token) then raise exception 'token'; end if;
  return query select * from public.superchats where status = 'pendente' order by at limit 20;
end $$;

create or replace function public.mod_decide(p_token text, p_id uuid, p_ok boolean, p_motivo text)
returns json language plpgsql security definer set search_path = public, private as $$
begin
  if not private.mod_ok(p_token) then raise exception 'token'; end if;
  update public.superchats set status = case when p_ok then 'aprovado' else 'rejeitado' end, motivo = left(p_motivo, 200), moderado_at = now() where id = p_id;
  return json_build_object('ok', true);
end $$;

create or replace function public.export_events(p_token text, p_debate text, p_desde timestamptz, p_ate timestamptz)
returns json language plpgsql security definer set search_path = public, private as $$
begin
  if not private.mod_ok(p_token) then raise exception 'token'; end if;
  return json_build_object(
    'votos', (select coalesce(json_agg(json_build_object('side', side, 'n', n, 'at', extract(epoch from at)) order by at), '[]') from private.vote_events where debate = p_debate and at between p_desde and p_ate),
    'superchats', (select coalesce(json_agg(json_build_object('nome', nome, 'mensagem', mensagem, 'valor_centavos', valor_centavos, 'teste', teste, 'at', extract(epoch from coalesce(moderado_at, at))) order by at), '[]') from public.superchats where debate = p_debate and status = 'aprovado' and at between p_desde and p_ate));
end $$;

revoke all on function private.mod_ok(text) from public, anon, authenticated;
grant execute on function public.cast_vote(text,int,text,text), public.subscribe_email(text,boolean,text,jsonb,text),
  public.create_superchat(text,text,int,text,text,text), public.mod_pending(text), public.mod_decide(text,uuid,boolean,text),
  public.export_events(text,text,timestamptz,timestamptz) to anon, authenticated;

alter publication supabase_realtime add table public.vote_totals, public.superchats;
alter function private.client_ip() set search_path = pg_catalog;
