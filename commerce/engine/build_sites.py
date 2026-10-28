"""Build every storefront in config/stores.json, the network index and the owner dashboard from catalogue/products.json.

Deterministic: same catalogue + config → same site. No AI calls.
Usage: python3 engine/build_sites.py
"""
import json, os, shutil, html, re
from jinja2 import Environment, FileSystemLoader, select_autoescape

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SITE = os.path.join(ROOT, "site")
BTN = {"plainday": "#4E7360", "bizwright": "#1D2B3A", "abacus": "#1E7A67"}  # hand-picked; other stores computed by btn_colour()


def _lum(hexc):
    c = [int(hexc[i:i + 2], 16) / 255 for i in (1, 3, 5)]
    c = [x / 12.92 if x <= 0.03928 else ((x + 0.055) / 1.055) ** 2.4 for x in c]
    return 0.2126 * c[0] + 0.7152 * c[1] + 0.0722 * c[2]


def btn_colour(accent):
    """Darken the accent until white text on it meets WCAG AA contrast (4.5:1)."""
    r, g, b = (int(accent[i:i + 2], 16) for i in (1, 3, 5))
    for _ in range(40):
        h = f"#{r:02X}{g:02X}{b:02X}"
        if 1.05 / (_lum(h) + 0.05) >= 4.5:
            return h
        r, g, b = int(r * 0.93), int(g * 0.93), int(b * 0.93)
    return "#222222"

env = Environment(loader=FileSystemLoader(os.path.join(ROOT, "engine", "templates")), autoescape=select_autoescape(["html"]))


