-- Review requests (owner, 14 Nov 2026: "do the review request emails").
-- A few days after a real paid order, ops-api /cron/review-requests emails the buyer once, asking for an honest review.
-- The link carries the order's own secret, so only the buyer can review, once per order. Reviews arrive as 'pending':
-- nothing is shown on the site until the owner approves it. No incentives, no edits to wording.
create table if not exists public.reviews (
  id bigint generated always as identity primary key,
  order_ref text not null unique references public.orders(ref),
  product_id text not null references public.products(id),
  rating smallint not null check (rating between 1 and 5),
  body text not null check (char_length(body) between 10 and 2000),
  display_name text check (char_length(display_name) <= 40),
  status text not null default 'pending' check (status in ('pending', 'approved', 'rejected')),
  created_at timestamptz not null default now(),
  moderated_at timestamptz
);
alter table public.reviews enable row level security;
create index if not exists reviews_product_id_idx on public.reviews (product_id);
alter table public.orders add column if not exists review_requested_at timestamptz;

-- include reviews in the nightly backup's restore drill
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
                           'contact_messages','events','work_log','costs','job_runs','daily_reports','reviews'])) then
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

-- daily at 08:05 SAST
select cron.schedule('review-requests', '5 6 * * *', $c$select public.call_ops('/cron/review-requests')$c$);
