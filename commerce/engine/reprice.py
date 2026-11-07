"""Set every product's price from its content (owner, 7 Nov 2026: "the prices must match the products").

Reads docs/2.0/value-audit.csv (engine/value_audit.py) and writes config/pricing.json, which the factory applies to the
catalogue (factory/run.py apply_pricing). Rules (docs/2.0/QUALITY-STANDARD.md):
  - single products: the audit's fair ceiling for the content as it is today;
  - bundles: at most 65% of the sum of their items' new prices, snapped down to a price point, never below R49;
  - USD (marketplace listings) = ZAR / FX / local factor from the existing pricing.json, rounded to $0.50, minimum $2.
Run value_audit.py first, then this, then the factory (to refresh the catalogue), sync and site build.
Usage: python3 engine/reprice.py [--dry-run]
"""
import csv, json, os, sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
POINTS = [29, 39, 49, 59, 69, 79, 89, 99, 129, 149, 199, 249, 299]


def main(dry):
    pj = os.path.join(ROOT, "config", "pricing.json")
    cfg = json.load(open(pj))
    fx, lf = cfg["fx_usd_zar"], cfg["local_factor"]
    cat = {p["id"]: p for p in json.load(open(os.path.join(ROOT, "catalogue", "products.json")))["products"]}
    by_slug = {p["slug"]: p for p in cat.values()}
    audit = {r["id"]: r for r in csv.DictReader(open(os.path.join(ROOT, "docs", "2.0", "value-audit.csv")))}
    new = {}
    for pid, p in cat.items():
        if not p.get("bundle_of"):
            new[p["slug"]] = int(audit[pid]["fair_ceiling_zar"])
    for pid, p in cat.items():
        if p.get("bundle_of"):
            parts = sum(new[s] for s in p["bundle_of"])
            target = max(49, parts * 0.65)
            new[p["slug"]] = max([x for x in POINTS if x <= target] or [49])
    changes, out = [], {}
    for slug, zar in new.items():
        old = cfg["prices"].get(slug, {})
        usd = max(2.0, round(zar / fx / lf * 2) / 2)
        out[slug] = {"price_usd": usd, "price_zar": zar, "basis": "content audit 2026-11-07"}
        p = by_slug[slug]
        if p.get("bundle_of"):
            su = sum(out[s]["price_usd"] if s in out else max(2.0, round(new[s] / fx / lf * 2) / 2) for s in p["bundle_of"])
            sz = sum(new[s] for s in p["bundle_of"])
            out[slug]["saving_pct_zar"] = round(100 * (1 - zar / sz))
            out[slug]["saving_pct_usd"] = round(100 * (1 - usd / su)) if su else 0
        if old.get("price_zar") != zar:
            changes.append((p["id"], p["name"], old.get("price_zar"), zar))
    ups = [c for c in changes if c[2] is not None and c[3] > c[2]]
    downs = [c for c in changes if c[2] is not None and c[3] < c[2]]
    print(f"{len(changes)} price changes: {len(downs)} down, {len(ups)} up")
    for c in sorted(changes, key=lambda c: (c[2] or 0) - c[3], reverse=True)[:15]:
        print(f"  {c[0]:8} R{c[2]} -> R{c[3]}  {c[1][:60]}")
    for c in ups[:15]:
        print(f"  UP {c[0]:8} R{c[2]} -> R{c[3]}  {c[1][:60]}")
    if not dry:
        cfg["prices"] = out
        cfg["repriced_on"] = "2026-11-07"
        cfg["note"] = "Prices follow content (engine/value_audit.py + engine/reprice.py); benchmark notes kept in research/pricing.csv."
        json.dump(cfg, open(pj, "w"), indent=1)
        print("written", os.path.relpath(pj, ROOT))


if __name__ == "__main__":
    main("--dry-run" in sys.argv)
