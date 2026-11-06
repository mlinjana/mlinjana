-- Nightly logical backups + a restore drill (P0 "Nightly database backup with a restore drill").
-- The Free plan has no automatic backups (Supabase docs: "We recommend that free tier plan projects regularly export
-- their data"). ops-api /cron/backup writes every business table to the private 'backups' bucket (db/YYYY-MM-DD.json.gz,
-- 30 days kept); /cron/restore-drill loads the latest file into the private restore_drill schema and compares row
-- counts and checksums with the file. Both run from pg_cron through public.call_ops (cron secret stays in the DB).

create schema if not exists restore_drill;
revoke all on schema restore_drill from public, anon, authenticated;

create or replace function public.restore_drill_table(tbl text, rows jsonb)
returns jsonb
language plpgsql
security definer
set search_path = ''
as $$
declare
  n bigint;
  restored_md5 text;
  backup_md5 text;
begin
  if not (tbl = any (array['config','stores','products','listings','orders','baskets','download_tokens','payment_events',
                           'contact_messages','events','work_log','costs','job_runs','daily_reports'])) then
    raise exception 'restore_drill_table: table % is not in the backup set', tbl;
  end if;
  execute format('drop table if exists restore_drill.%I', tbl);
  execute format('create table restore_drill.%I (like public.%I including defaults)', tbl, tbl);
  execute format('insert into restore_drill.%I select * from jsonb_populate_recordset(null::public.%I, $1)', tbl, tbl) using rows;
  execute format('select count(*), md5(coalesce(string_agg(to_jsonb(r)::text, %L order by to_jsonb(r)::text), %L)) from restore_drill.%I r',
                 ',', '', tbl) into n, restored_md5;
  select md5(coalesce(string_agg(e::text, ',' order by e::text), '')) into backup_md5 from jsonb_array_elements(rows) e;
  return jsonb_build_object('table', tbl, 'restored', n, 'backup_rows', jsonb_array_length(rows), 'checksum_match', restored_md5 = backup_md5);
end
$$;
revoke all on function public.restore_drill_table(text, jsonb) from public, anon, authenticated;
grant execute on function public.restore_drill_table(text, jsonb) to service_role;

-- 01:20 SAST nightly; restore drill 01:50 SAST every Monday (after Sunday night's backup)
select cron.schedule('nightly-backup', '20 23 * * *', $c$select public.call_ops('/cron/backup')$c$);
select cron.schedule('weekly-restore-drill', '50 23 * * 0', $c$select public.call_ops('/cron/restore-drill')$c$);
