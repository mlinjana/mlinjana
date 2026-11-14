from pathlib import Path
import unittest
from html.parser import HTMLParser
SITE = Path(__file__).resolve().parents[1] / "site"
class Refresh(unittest.TestCase):
    def test_product_purchase_order_and_renewal(self):
        for path in SITE.glob("*/p/*.html"):
            s = path.read_text()
            self.assertLess(s.index('aria-label="Buy"'), s.index("What's inside"), str(path))
            if 'id="free-dl"' not in s:
                self.assertIn('Renew &amp; download', s, str(path))
                self.assertIn('class="pp-compat"', s, str(path))
    def test_invoice_recommendations(self):
        s = (SITE / "bizwright/p/invoice-template-excel.html").read_text()
        related = s.split('You may also like')[1]
        self.assertIn('13-week-cash-flow-forecast', related)
        self.assertNotIn('fuel-card-reconciliation', related)
    def test_home_has_real_product_hero_and_faq(self):
        s = (SITE / "index.html").read_text()
        self.assertIn('class="ph-art product-hero"', s)
        self.assertIn('shopping-faq-title', s)
        self.assertNotIn('Popular in Business', s)
        self.assertIn('Featured tools', s)
if __name__ == "__main__": unittest.main()
