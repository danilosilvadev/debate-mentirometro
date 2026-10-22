-- Troféu Pinóquio: palpite do público (sem dinheiro) sobre quem vai mentir mais.
-- Sem PII: guarda só sha256(debate|client_id aleatório do navegador) para "1 palpite por navegador"
-- (pode trocar de opção), mais limite por IP. anon só chama palpitar() e lê public.palpite_totais.
create schema if not exists private;
create extension if not exists pgcrypto with schema extensions;

create table if not exists private.palpites (
  debate text not null,
  client_hash text not null,
  escolha text not null check (escolha in ('lula','flavio','empate')),
  ip_hash text not null default '',
  at timestamptz not null default now(),
  primary key (debate, client_hash)
);
create index if not exists palpites_ip_at on private.palpites (ip_hash, at);
alter table private.palpites enable row level security;

create table if not exists public.palpite_totais (
  debate text primary key,
  lula bigint not null default 0 check (lula >= 0),
  flavio bigint not null default 0 check (flavio >= 0),
  empate bigint not null default 0 check (empate >= 0),
  -- gancho pós-debate: resultado oficial do Mentirômetro ('lula'|'flavio'|'empate'), preenchido pelo pipeline
  resultado text check (resultado is null or resultado in ('lula','flavio','empate')),
  updated_at timestamptz not null default now()
);
alter table public.palpite_totais enable row level security;
drop policy if exists "palpites publicos" on public.palpite_totais;
create policy "palpites publicos" on public.palpite_totais for select to anon, authenticated using (true);
revoke insert, update, delete on public.palpite_totais from anon, authenticated;

create or replace function public.palpitar(p_debate text, p_escolha text, p_client text)
returns json language plpgsql security definer set search_path = public, private, extensions as $$
declare
  v_hash text; v_ip text := private.client_ip(); v_iph text; v_old text; n_ip int;
begin
  if char_length(coalesce(p_debate,'')) not between 3 and 64 then return json_build_object('ok', false, 'erro', 'debate'); end if;
  if p_escolha not in ('lula','flavio','empate') then return json_build_object('ok', false, 'erro', 'escolha'); end if;
  if char_length(coalesce(p_client,'')) not between 16 and 64 then return json_build_object('ok', false, 'erro', 'cliente'); end if;
  if exists (select 1 from public.palpite_totais where debate = p_debate and resultado is not null) then
    return json_build_object('ok', false, 'erro', 'encerrado'); end if;
  v_hash := encode(digest(p_debate || '|' || p_client, 'sha256'), 'hex');
  v_iph := case when v_ip = '' then '' else encode(digest('ip|' || v_ip, 'sha256'), 'hex') end;
  select count(*) into n_ip from private.palpites where ip_hash = v_iph and v_iph <> '' and at > now() - interval '1 minute';
  if n_ip >= 30 then return json_build_object('ok', false, 'erro', 'devagar'); end if;
  insert into public.palpite_totais(debate) values (p_debate) on conflict (debate) do nothing;
  select escolha into v_old from private.palpites where debate = p_debate and client_hash = v_hash for update;
  if v_old is null then
    insert into private.palpites(debate, client_hash, escolha, ip_hash) values (p_debate, v_hash, p_escolha, v_iph);
  elsif v_old <> p_escolha then
    update private.palpites set escolha = p_escolha, at = now() where debate = p_debate and client_hash = v_hash;
  end if;
  if v_old is distinct from p_escolha then
    update public.palpite_totais set
      lula = lula + (p_escolha = 'lula')::int - (coalesce(v_old,'') = 'lula')::int,
      flavio = flavio + (p_escolha = 'flavio')::int - (coalesce(v_old,'') = 'flavio')::int,
      empate = empate + (p_escolha = 'empate')::int - (coalesce(v_old,'') = 'empate')::int,
      updated_at = now()
    where debate = p_debate;
  end if;
  return (select json_build_object('ok', true, 'escolha', p_escolha, 'mudou', v_old is not null and v_old <> p_escolha,
    'lula', lula, 'flavio', flavio, 'empate', empate) from public.palpite_totais where debate = p_debate);
end $$;
revoke all on function public.palpitar(text,text,text) from public;
grant execute on function public.palpitar(text,text,text) to anon, authenticated;
