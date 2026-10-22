-- Anon/authenticated must never TRUNCATE public counters/tables (applied 2026-10-22).
revoke truncate on public.palpite_totais, public.vote_totals, public.subscriber_count, public.superchats from anon, authenticated;