def policies(store, legal):
    n = store["name"]
    return {
        "refunds": ("Refunds & support", f"""
<p>{n} sells digital downloads. Your files are available immediately after PayFast confirms your payment.</p>
<h2>If something is wrong</h2>
<p>If a file is faulty, doesn't match its description, or you can't open it with the software listed on the product page, contact us within 14 days of purchase with your order number. We'll help you get it working, send a corrected file, or refund you in full.</p>
<h2>Change of mind</h2>
<p>Because digital files can't be returned, we don't normally refund a change of mind once a file has been downloaded. If you bought the wrong product by mistake and haven't downloaded it, contact us and we'll help.</p>
<h2>How refunds are paid</h2>
<p>Approved refunds are made to the original payment method through PayFast. Your bank may take several working days to show it.</p>
<h2>Lost download link</h2>
<p>Links last 7 days and 5 downloads. If yours has expired, use the <a href="contact.html">contact form</a> with your order number and we'll send a new one.</p>
<p class="muted small">This policy does not limit any rights you have under the law of your country, including the South African Consumer Protection Act and Electronic Communications and Transactions Act where they apply.</p>"""),
        "privacy": ("Privacy", f"""
<p>We collect as little personal information as possible.</p>
<h2>What we collect</h2>
<ul><li><strong>Orders:</strong> your email address, the product, amount, date and payment status. We need these to deliver your files and keep tax records.</li>
<li><strong>Payments:</strong> handled entirely by PayFast. We never see or store your card or bank details. PayFast's own privacy policy applies to the payment step.</li>
<li><strong>Messages:</strong> what you send through the contact form.</li>
<li><strong>Visit statistics:</strong> page path, product viewed, and the website that referred you. No cookies, no IP addresses, no advertising trackers.</li></ul>
<h2>How we use it</h2>
<p>Only to deliver your order, provide support, keep business records and understand which products are useful. We don't sell or share your information for marketing, and we don't send newsletters unless you ask to join one.</p>
<h2>Where it's stored</h2>
<p>Order data is stored with our hosting provider (Supabase, EU data centre) with access restricted to the store owner.</p>
<h2>Your rights</h2>
<p>You can ask us what information we hold about you, ask us to correct it, or ask us to delete it (we may need to keep order records for tax law). Use the <a href="contact.html">contact form</a>. South African customers may also contact the Information Regulator.</p>
<p class="muted small">Responsible party: {html.escape(legal['operator'])}. Address: {html.escape(legal['address'])}.</p>"""),
        "terms": ("Terms of sale", f"""
<p>These terms apply when you buy from {n}.</p>
<h2>Seller</h2>
<p>{html.escape(legal['operator'])}, {html.escape(legal['country'])}. Registration: {html.escape(legal['registration'])}. Address: {html.escape(legal['address'])}. Contact: via the <a href="contact.html">contact form</a>.</p>
<h2>Products and prices</h2>
<p>All products are digital files described on their product pages, including format and compatibility. Prices are in South African rand (ZAR) and include any applicable taxes we're required to charge. Your bank sets the exchange rate for non-ZAR cards.</p>
<h2>Payment and delivery</h2>
<p>Payment is processed by PayFast. An order is only confirmed once PayFast notifies us that payment is complete; your download link then appears on the confirmation page.</p>
<h2>Licence</h2>
<p>Your purchase gives you a licence to use the files, not ownership of the copyright. See the <a href="licence.html">licence</a>.</p>
<h2>Liability</h2>
<p>Templates and calculators are tools. Check results before relying on them; nothing we sell is legal, tax or financial advice. To the extent the law allows, our liability is limited to the price you paid.</p>
<p class="muted small">Draft terms prepared for pre-launch testing — to be reviewed by the owner before live sales.</p>"""),
        "licence": ("Licence", f"""
<h2>You may</h2><ul><li>Use the product yourself or in your household.</li><li>Use it in one business you own or work for, including to serve your own customers (for example, sending invoices made with an invoice template).</li><li>Print it as often as you need for that use and edit it for yourself.</li></ul>
<h2>You may not</h2><ul><li>Resell, share, give away or upload the files — original or edited — where others can download them.</li><li>Sell printed copies or include the files in a product you sell.</li><li>Claim the design or content as your own.</li></ul>
<p>Need a licence for several businesses or a team? <a href="contact.html">Ask us</a> before using it that way.</p>"""),
        "contact": ("Contact & help", """
<p>Questions about a product or an order? Send us a message — we reply by email, usually within two working days.</p>
<form id="contact" novalidate>
<label for="c-email">Your email</label><input id="c-email" name="email" type="email" required autocomplete="email">
<label for="c-order">Order number (optional)</label><input id="c-order" name="order_ref" placeholder="ORD-…">
<label for="c-msg">Message</label><textarea id="c-msg" name="message" rows="6" required></textarea>
<input name="website" tabindex="-1" autocomplete="off" style="position:absolute;left:-9999px" aria-hidden="true">
<button class="btn" type="submit">Send message</button>
<p id="contact-msg" class="msg" role="status"></p>
</form>"""),
        "thanks": ("Thank you", """
<p>Order <strong id="order-ref">…</strong></p>
<div id="order-status" class="status">Checking your payment…</div>
<p class="muted small">Your download appears here as soon as PayFast confirms the payment. Keep this page — the link lets you download again.</p>"""),
    }


def jsonld(p, store, url):
    return json.dumps({"@context": "https://schema.org", "@type": "Product", "name": p["name"], "description": p["summary"],
                       "sku": p["id"], "brand": {"@type": "Brand", "name": store["name"]},
                       "offers": {"@type": "Offer", "price": f"{p['price_zar']:.2f}", "priceCurrency": "ZAR",
                                  "availability": "https://schema.org/InStock", "url": url}}).replace("</", "<\\/")


