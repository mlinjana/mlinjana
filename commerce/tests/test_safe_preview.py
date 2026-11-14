"""Assert that preview HTML cannot accept a payment and is not crawlable."""
from pathlib import Path
import unittest

site = Path(__file__).resolve().parents[1] / "site"


class SafePreviewTests(unittest.TestCase):
    def test_robots(self):
        self.assertIn("Disallow: /", (site / "robots.txt").read_text())
        self.assertFalse((site / "sitemap.xml").exists(), "Preview must not have a crawlable sitemap")

    def test_checkout_is_not_available(self):
        for page in (site / "index.html", site / "start-here.html",
                     site / "abacus/p/inventory-management-spreadsheet.html"):
            html = page.read_text(encoding="utf-8")
            with self.subTest(page=page.name):
                self.assertIn('content="noindex, nofollow"', html)
                self.assertIn("Orders are not open yet.", html)
                self.assertNotIn('id="bk-form"', html)
                self.assertIn('data-api="https://api.invalid/functions/v1"', html)
                self.assertIn("PayFast <strong>sandbox</strong>", html)


if __name__ == "__main__":
    unittest.main()
