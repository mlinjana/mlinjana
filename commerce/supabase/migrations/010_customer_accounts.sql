-- Customer accounts (owner, 14 Nov 2026: Google + email-link sign-in, optional; order history, synced favourites,
-- profile and account deletion, prefilled checkout). Applied as two migrations: customer_accounts, customer_accounts_2.
create table if not exists public.profiles (
  id uuid primary key references auth.users(id) on delete cascade,
  display_name text check (char_length(display_name) <= 60),
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);
alter table public.profiles enable row level security;
create policy "own profile: read" on public.profiles for select to authenticated using ((select auth.uid()) = id);
create policy "own profile: insert" on public.profiles for insert to authenticated with check ((select auth.uid()) = id);
create policy "own profile: update" on public.profiles for update to authenticated using ((select auth.uid()) = id) with check ((select auth.uid()) = id);

create table if not exists public.account_favourites (
  user_id uuid not null references auth.users(id) on delete cascade,
  product_id text not null references public.products(id) on delete cascade,
  created_at timestamptz not null default now(),
  primary key (user_id, product_id)
);
create index if not exists account_favourites_product_id_idx on public.account_favourites (product_id);
alter table public.account_favourites enable row level security;
create policy "own favourites: read" on public.account_favourites for select to authenticated using ((select auth.uid()) = user_id);
create policy "own favourites: add" on public.account_favourites for insert to authenticated with check ((select auth.uid()) = user_id);
create policy "own favourites: remove" on public.account_favourites for delete to authenticated using ((select auth.uid()) = user_id);

-- A signed-in buyer sees paid orders placed with their confirmed sign-in email (guest orders included).
create or replace function public.my_orders()
returns table (ref text, product_id text, title text, store_id text, slug text, licence text, amount_cents integer,
               status text, paid_at timestamptz, download_token text, expires_at timestamptz, downloads_left integer)
language sql stable security definer set search_path = ''
as $$
  select o.ref, o.product_id, p.title, o.store_id, p.slug, o.licence, o.amount_cents, o.status, o.paid_at,
         case when t.token is not null and not t.revoked and t.expires_at > now() and t.downloads < t.max_downloads then t.token end,
         t.expires_at, greatest(coalesce(t.max_downloads - t.downloads, 0), 0)
  from auth.users u
  join public.orders o on lower(o.email) = lower(u.email)
  join public.products p on p.id = o.product_id
  left join lateral (select * from public.download_tokens d where d.order_id = o.id order by d.created_at desc limit 1) t on true
  where u.id = (select auth.uid()) and u.email_confirmed_at is not null and o.status in ('paid', 'refunded')
  order by o.paid_at desc nulls last
  limit 200;
$$;
revoke all on function public.my_orders() from public, anon;
grant execute on function public.my_orders() to authenticated;

-- Delete my account: sign-in, profile and favourites go; paid order records stay (tax law).
create or replace function public.delete_my_account()
returns void
language plpgsql security definer set search_path = ''
as $$
begin
  if (select auth.uid()) is null then raise exception 'not signed in'; end if;
  delete from auth.users where id = (select auth.uid());
end
$$;
revoke all on function public.delete_my_account() from public, anon;
grant execute on function public.delete_my_account() to authenticated;
