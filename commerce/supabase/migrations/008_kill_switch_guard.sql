-- Applied 11 Nov 2026 (as CREATE OR REPLACE TRIGGER, without a DROP, which is what Supabase's prompt had been stopping).
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
create or replace trigger kill_switch_guard before update on public.config for each row execute function public.kill_switch_guard();
