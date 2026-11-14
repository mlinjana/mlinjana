"""Run the *staged migration* against disposable Postgres, never production.

The fixture deliberately contains only the events constraint modified by 011.
This verifies allowed event types and rejection of invalid types; it is not
an integration test for all Supabase auth/RLS policies.
"""
from pathlib import Path
import os
import psycopg

root = Path(__file__).resolve().parents[1]
sql = (root / "supabase/migrations/011_conversion_funnel.sql").read_text()
dsn = os.environ.get("ISOLATED_POSTGRES_DSN")
if not dsn:
    raise SystemExit("ISOLATED_POSTGRES_DSN is required; refusing to use other databases")

with psycopg.connect(dsn, autocommit=True) as db:
    with db.cursor() as cur:
        cur.execute("""CREATE TABLE public.events (
            id bigint generated always as identity primary key,
            type text NOT NULL,
            CONSTRAINT events_type_check
            CHECK (type IN ('page_view','product_view','checkout_start'))
        )""")
        cur.execute(sql)
        for kind in ("page_view", "product_view", "checkout_start",
                     "basket_add", "checkout_handoff", "checkout_error"):
            cur.execute("INSERT INTO public.events(type) VALUES (%s)", (kind,))
        try:
            cur.execute("INSERT INTO public.events(type) VALUES ('unrecognised_event')")
        except psycopg.errors.CheckViolation:
            pass
        else:
            raise AssertionError("Unknown event type was not rejected")
        cur.execute("SELECT count(*) FROM public.events")
        count = cur.fetchone()[0]
        assert count == 6, count
        print("Isolated migration constraint test passed:", count, "valid event types")
