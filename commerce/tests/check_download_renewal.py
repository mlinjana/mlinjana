"""Security and behaviour tests for self-service download renewal in disposable PostgreSQL.

Tests the exact checked-in migration against a minimal fixture. No production
database access, payment requests, customer identities, or real tokens are used.
"""
import os
import re
from pathlib import Path

import psycopg

DSN = os.environ["ISOLATED_POSTGRES_DSN"]
SQL = (Path(__file__).resolve().parents[1] / "supabase/migrations/013_self_service_download_renewal.sql").read_text(encoding="utf-8")
A = "aaaaaaaa-aaaa-4aaa-aaaa-aaaaaaaaaaaa"
B = "bbbbbbbb-bbbb-4bbb-bbbb-bbbbbbbbbbbb"
A_PAID = "11111111-1111-4111-8111-111111111111"
B_PAID = "22222222-2222-4222-8222-222222222222"
A_PENDING = "33333333-3333-4333-8333-333333333333"
A_REFUNDED = "44444444-4444-4444-8444-444444444444"
A_REVOKED = "55555555-5555-4555-8555-555555555555"
A_RATE = "66666666-6666-4666-8666-666666666666"

def renew(cur, ref):
    cur.execute("select public.renew_my_download(%s)", (ref,))
    return cur.fetchone()[0]

def expect_denied(cur, ref):
    try:
        renew(cur, ref)
    except psycopg.Error:
        return
    raise AssertionError(f"Order {ref} incorrectly allowed to renew")

with psycopg.connect(DSN, autocommit=True) as db:
    with db.cursor() as c:
        c.execute("create schema auth")
        c.execute("create schema extensions")
        c.execute("create extension if not exists pgcrypto with schema extensions")
        c.execute("create role authenticated nologin")
        c.execute("create role anon nologin")
        c.execute("grant usage on schema public, auth to authenticated")
        c.execute("create table auth.users (id uuid primary key, email text not null, email_confirmed_at timestamptz)")
        c.execute("""create function auth.uid() returns uuid language sql stable as
                     $$ select nullif(current_setting('request.jwt.claim.sub', true),'')::uuid $$""")
        c.execute("grant execute on function auth.uid() to authenticated")
        c.execute("""create table public.orders (
                  id uuid primary key, ref text unique not null, email text not null, status text not null
                )""")
        c.execute("""create table public.download_tokens (
                  token text primary key, order_id uuid not null references public.orders(id),
                  expires_at timestamptz not null, max_downloads integer not null default 5,
                  downloads integer not null default 0, revoked boolean not null default false,
                  created_at timestamptz not null default now()
                )""")
        c.execute("insert into auth.users values (%s,'a@example.invalid',now()),(%s,'b@example.invalid',now())",(A,B))
        orders=[
          (A_PAID,"ORD-AAAAAAAAAAAA","a@example.invalid","paid"),
          (B_PAID,"ORD-BBBBBBBBBBBB","b@example.invalid","paid"),
          (A_PENDING,"ORD-CCCCCCCCCCCC","a@example.invalid","pending"),
          (A_REFUNDED,"ORD-DDDDDDDDDDDD","a@example.invalid","refunded"),
          (A_REVOKED,"ORD-EEEEEEEEEEEE","a@example.invalid","paid"),
          (A_RATE,"ORD-FFFFFFFFFFFF","a@example.invalid","paid"),
        ]
        for row in orders:
            c.execute("insert into public.orders values (%s,%s,%s,%s)",row)
        c.execute("""insert into public.download_tokens(token,order_id,expires_at,max_downloads,downloads)
                     values ('expired-original',%s,now()-interval '1 day',5,0)""",(A_PAID,))
        c.execute("""insert into public.download_tokens(token,order_id,expires_at,revoked)
                     values ('revoked-original',%s,now()+interval '1 day',true)""",(A_REVOKED,))
        for i in range(5):
            c.execute("""insert into public.download_tokens(token,order_id,expires_at,created_at)
                         values (%s,%s,now()-interval '1 day',now()-interval '1 hour')""",(f"limit-{i}",A_RATE))
        c.execute(SQL)

        # The function is executable only by authenticated clients.
        c.execute("select has_function_privilege('anon','public.renew_my_download(text)','EXECUTE')")
        assert c.fetchone()[0] is False, "Anonymous role must not execute renewal RPC"
        c.execute("select has_function_privilege('authenticated','public.renew_my_download(text)','EXECUTE')")
        assert c.fetchone()[0] is True

        c.execute("set role authenticated")
        c.execute("select set_config('request.jwt.claim.sub',%s,false)", (A,))
        token=renew(c,"ORD-AAAAAAAAAAAA")
        assert re.fullmatch(r"[a-f0-9]{48}",token),token
        same=renew(c,"ORD-AAAAAAAAAAAA")
        assert token==same, "Active link must be reused rather than multiplied"
        c.execute("select count(*) from public.download_tokens where order_id=%s",(A_PAID,))
        assert c.fetchone()[0]==2
        c.execute("select max_downloads,downloads,expires_at > now() from public.download_tokens where token=%s",(token,))
        assert c.fetchone()==(5,0,True)

        # Existing active link can be used up to five times, then renewed.
        c.execute("update public.download_tokens set downloads=5 where token=%s",(token,))
        refreshed=renew(c,"ORD-AAAAAAAAAAAA")
        assert refreshed!=token
        expect_denied(c,"ORD-BBBBBBBBBBBB")  # User A cannot renew B's order.
        expect_denied(c,"ORD-CCCCCCCCCCCC")  # Not paid.
        expect_denied(c,"ORD-DDDDDDDDDDDD")  # Refunded.
        expect_denied(c,"ORD-EEEEEEEEEEEE")  # Revoked access.
        expect_denied(c,"ORD-FFFFFFFFFFFF")  # Rate limit.
        expect_denied(c,"ORD-NOTANORDER")
        c.execute("select set_config('request.jwt.claim.sub',%s,false)", (B,))
        expect_denied(c,"ORD-AAAAAAAAAAAA")
        other=renew(c,"ORD-BBBBBBBBBBBB")
        assert re.fullmatch(r"[a-f0-9]{48}",other)
        assert other!=token
        c.execute("select set_config('request.jwt.claim.sub','',false)")
        expect_denied(c,"ORD-BBBBBBBBBBBB")
print("PASS: verified ownership, paid-only, active reuse, expired/used renew, revoked and rate-limit checks")
