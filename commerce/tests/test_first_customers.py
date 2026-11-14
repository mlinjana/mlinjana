"""Regression checks for the first-customer conversion improvements.

Runs AFTER engine/build_sites.py. Does not reach external APIs or execute payments.
"""
from pathlib import Path
import json
import re
import unittest

ROOT = Path(__file__).resolve().parents[1]
SITE = ROOT / "site"


class FirstCustomerStorefrontTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.home = (SITE / "index.html").read_text(encoding="utf-8")
        cls.catalogue = json.loads((SITE / "assets" / "catalogue.json").read_text(encoding="utf-8"))

    def test_homepage_has_task_discovery(self):
        self.assertIn('id="shop-by-task"', self.home)
        self.assertIn('id="task-shop-title"', self.home)
        self.assertIn("What do you need to get done?", self.home)

    def test_task_links_resolve_to_generated_category_pages(self):
        for url in (
            "/business/inventory-management/",
            "/business/finance-budgeting/",
            "/life/personal-finance/",
            "/education/teacher-resources/",
        ):
            with self.subTest(url=url):
                self.assertIn('href="' + url + '"', self.home)
                self.assertTrue((SITE / url.lstrip("/") / "index.html").is_file())

    def test_homepage_explains_offer_for_search_engines(self):
        self.assertIn("Ready-to-use business templates", self.home)
        self.assertIn('name="description"', self.home)
        self.assertIn("Preview actual pages", self.home)

    def test_product_copy_has_order_recovery(self):
        pages = sorted((SITE / "bizwright" / "p").glob("*.html"))
        self.assertGreater(len(pages), 0, "Expected generated Bizwright product pages")
        sample = pages[0].read_text(encoding="utf-8")
        self.assertIn("Review the actual file previews", sample)
        self.assertIn("Digital download, no shipping", sample)
        self.assertIn('href="/help/downloads"', sample)

    def test_new_conversion_events_match_database_constraint_and_api(self):
        js = (ROOT / "engine/static/site.js").read_text(encoding="utf-8")
        api = (ROOT / "supabase/functions/store-api/index.ts").read_text(encoding="utf-8")
        migration = (ROOT / "supabase/migrations/011_conversion_funnel.sql").read_text(encoding="utf-8")
        for event in ("basket_add", "checkout_handoff", "checkout_error"):
            with self.subTest(event=event):
                self.assertIn('type: "' + event + '"', js)
                self.assertIn('"' + event + '"', api)
                self.assertIn("'" + event + "'", migration)
        self.assertIn("f.submit()", js, "Do not remove the PayFast handoff")
        self.assertNotIn('type: "payment_success"', js,
                         "Payment must only be confirmed by the backend, not the browser")


if __name__ == "__main__":
    unittest.main()
