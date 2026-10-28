"""Evidence-based price recommendations → config/pricing.json + research/pricing.csv.

Method (deterministic, no AI at run time):
  1. Each product maps to a benchmark: list prices observed on Etsy/Gumroad/Payhip/Flevy (research 2026-10-28, sources below).
  2. Marketplace price (USD) sits inside the observed *typical* band — mid-market, not premium, because a new shop has no reviews.
     Products with more content than typical listings (verified page/formula counts) sit at the upper half of the band.
  3. Own-store price (ZAR) = USD × FX × LOCAL_FACTOR, rounded to the nearest R..9, minimum R39.
     LOCAL_FACTOR 0.75 reflects SA buying power and lower own-store fees (PayFast ≈3.2%+R2 vs Etsy 6.5% + processing + listing fee).
  4. Bundles are priced below the sum of their components; the saving shown to buyers is computed, never hard-coded.
Observed prices are snapshots (many listings run time-limited sales). Re-run after collecting real conversion data.
Usage: python3 engine/pricing.py
"""
import csv, json, os

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
FX = 16.4            # USD→ZAR, mid-2026 dated quotes (16.43 on 2026-07-21); October 2026 rate not verified
LOCAL_FACTOR = 0.75
MIN_ZAR = 39

S = {  # sources (search snapshots, 2026-10-28)
    "etsy_budget": "Etsy budget planner listings $1.12–$14.06; seller guide: single printables $3–6, systems $7–12 (promptlesspress.com)",
    "undated": "RankHero 'undated digital planner': median $7.48, range $2–21 (n=58)",
    "journal": "Gratitude journals: Etsy $0.60 sale (from $2.40), Payhip $2.99–$3, Gumroad $15, Payhip $19",
    "student_meal": "Etsy meal & student planners mostly $1–4; 40-page undated student planner $7",
    "debt": "Etsy debt snowball/avalanche spreadsheets $2–14.99; full-feature examples $7–9.99",
    "bizplan": "Gumroad business plan + financial model: $5+ pack, $45 kit (Word + Excel model), $50 template; €39 pack",
    "inventory": "Etsy/Payhip inventory spreadsheets: basic $1–5, fuller $6–15, systems $25–100+",
    "invoice": "Gumroad Excel/Sheets invoice templates free–$10; $3 bundle",
    "sop": "Gumroad SOP templates $5 (Word) to £9–£17 (kits with guide)",
    "gantt": "Etsy/Gumroad Gantt/project trackers: basic $3–8, dashboard packages $12–25, up to $39",
    "social": "Etsy social content planners: $2–5 basic, $5–11 mid, $15–30 all-in-one",
    "crm": "Etsy/Gumroad CRM & pipeline sheets $4.67–$20 (typical $7.95–$12.90)",
    "loan": "Gumroad amortisation templates $3; extra-payment mortgage calculator $19.99",
    "warehouse": "Warehouse/logistics KPI templates: Flevy $29–45, SCMDOJO $59, Gumroad A$47–$100; Etsy inventory system $10.25 sale",
    "guide": "TheBricks guide: simple trackers $5–10; complex multi-tab dashboards $40–75",
    "none": "No direct comparable found in research — estimate by analogy",
}

