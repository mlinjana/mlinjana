"""Listing records + marketplace exports + channel adapters.

Rules: a listing is only 'live' after its public URL has been fetched successfully (health check or verify step).
Channels without authorised access stay 'awaiting_authorisation' with the exact requirement recorded.
Usage: python3 engine/publish.py [--verify-own]
"""
import csv, json, os, sys, urllib.request

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CFG = json.load(open(os.path.join(ROOT, "config", "stores.json")))
LISTINGS = os.path.join(ROOT, "catalogue", "listings.json")

REQUIREMENTS = {
    "etsy": "Owner must open an Etsy shop (identity & bank verification) and register an Etsy API app with listings_w scope; "
            "Etsy charges a listing fee per listing (needs your authorisation).",
    "gumroad": "Owner must create a Gumroad account, connect payouts, and provide an access token (GUMROAD_ACCESS_TOKEN).",
    "payhip": "Owner must create a Payhip account and connect PayPal for payouts. No public listing API was found, so listings use the export CSV.",
    "shopify": "Connected Shopify store is on a trial plan — selling requires a paid plan (your authorisation) and a digital-downloads app.",
}


def load_existing():
    return {(l["product_id"], l["channel"]): l for l in json.load(open(LISTINGS))} if os.path.exists(LISTINGS) else {}


def build_records(products):
    old = load_existing()
    out = []
    for p in products:
        if not p["validation"].get("ok"):
            continue
        store = next(s for s in CFG["stores"] if s["id"] == p["store"])
        url = f"{CFG['site_base']}/{store['path']}/p/{p['slug']}.html"
        prev = old.get((p["id"], "own_store"), {})
        out.append({"product_id": p["id"], "channel": "own_store", "url": url, "price_cents": p["price_zar"] * 100, "currency": "ZAR",
                    "external_id": p["slug"], "status": prev.get("status") if prev.get("url") == url and prev.get("status") == "live" else "pending_verification",
                    "last_error": None})
        for ch, req in REQUIREMENTS.items():
            prev = old.get((p["id"], ch), {})
            if prev.get("status") in ("live", "draft") and prev.get("external_id"):
                out.append(prev)
                continue
            out.append({"product_id": p["id"], "channel": ch, "url": None, "price_cents": int(round(p["price_usd"] * 100)), "currency": "USD",
                        "external_id": None, "status": "awaiting_authorisation", "last_error": req})
    return out


def verify(records):
    """Fetch each URL we hold (12 at a time); mark live only on HTTP 2xx/3xx."""
    from concurrent.futures import ThreadPoolExecutor

    def check(r):
        try:
            req = urllib.request.Request(r["url"], headers={"User-Agent": "commerce-network-verify/1"})
            code = urllib.request.urlopen(req, timeout=20).status
        except Exception as e:
            code = getattr(e, "code", 0)
        r["status"] = "live" if 200 <= code < 400 else "failed"
        r["last_error"] = None if r["status"] == "live" else f"HTTP {code}"

    with ThreadPoolExecutor(12) as ex:
        list(ex.map(check, [r for r in records if r.get("url")]))
    return records


def exports(products):
    os.makedirs(os.path.join(ROOT, "catalogue", "exports"), exist_ok=True)
    path = os.path.join(ROOT, "catalogue", "exports", "marketplace_listings.csv")
    with open(path, "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["product_id", "store", "title_seo", "name", "description", "tags", "price_usd", "price_zar", "category", "formats",
                    "file_key", "cover_image", "preview_images"])
        for p in products:
            if p["validation"].get("ok"):
                w.writerow([p["id"], p["store"], p["title"], p["name"], p["description"], ",".join(p["tags"]), f"{p['price_usd']:.2f}",
                            p["price_zar"], p["category"], " + ".join(p["formats"]), p["file"]["key"], p["images"]["marketplace"][0] if p["images"].get("marketplace") else "",
                            " | ".join(p["images"].get("marketplace", [])[1:])])
    return path


class GumroadAdapter:
    """Creates unpublished Gumroad products from listing records. UNTESTED: needs GUMROAD_ACCESS_TOKEN.
    Endpoint per Gumroad API v2 docs (POST /v2/products) — verify against current docs before the first run.
    Product files must then be attached in Gumroad; status stays 'draft' (never 'live') until the URL is verified."""
    API = "https://api.gumroad.com/v2/products"

    def __init__(self, token):
        self.token = token

    def create(self, p):
        import urllib.parse
        data = urllib.parse.urlencode({"access_token": self.token, "name": p["name"], "price": int(round(p["price_usd"] * 100)),
                                       "description": p["description"].replace("\n", "<br>")}).encode()
        with urllib.request.urlopen(urllib.request.Request(self.API, data=data, method="POST"), timeout=30) as r:
            d = json.load(r)
        if not d.get("success"):
            raise RuntimeError(d)
        return d["product"]["id"], d["product"].get("short_url")


def main():
    products = json.load(open(os.path.join(ROOT, "catalogue", "products.json")))["products"]
    recs = build_records(products)
    if "--verify-own" in sys.argv:
        verify([r for r in recs if r["channel"] == "own_store"])
    tok = os.environ.get("GUMROAD_ACCESS_TOKEN")
    if tok and "--gumroad" in sys.argv:
        g = GumroadAdapter(tok)
        for r in recs:
            if r["channel"] == "gumroad" and r["status"] == "awaiting_authorisation":
                p = next(x for x in products if x["id"] == r["product_id"])
                try:
                    r["external_id"], r["url"] = g.create(p)
                    r["status"], r["last_error"] = "draft", "Attach the ZIP in Gumroad, then publish; verified on next health check"
                except Exception as e:
                    r["status"], r["last_error"] = "failed", str(e)[:300]
    json.dump(recs, open(LISTINGS, "w"), indent=1)
    exp = exports(products)
    from collections import Counter
    print("listings:", dict(Counter((r["channel"], r["status"]) for r in recs)), "| export:", os.path.relpath(exp, ROOT))


if __name__ == "__main__":
    main()