def main():
    cfg = json.load(open(os.path.join(ROOT, "config", "stores.json")))
    cat = json.load(open(os.path.join(ROOT, "catalogue", "products.json")))["products"]
    staging = cfg["mode"] != "live"
    for d in os.listdir(SITE) if os.path.isdir(SITE) else []:
        if d not in ("assets",):
            p = os.path.join(SITE, d)
            shutil.rmtree(p) if os.path.isdir(p) else os.remove(p)
    os.makedirs(os.path.join(SITE, "assets"), exist_ok=True)
    for f in ("site.css", "site.js", "dashboard.js"):
        src = os.path.join(ROOT, "engine", "static", f)
        if os.path.exists(src):
            shutil.copy(src, os.path.join(SITE, "assets", f))
    by_slug = {p["slug"]: p for p in cat}
    built, pages = [], 0
    for st in cfg["stores"]:
        st = dict(st)
        base_url = f"{cfg['site_base']}/{st['path']}"
        prods = [p for p in cat if p["store"] == st["id"] and p["validation"].get("ok") and p["images"].get("cover")]
        for p in prods:
            p["file_mb"] = f"{(p['file']['bytes'] or 0) / 1e6:.1f}"
            p["bundle_items"] = [by_slug[s] for s in p.get("bundle_of", [])]
            p["bundle_sum"] = sum(b["price_zar"] for b in p["bundle_items"])
        ctx = dict(store={**st, "accent_btn": BTN.get(st["id"]) or btn_colour(st["accent"])}, api=cfg["api_base"], staging=staging, base=f"/{st['path']}", root="/")
        out = os.path.join(SITE, st["path"])
        os.makedirs(os.path.join(out, "p"), exist_ok=True)
        cats = [c for c in st["categories"] if any(p["category"] == c for p in prods)]
        for p in prods:  # categories not listed in config appear in product order, bundles last
            if p["category"] not in cats and p["category"] != "Bundles":
                cats.append(p["category"])
        if any(p["category"] == "Bundles" for p in prods) and "Bundles" not in cats:
            cats.append("Bundles")
        open(os.path.join(out, "index.html"), "w").write(env.get_template("store_index.html").render(products=prods, categories=cats, **ctx))
        pages += 1
        for p in prods:
            related = [r for r in prods if r["category"] == p["category"] and r["id"] != p["id"]][:4]
            open(os.path.join(out, "p", p["slug"] + ".html"), "w").write(env.get_template("product.html").render(
                p=p, related=related, jsonld=jsonld(p, st, f"{base_url}/p/{p['slug']}.html"), **ctx))
            pages += 1
        for key, (title, body) in policies(st, cfg["legal"]).items():
            open(os.path.join(out, key + ".html"), "w").write(env.get_template("page.html").render(title=title, body=body, **ctx))
            pages += 1
        built.append({"id": st["id"], "path": st["path"], "name": st["name"], "url": base_url, "products": len(prods), "tagline": st["tagline"], "accent": st["accent"]})
    # network index (staging helper) + dashboard shell
    idx = ["<!doctype html><html lang=en><meta charset=utf-8><meta name=viewport content='width=device-width,initial-scale=1'>",
           "<meta name=robots content='noindex,nofollow'><title>Commerce network</title>",
           "<style>body{font:16px/1.5 system-ui,sans-serif;margin:0;background:#f6f7f9;color:#111}main{max-width:900px;margin:0 auto;padding:32px 16px}"
           "a.s{display:block;background:#fff;border:1px solid #ddd;border-left:6px solid var(--c);border-radius:10px;padding:16px;margin:12px 0;text-decoration:none;color:#111}"
           "@media (prefers-color-scheme:dark){body{background:#111;color:#eee}a.s{background:#1b1b1b;border-color:#333;color:#eee}}</style><main>",
           "<h1>Storefronts (staging)</h1><p>Pre-launch test environment. Payments use the PayFast sandbox.</p>"]
    for b in built:
        idx.append(f"<a class=s style='--c:{b['accent']}' href='/{b['path']}/'><strong>{html.escape(b['name'])}</strong> — {html.escape(b['tagline'])}<br><small>{b['products']} products</small></a>")
    idx.append("<p><a href='/dashboard/'>Owner dashboard</a></p></main>")
    open(os.path.join(SITE, "index.html"), "w").write("\n".join(idx))
    dash_t = env.get_template("dashboard.html")
    os.makedirs(os.path.join(SITE, "dashboard"), exist_ok=True)
    catalogue_public = [{k: p[k] for k in ("id", "store", "slug", "name", "category", "price_zar", "price_usd", "formats")} |
                        {"valid": p["validation"].get("ok", False), "errors": p["validation"].get("errors", [])[:3]} for p in cat]
    listings = json.load(open(os.path.join(ROOT, "catalogue", "listings.json"))) if os.path.exists(os.path.join(ROOT, "catalogue", "listings.json")) else []
    open(os.path.join(SITE, "dashboard", "index.html"), "w").write(dash_t.render(
        api=cfg["api_base"], stores=json.dumps(built), catalogue=json.dumps(catalogue_public), listings=json.dumps(listings)))
    open(os.path.join(SITE, "robots.txt"), "w").write("User-agent: *\nDisallow: /\n" if staging else
                                                      "User-agent: *\nAllow: /\nDisallow: /dashboard/\nSitemap: " + cfg["site_base"] + "/sitemap.xml\n")
    if not staging:
        urls = [f"{cfg['site_base']}/{st['path']}/p/{p['slug']}.html" for st in cfg["stores"] for p in cat if p["store"] == st["id"]]
        open(os.path.join(SITE, "sitemap.xml"), "w").write('<?xml version="1.0" encoding="UTF-8"?><urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">' +
                                                          "".join(f"<url><loc>{u}</loc></url>" for u in urls) + "</urlset>")
    csp = ("default-src 'self'; img-src 'self' data:; style-src 'self' 'unsafe-inline'; script-src 'self' 'unsafe-inline'; "
           f"connect-src 'self' {cfg['api_base'].split('/functions')[0]}; form-action 'self' https://sandbox.payfast.co.za https://www.payfast.co.za; "
           "frame-ancestors 'none'; base-uri 'self'")
    redirects = [{"source": f"/{old}/:rest*", "destination": f"/{st['path']}/:rest*", "permanent": True}
                 for st in cfg["stores"] for old in st.get("former_paths", [])]
    if "vercel.app" not in cfg["site_base"]:  # the Vercel copy is retired: send every request to the live host
        redirects = [{"source": "/:path*", "destination": cfg["site_base"] + "/:path*", "permanent": True}]
    json.dump({"cleanUrls": False, "trailingSlash": False, "redirects": redirects,
               "headers": [{"source": "/(.*)", "headers": [
                   {"key": "Content-Security-Policy", "value": csp}, {"key": "X-Content-Type-Options", "value": "nosniff"},
                   {"key": "Referrer-Policy", "value": "strict-origin-when-cross-origin"}, {"key": "X-Frame-Options", "value": "DENY"},
                   {"key": "Permissions-Policy", "value": "camera=(), microphone=(), geolocation=()"}]},
                   {"source": "/assets/p/(.*)", "headers": [{"key": "Cache-Control", "value": "public, max-age=604800"}]}]},
              open(os.path.join(SITE, "vercel.json"), "w"), indent=1)
    # Cloudflare Pages equivalents of vercel.json (same headers and redirects), so the site can move hosts unchanged
    open(os.path.join(SITE, "_headers"), "w").write(
        "/*\n" + "".join(f"  {k}: {v}\n" for k, v in [
            ("Content-Security-Policy", csp), ("X-Content-Type-Options", "nosniff"), ("Referrer-Policy", "strict-origin-when-cross-origin"),
            ("X-Frame-Options", "DENY"), ("Permissions-Policy", "camera=(), microphone=(), geolocation=()")]) +
        "/assets/p/*\n  Cache-Control: public, max-age=604800\n")
    open(os.path.join(SITE, "_redirects"), "w").write(
        "".join(f"/{old}/* /{st['path']}/:splat 301\n" for st in cfg["stores"] for old in st.get("former_paths", [])))
    print(f"built {pages} store pages for {len(built)} stores:", ", ".join(f"{b['name']} ({b['products']})" for b in built))


if __name__ == "__main__":
    main()
