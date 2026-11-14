"""Frontend-only commerce release acceptance checks (no DB or payment changes)."""
from pathlib import Path
import unittest

ROOT=Path(__file__).resolve().parents[1]
SITE=ROOT/"site"

class FrontendRelease(unittest.TestCase):
    def test_homepage(self):
        s=(SITE/"index.html").read_text(encoding="utf-8")
        self.assertIn('href="/start-here"',s)
        self.assertIn('id="shop-by-task"',s)
        for path in ("business/inventory-management","business/finance-budgeting","life/personal-finance","education/teacher-resources"):
            self.assertTrue((SITE/path/"index.html").exists(),path)

    def test_curated_products(self):
        s=(SITE/"start-here.html").read_text(encoding="utf-8")
        self.assertEqual(s.count('class="starter-item"'),5)
        for path in ("abacus/p/inventory-management-spreadsheet","bizwright/p/invoice-template-excel",
                     "abacus/p/50-30-20-budget-calculator","chalkline/p/weekly-lesson-planner",
                     "fleetwise/p/small-fleet-control-bundle"):
            self.assertIn('href="/'+path+'"',s)
            self.assertTrue((SITE/(path+".html")).exists(),path)

    def test_purchase_backend_unchanged(self):
        # Release separation: frontend-only PR must not carry backend tracking migration.
        self.assertFalse((ROOT/"supabase/migrations/011_conversion_funnel.sql").exists())
        js=(ROOT/"engine/static/site.js").read_text(encoding="utf-8")
        for event in ("basket_add","checkout_handoff","checkout_error"):
            self.assertNotIn('type: "'+event+'"',js)

if __name__=="__main__":
    unittest.main()
