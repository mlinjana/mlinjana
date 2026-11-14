-- Self-service download renewal for verified customers, independent of PayFast.
-- Applied after customer_accounts migration. No anonymous execution rights.
-- Renewal never changes the order, payment, file or previously issued tokens.
create or replace function public.renew_my_download(p_ref text)
returns text
language plpgsql
security definer
set search_path = ''
as $$
declare
  v_email text;
  v_order_id uuid;
  v_order_status text;
  v_token text;
  v_expires_at timestamptz;
  v_downloads integer;
  v_max_downloads integer;
  v_revoked boolean;
  v_recent_issues integer;
  v_now timestamptz := now();
begin
  if (select auth.uid()) is null then
    raise exception 'Sign in to renew a download.' using errcode='P0001';
  end if;

  -- Require a verified email identity. Orders were originally linked to the
  -- checkout email, including guest checkouts made before creating an account.
  select lower(u.email) into v_email
  from auth.users u
  where u.id = (select auth.uid())
    and u.email_confirmed_at is not null;
  if v_email is null then
    raise exception 'Verify your email to access your purchases.' using errcode='P0001';
  end if;

  -- Never issue a link for unpaid, failed, cancelled or refunded orders.
  select o.id, o.status into v_order_id, v_order_status
  from public.orders o
  where o.ref = p_ref and lower(o.email) = v_email and o.status = 'paid';
  if v_order_id is null then
    raise exception 'Paid order not found for your account.' using errcode='P0001';
  end if;

  -- Avoid simultaneous requests minting duplicate tokens and bypassing limits.
  perform pg_catalog.pg_advisory_xact_lock(pg_catalog.hashtextextended(v_order_id::text, 0));

  select d.token, d.expires_at, d.downloads, d.max_downloads, d.revoked
    into v_token, v_expires_at, v_downloads, v_max_downloads, v_revoked
  from public.download_tokens d
  where d.order_id = v_order_id
  order by d.created_at desc limit 1;

  if v_revoked is true then
    raise exception 'Download access is unavailable for this order.' using errcode='P0001';
  end if;
  -- If a working download token already exists, reuse it.
  if v_token is not null and v_expires_at > v_now and v_downloads < v_max_downloads then
    return v_token;
  end if;

  -- Reasonable anti-abuse limit: a buyer can renew up to four times per
  -- rolling 24 hours per purchase (original checkout token excluded).
  select count(*) into v_recent_issues
  from public.download_tokens d
  where d.order_id = v_order_id
    and d.created_at > v_now - interval '24 hours';
  if v_recent_issues >= 5 then
    raise exception 'Daily download renewal limit reached. Please retry tomorrow.'
      using errcode='P0001';
  end if;

  -- 192-bit random token, with the same 7-day / five-download policy as
  -- the existing paid-order receipt links.
  v_token := pg_catalog.encode(extensions.gen_random_bytes(24), 'hex');
  insert into public.download_tokens (token, order_id, expires_at, max_downloads)
  values (v_token, v_order_id, v_now + interval '7 days', 5);
  return v_token;
end;
$$;
revoke all on function public.renew_my_download(text) from public, anon;
grant execute on function public.renew_my_download(text) to authenticated;

comment on function public.renew_my_download(text) is
  'Private self-service download renewal for a verified buyer of a paid order. Existing active links reused; expired/used links replaced with rate limiting.';
