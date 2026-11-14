-- Phase 1 conversion funnel: permit additional anonymous event types.
-- REVIEWED MIGRATION ONLY: not applied to production by this branch.
-- The existing store-api still validates allowed types and writes only type, store_id,
-- product_id, path and referrer hostname. No customer email or order tokens are logged.
-- Apply this migration BEFORE deploying the new store-api event allowlist.

ALTER TABLE public.events
  DROP CONSTRAINT IF EXISTS events_type_check;
ALTER TABLE public.events
  ADD CONSTRAINT events_type_check
  CHECK (type IN (
    'page_view',
    'product_view',
    'basket_add',
    'checkout_start',
    'checkout_handoff',
    'checkout_error'
  ));
