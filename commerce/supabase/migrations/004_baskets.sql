-- Basket checkout (5 Nov 2026): several products paid in one PayFast payment.
-- Each product stays its own row in orders (same delivery, tokens and reports as single purchases); the basket
-- holds the payment. Service-role access only, like every other table (RLS on, no policies).
create table if not exists public.baskets (
  id uuid primary key default gen_random_uuid(),
  ref text not null unique,
  secret text not null,
  email text not null,
  amount_cents integer not null check (amount_cents > 0),
  currency text not null default 'ZAR',
  provider text not null default 'payfast',
  provider_mode text not null,
  status text not null default 'pending',
  provider_payment_id text,
  gross_cents integer,
  fee_cents integer,
  net_cents integer,
  created_at timestamptz not null default now(),
  paid_at timestamptz,
  notes text
);
alter table public.baskets enable row level security;
alter table public.orders add column if not exists basket_id uuid references public.baskets(id);
create index if not exists orders_basket_id_idx on public.orders(basket_id);
create index if not exists baskets_email_created_idx on public.baskets(email, created_at);
