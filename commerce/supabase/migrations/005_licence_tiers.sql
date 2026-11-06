-- Licence tiers (owner decision #39, 6 Nov 2026): Standard (personal + one business, list price) and
-- Team (up to 10 people in one organisation, 2.5x list price rounded to whole rand). Commercial/Enterprise is quoted
-- by hand, so it never reaches checkout. store-api sets the tier and its price; existing orders are Standard.
alter table public.orders
  add column if not exists licence text not null default 'standard'
  constraint orders_licence_check check (licence in ('standard', 'team'));
comment on column public.orders.licence is 'standard = personal + one business; team = up to 10 people in one organisation (2.5x price)';
