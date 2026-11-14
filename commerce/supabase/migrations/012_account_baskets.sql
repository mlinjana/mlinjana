-- Profile basket storage for authenticated customers; distinct from payment/order baskets.
-- Every customer can only read/write their own draft list. The RLS condition is
-- identity-based and never relies on editable user_metadata.
create table if not exists public.account_baskets (
  user_id uuid primary key references auth.users(id) on delete cascade,
  items jsonb not null default '[]'::jsonb
    constraint account_baskets_items_shape check (
      jsonb_typeof(items) = 'array' and jsonb_array_length(items) <= 25
    ),
  updated_at timestamptz not null default now()
);

alter table public.account_baskets enable row level security;
revoke all on public.account_baskets from anon;
grant select, insert, update on public.account_baskets to authenticated;

create policy "account basket: read own" on public.account_baskets
  for select to authenticated
  using ((select auth.uid()) = user_id);
create policy "account basket: insert own" on public.account_baskets
  for insert to authenticated
  with check ((select auth.uid()) = user_id);
create policy "account basket: update own" on public.account_baskets
  for update to authenticated
  using ((select auth.uid()) = user_id)
  with check ((select auth.uid()) = user_id);

comment on table public.account_baskets is
  'User-owned draft shopping basket only. No payment details; local browser basket cleared on sign-out.';
