-- Mlinjana Studios: first-customer funnel baseline (READ ONLY)
-- Run in the connected commerce-network Supabase SQL editor.
-- Do NOT treat this as a unique-visitor conversion rate: events are anonymous page/event counts.
-- Sandbox is excluded; the owner's real-money test must still be manually excluded for organic sales reporting.
-- Payment rows are counted once: single orders (basket_id IS NULL) plus baskets;
-- a paid basket's constituent order rows must not be counted again.
-- No emails, order secrets or download tokens are queried.

WITH recent_events AS (
  SELECT type, count(*) AS n
  FROM public.events
  WHERE ts >= now() - interval '30 days'
  GROUP BY type
), payments AS (
  SELECT status, provider_mode, amount_cents
  FROM public.orders
  WHERE basket_id IS NULL AND created_at >= now() - interval '30 days'
  UNION ALL
  SELECT status, provider_mode, amount_cents
  FROM public.baskets
  WHERE created_at >= now() - interval '30 days'
)
SELECT
  (SELECT coalesce(sum(n), 0) FROM recent_events WHERE type = 'product_view') AS product_view_events,
  (SELECT coalesce(sum(n), 0) FROM recent_events WHERE type = 'basket_add') AS basket_add_events,
  (SELECT coalesce(sum(n), 0) FROM recent_events WHERE type = 'checkout_start') AS checkout_start_events,
  (SELECT coalesce(sum(n), 0) FROM recent_events WHERE type = 'checkout_handoff') AS checkout_handoff_events,
  (SELECT coalesce(sum(n), 0) FROM recent_events WHERE type = 'checkout_error') AS checkout_error_events,
  (SELECT count(*) FROM payments WHERE status = 'paid' AND provider_mode = 'live') AS live_paid_transactions_including_owner_tests,
  (SELECT coalesce(sum(amount_cents), 0) FROM payments WHERE status = 'paid' AND provider_mode = 'live') / 100.0 AS live_gross_zar_including_owner_tests,
  (SELECT count(*) FROM payments WHERE status = 'paid' AND provider_mode = 'sandbox') AS sandbox_paid_transactions;

-- Daily trend, Johannesburg local date. Also read-only.
WITH days AS (
  SELECT d::date AS day
  FROM generate_series(
    (now() AT TIME ZONE 'Africa/Johannesburg')::date - 29,
    (now() AT TIME ZONE 'Africa/Johannesburg')::date,
    interval '1 day'
  ) AS d
), ev AS (
  SELECT (ts AT TIME ZONE 'Africa/Johannesburg')::date AS day,
    count(*) FILTER (WHERE type = 'product_view') AS product_views,
    count(*) FILTER (WHERE type = 'basket_add') AS basket_adds,
    count(*) FILTER (WHERE type = 'checkout_start') AS checkout_starts,
    count(*) FILTER (WHERE type = 'checkout_handoff') AS checkout_handoffs,
    count(*) FILTER (WHERE type = 'checkout_error') AS checkout_errors
  FROM public.events WHERE ts >= now() - interval '31 days' GROUP BY 1
), paid AS (
  SELECT (paid_at AT TIME ZONE 'Africa/Johannesburg')::date AS day,
    count(*) AS transactions, sum(amount_cents) AS cents
  FROM public.orders
  WHERE status = 'paid' AND provider_mode = 'live' AND basket_id IS NULL
    AND paid_at >= now() - interval '31 days'
  GROUP BY 1
  UNION ALL
  SELECT (paid_at AT TIME ZONE 'Africa/Johannesburg')::date AS day,
    count(*) AS transactions, sum(amount_cents) AS cents
  FROM public.baskets
  WHERE status = 'paid' AND provider_mode = 'live'
    AND paid_at >= now() - interval '31 days'
  GROUP BY 1
), payment_totals AS (
  SELECT day, sum(transactions) AS transactions, sum(cents) AS cents
  FROM paid GROUP BY 1
)
SELECT to_char(d.day, 'YYYY-MM-DD') AS local_day,
  coalesce(ev.product_views, 0) AS product_view_events,
  coalesce(ev.basket_adds, 0) AS basket_add_events,
  coalesce(ev.checkout_starts, 0) AS checkout_start_events,
  coalesce(ev.checkout_handoffs, 0) AS checkout_handoff_events,
  coalesce(ev.checkout_errors, 0) AS checkout_error_events,
  coalesce(p.transactions, 0) AS live_paid_transactions,
  round(coalesce(p.cents, 0)::numeric / 100, 2) AS live_gross_zar
FROM days d
LEFT JOIN ev ON ev.day = d.day
LEFT JOIN payment_totals p ON p.day = d.day
ORDER BY d.day DESC;

-- Next data requirements:
-- 1. Segregate internal QA traffic at collection time (without collecting personal data).
-- 2. Apply migration 011 and deploy store-api + site.js to start collecting the new events.
-- 3. Use verified payment rows, not redirect-page visits, for revenue.
-- 4. Define a non-test order classification before claiming independent first-customer sales.