# slug: (usd, source_key, basis, rationale)
PLAN = {
    # ---- Plainday (printables)
    "undated-daily-planner": (6, "undated", "benchmark", "95 pages; below the $7.48 median for a new shop"),
    "undated-weekly-planner": (6.5, "undated", "benchmark", "119 pages incl. 52 reviews; near median"),
    "monthly-budget-planner": (7, "etsy_budget", "benchmark", "44-page complete system → 'system' band $7–12, low end"),
    "savings-challenge-pack": (4, "etsy_budget", "benchmark", "single-purpose band $3–6"),
    "guided-gratitude-journal": (5, "journal", "benchmark", "90 original prompts; between $3 Payhip and $15 Gumroad"),
    "weekly-reflection-journal": (5, "journal", "benchmark", "52 prompts + annual review"),
    "goal-setting-workbook": (7, "etsy_budget", "benchmark", "workbook system band $7–12, low end"),
    "student-study-planner": (5, "student_meal", "benchmark", "25 pages; between $1–4 basics and $7 40-page planner"),
    "exam-revision-planner": (4, "student_meal", "benchmark", "focused 15-page toolkit"),
    "habit-tracker-set": (3.5, "etsy_budget", "benchmark", "single-purpose band"),
    "home-cleaning-schedule": (3, "student_meal", "benchmark", "7 pages; low band"),
    "meal-planner-grocery-list": (3.5, "student_meal", "benchmark", "24 pages; top of $1–4 band"),
    "home-organisation-binder": (6, "etsy_budget", "benchmark", "binder system, lower 'system' band"),
    "productivity-planner": (6, "undated", "benchmark", "51 pages time-blocking + matrix"),
    "personal-project-planner": (4, "etsy_budget", "benchmark", "single-purpose band"),
    "wellness-mood-tracker": (4, "etsy_budget", "benchmark", "single-purpose band"),
    "reading-journal": (3.5, "journal", "benchmark", "low band"),
    "yearly-planner-annual-review": (4.5, "undated", "benchmark", "below median"),
    "travel-planner": (3.5, "student_meal", "benchmark", "low band"),
    "productivity-planner-bundle": (14, "etsy_budget", "benchmark", "bundles observed $7–15"),
    # ---- Bizwright (business templates)
    "business-plan-template": (19, "bizplan", "benchmark", "Word plan + 36-month model; below $45–50 kits"),
    "lean-canvas-one-page-plan": (4, "bizplan", "benchmark", "low-content; near $5 entry packs"),
    "invoice-template-excel": (5, "invoice", "benchmark", "mid of free–$10; adds register + overdue tracking"),
    "quotation-estimate-template": (5, "invoice", "benchmark", "same band as invoices"),
    "income-expense-tracker": (7, "guide", "benchmark", "simple tracker band $5–10"),
    "marketing-calendar": (7, "social", "benchmark", "mid band $5–11"),
    "social-media-content-planner": (8, "social", "benchmark", "mid band with analytics"),
    "sop-template-kit": (12, "sop", "benchmark", "5 worked examples; between $5 and £17 kits"),
    "project-management-tracker": (14, "gantt", "benchmark", "Gantt + dashboard + RACI + risks → $12–25 band"),
    "client-crm-sales-pipeline": (12, "crm", "benchmark", "weighted forecast; typical $8–13"),
    "employee-onboarding-kit": (9, "none", "estimate", "analogy: SOP/CRM kits $8–17"),
    "meeting-agenda-minutes-kit": (5, "none", "estimate", "analogy: simple Word templates ~$5"),
    "hiring-kit": (9, "none", "estimate", "analogy: multi-document HR kits"),
    "customer-feedback-complaints-log": (6, "guide", "estimate", "simple tracker band $5–10"),
    "pricing-calculator": (7, "guide", "benchmark", "simple tracker band $5–10"),
    "brand-style-guide-template": (8, "none", "estimate", "analogy: Word kits $5–17"),
    "small-business-kpi-dashboard": (15, "guide", "benchmark", "below complex dashboards ($40–75); simpler scope"),
    "purchase-order-supplier-kit": (5, "invoice", "benchmark", "same band as invoices"),
    "ceo-weekly-business-planner": (7, "etsy_budget", "benchmark", "printable system band"),
    "business-admin-bundle": (16, "invoice", "benchmark", "bundle of 4 below component sum"),
    # ---- Abacus Lane (finance & operations)
    "personal-budget-dashboard": (9, "guide", "benchmark", "dashboard + 2,000-row log; upper simple band"),
    "debt-snowball-avalanche-calculator": (9, "debt", "benchmark", "full-feature listings $7–10; tested 30-year engine"),
    "savings-goal-tracker": (5, "guide", "benchmark", "simple tracker band"),
    "emergency-fund-calculator": (4, "guide", "benchmark", "single-purpose"),
    "net-worth-tracker": (6, "guide", "benchmark", "simple tracker band"),
    "annual-personal-finance-workbook": (8, "guide", "benchmark", "multi-tab workbook"),
    "loan-amortisation-calculator": (7, "loan", "benchmark", "between $3 basic and $19.99 calculator"),
    "home-loan-calculator": (9, "loan", "benchmark", "4 tools in one; below $19.99"),
    "inventory-management-spreadsheet": (12, "inventory", "benchmark", "fuller templates $6–15"),
    "stock-control-reorder-point": (19, "inventory", "benchmark", "safety stock + EOQ; between fuller ($15) and systems ($25+)"),
    "warehouse-productivity-dashboard": (29, "warehouse", "benchmark", "low end of $29–59 warehouse KPI band"),
    "supply-chain-kpi-toolkit": (29, "warehouse", "benchmark", "low end of $29–59 band"),
    "abc-inventory-analysis": (12, "inventory", "estimate", "analogy: fuller inventory templates"),
    "13-week-cash-flow-forecast": (12, "guide", "estimate", "between simple ($10) and complex ($40+)"),
    "break-even-profit-calculator": (6, "guide", "benchmark", "simple tracker band"),
    "sinking-funds-bill-tracker": (5, "etsy_budget", "benchmark", "single-purpose band"),
    "compound-interest-retirement-projector": (6, "guide", "benchmark", "simple calculator band"),
    "shared-expense-splitter": (4, "guide", "benchmark", "single-purpose"),
    "demand-forecasting-template": (15, "guide", "estimate", "4 methods + accuracy; below complex dashboards"),
    "operations-toolkit-bundle": (65, "warehouse", "benchmark", "5 tools (sum $101) at ~35% off"),
}


def zar(usd):
    v = round(usd * FX * LOCAL_FACTOR / 10) * 10 - 1
    return max(MIN_ZAR, int(v))


