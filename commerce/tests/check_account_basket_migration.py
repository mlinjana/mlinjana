"""Verify account_baskets migration in disposable PostgreSQL, never production."""
from pathlib import Path
import os
import psycopg

SQL = (Path(__file__).resolve().parents[1] / "supabase/migrations/012_account_baskets.sql").read_text()
A = "aaaaaaaa-aaaa-4aaa-aaaa-aaaaaaaaaaaa"
B = "bbbbbbbb-bbbb-4bbb-bbbb-bbbbbbbbbbbb"
DSN = os.environ["ISOLATED_POSTGRES_DSN"]

with psycopg.connect(DSN, autocommit=True) as c:
    c.execute("create schema auth")
    c.execute("create table auth.users (id uuid primary key)")
    c.execute("insert into auth.users values (%s), (%s)", (A, B))
    c.execute("create role authenticated nologin")
    c.execute("create role anon nologin")
    c.execute("grant usage on schema public, auth to authenticated")
    c.execute("""create function auth.uid() returns uuid language sql stable
               as $$ select nullif(current_setting('request.jwt.claim.sub', true),'')::uuid $$""")
    c.execute("grant execute on function auth.uid() to authenticated")
    c.execute(SQL)
    with c.cursor() as cur:
        cur.execute("select relrowsecurity from pg_class where oid='public.account_baskets'::regclass")
        assert cur.fetchone()[0], "RLS must be enabled"
        cur.execute("select has_table_privilege('anon','public.account_baskets','SELECT')")
        assert cur.fetchone()[0] is False, "Anonymous visitors must not read baskets"
        cur.execute("set role authenticated")
        cur.execute("select set_config('request.jwt.claim.sub',%s,false)", (A,))
        cur.execute("insert into public.account_baskets(user_id,items) values (%s,%s::jsonb)",(A,'["ABL-009","BZW-003:team"]'))
        cur.execute("select items from public.account_baskets")
        assert cur.fetchone()[0]==["ABL-009","BZW-003:team"]
        try:
            cur.execute("insert into public.account_baskets(user_id,items) values (%s,%s::jsonb)",(B,'["CHK-011"]'))
            raise AssertionError("A must not be allowed to insert B's basket")
        except psycopg.errors.InsufficientPrivilege: pass
        cur.execute("select set_config('request.jwt.claim.sub',%s,false)",(B,))
        cur.execute("select count(*) from public.account_baskets")
        assert cur.fetchone()[0]==0, "B must not see A's basket"
        cur.execute("insert into public.account_baskets(user_id,items) values (%s,%s::jsonb)",(B,'["CHK-011"]'))
        cur.execute("select items from public.account_baskets")
        assert cur.fetchone()[0]==["CHK-011"], "B sees only own items"
        try:
            cur.execute("update public.account_baskets set user_id=%s where user_id=%s",(A,B))
            raise AssertionError("B must not assign basket to A")
        except (psycopg.errors.InsufficientPrivilege,psycopg.errors.ForeignKeyViolation): pass
        cur.execute("select set_config('request.jwt.claim.sub',%s,false)",(A,))
        cur.execute("update public.account_baskets set items=%s::jsonb where user_id=%s",('["ABL-025"]',A))
        cur.execute("select items from public.account_baskets")
        assert cur.fetchone()[0]==["ABL-025"]
print("PASS: account baskets RLS blocks cross-user reads/writes and supports per-user upsert")
