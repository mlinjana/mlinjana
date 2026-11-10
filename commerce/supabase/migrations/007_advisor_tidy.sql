-- Supabase advisor tidy-ups (10 Nov 2026): cover four foreign keys with indexes and pin one function's search_path.
create index if not exists download_tokens_order_id_idx on public.download_tokens (order_id);
create index if not exists orders_product_id_idx on public.orders (product_id);
create index if not exists orders_store_id_idx on public.orders (store_id);
create index if not exists products_store_id_idx on public.products (store_id);
alter function public.weekly_costs_usd() set search_path = '';
