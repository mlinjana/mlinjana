-- NOT YET APPLIED (11 Nov 2026: Supabase's confirmation prompt timed out).
-- The deployed ops-api (v7) writes checkout=false when its error-streak or budget safeguard trips, which would lift a
-- deliberate checkout pause. Until the corrected function is deployed, the database keeps checkout paused for those
-- two automatic writes. The owner's own changes to kill_switch are not affected.
create or replace function public.kill_switch_guard() returns trigger
language plpgsql set search_path = '' as $$
begin
  if new.key = 'kill_switch'
     and coalesce(new.value->>'reason','') in ('repeated job errors — check job_runs', 'weekly budget exceeded')
     and coalesce((new.value->>'checkout')::boolean, false) = false then
    new.value := jsonb_set(new.value, '{checkout}', 'true'::jsonb);
  end if;
  return new;
end $$;
revoke all on function public.kill_switch_guard() from public, anon, authenticated;
drop trigger if exists kill_switch_guard on public.config;
create trigger kill_switch_guard before update on public.config for each row execute function public.kill_switch_guard();