# Niche stores whose buyers use the product to run a business (higher willingness to pay in the same bands).
B2B = {"bizwright", "doorpost", "gigsmith", "goodledger", "mise", "shopkeeper", "trowel", "chairbook", "fleetwise"}


def half(x):
    return round(x * 2) / 2


def band_rule(p):
    """Category-band estimate for products without an individual benchmark (all niche products, 2026-10-28).
    Bands come from the same research snapshots as PLAN: single printables $3–6, printable systems $7–12 (etsy_budget);
    simple trackers $5–10 (guide); Word templates $5 to ~$12 for kits (sop). Business-use products sit ~30% higher in band."""
    info = p.get("validation", {}).get("info", {})
    biz = p["store"] in B2B
    fmt = p["formats"][0]
    if fmt.startswith("PDF"):
        pages = max(info.get("pdf_pages", {"": 0}).values()) if info.get("pdf_pages") else 0
        usd = 3 if pages <= 8 else 3.5 if pages <= 20 else 4.5 if pages <= 45 else 5.5
        return half(min(usd * (1.2 if biz else 1), 7)), "etsy_budget", f"{pages}-page printable → single-printable band $3–6"
    if fmt == "DOCX":
        pages = max(info.get("docx_pages", {"": 1}).values()) if info.get("docx_pages") else 1
        usd = 6 if pages <= 2 else 7 if pages <= 4 else 8
        return half(usd * (1.25 if biz else 1)), "sop", f"{pages}-page editable Word template → Word template band $5–12"
    calc = any(str(f).startswith("Inputs:") for f in p["features"])
    sheets = sum(1 for f in p["features"] if str(f).startswith("'"))
    usd = 5 if calc else 6 + min(2, max(0, sheets - 1))
    return half(min(usd * (1.3 if biz else 1), 12)), "guide", ("calculator" if calc else f"{sheets}-log tracker") + " → simple-tracker band $5–10"


def main():
    cat = json.load(open(os.path.join(ROOT, "catalogue", "products.json")))["products"]
    by_slug = {p["slug"]: p for p in cat}
    plan = dict(PLAN)
    for p in cat:  # products without an individual benchmark get the category-band rule (bundles below)
        if p["slug"] not in plan and not p.get("bundle_of"):
            usd, src, why = band_rule(p)
            plan[p["slug"]] = (usd, src, "estimate (category band)", why)
    for p in cat:
        if p["slug"] not in plan and p.get("bundle_of"):
            parts = sum(plan[c][0] for c in p["bundle_of"])
            plan[p["slug"]] = (half(parts * 0.65), "none", "estimate (bundle ≈65% of parts)", f"{len(p['bundle_of'])} products (sum ${parts:g}) + bonus at ~35% off")
    missing = [p["slug"] for p in cat if p["slug"] not in plan]
    if missing:
        raise SystemExit(f"no price plan for: {missing}")
    out, rows = {}, []
    for slug, (usd, src, basis, why) in plan.items():
        out[slug] = {"price_usd": usd, "price_zar": zar(usd), "basis": basis}
    for slug, p in by_slug.items():  # bundle savings, computed
        if p.get("bundle_of"):
            su = sum(out[c]["price_usd"] for c in p["bundle_of"])
            sz = sum(out[c]["price_zar"] for c in p["bundle_of"])
            out[slug]["saving_pct_usd"] = round(100 * (1 - out[slug]["price_usd"] / su))
            out[slug]["saving_pct_zar"] = round(100 * (1 - out[slug]["price_zar"] / sz))
            if out[slug]["price_usd"] >= su or out[slug]["price_zar"] >= sz:
                raise SystemExit(f"bundle {slug} is not cheaper than its parts")
    for slug, (usd, src, basis, why) in plan.items():
        p = by_slug[slug]
        rows.append([p["id"], slug, p["store"], f"{p['price_usd']:.2f}", p["price_zar"], f"{usd:.2f}", out[slug]["price_zar"], basis, S[src], why])
    json.dump({"fx_usd_zar": FX, "local_factor": LOCAL_FACTOR, "researched_on": "2026-10-28", "prices": out},
              open(os.path.join(ROOT, "config", "pricing.json"), "w"), indent=1)
    with open(os.path.join(ROOT, "research", "pricing.csv"), "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["product_id", "slug", "store", "old_usd", "old_zar", "new_usd", "new_zar", "basis", "market_evidence", "rationale"])
        w.writerows(rows)
    n_est = sum(1 for v in plan.values() if v[2].startswith("estimate"))
    print(f"priced {len(out)} products ({len(out) - n_est} benchmarked, {n_est} estimates); FX {FX}, local factor {LOCAL_FACTOR}")
    for slug in ("productivity-planner-bundle", "business-admin-bundle", "operations-toolkit-bundle"):
        print(" ", slug, out[slug])


if __name__ == "__main__":
    main()
