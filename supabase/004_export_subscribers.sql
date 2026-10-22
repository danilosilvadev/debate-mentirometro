insert into private.config(k,v) values ('export_secret_sha256','<sha256 do segredo — defina fora do git>') on conflict (k) do update set v=excluded.v;
create or replace function public.export_subscribers(p_secret text, p_since timestamptz default '1970-01-01')
returns setof json language plpgsql security definer set search_path = public, private, extensions as $$
begin
  if encode(digest(coalesce(p_secret,''),'sha256'),'hex') is distinct from (select v from private.config where k='export_secret_sha256') then
    raise exception 'nao autorizado'; end if;
  return query select json_build_object('id',id,'debate',debate,'email',email,'whatsapp',whatsapp,'email_consent',email_consent,
    'whatsapp_consent',whatsapp_consent,'consent_text',consent_text,'at',at,'ip_hash',case when ip is null or ip='' then null else encode(digest(ip,'sha256'),'hex') end,
    'reminded_email_at',reminded_email_at,'reminded_whatsapp_at',reminded_whatsapp_at) from private.subscribers where at >= p_since order by id;
end $$;
revoke all on function public.export_subscribers(text,timestamptz) from public;
grant execute on function public.export_subscribers(text,timestamptz) to anon;
