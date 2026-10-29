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

# Per-store personality: display typeface + backdrop motif (deterministic, generated from the store's own colours).
STYLE = {k: (v["display"], v["motif"]) for k, v in json.load(open(os.path.join(ROOT, "config", "style.json"))).items()}


def motif_svg(store):
    """A layered, slowly drifting backdrop for the hero, unique per store (seeded by its id)."""
    import random
    rnd = random.Random(store["id"])
    kind = STYLE.get(store["id"], ("outfit", "soft"))[1]
    a, b = store["accent"], store["accent2"]
    out = []
    def g(inner, i):
        return f'<g class="fl" style="--d:{rnd.uniform(0, 6):.1f}s;--t:{rnd.uniform(14, 26):.0f}s;--x:{rnd.uniform(-30, 30):.0f}px;--y:{rnd.uniform(-24, 24):.0f}px">{inner}</g>'
    if kind == "soft":
        for i in range(6):
            cx, cy, r = rnd.uniform(0, 1200), rnd.uniform(0, 700), rnd.uniform(90, 260)
            out.append(g(f'<circle cx="{cx:.0f}" cy="{cy:.0f}" r="{r:.0f}" fill="{(a, b)[i % 2]}" opacity="{rnd.uniform(.10, .22):.2f}"/>', i))
    elif kind == "grid":
        out.append('<g opacity=".14">' + "".join(f'<path d="M{x} 0V700" stroke="{a}" stroke-width="1"/>' for x in range(0, 1201, 60)) +
                   "".join(f'<path d="M0 {y}H1200" stroke="{a}" stroke-width="1"/>' for y in range(0, 701, 60)) + '</g>')
        for i in range(5):
            x, y, s = rnd.randrange(0, 1140, 60), rnd.randrange(0, 640, 60), rnd.choice([60, 120, 180])
            out.append(g(f'<rect x="{x}" y="{y}" width="{s}" height="{s}" rx="10" fill="{(a, b)[i % 2]}" opacity="{rnd.uniform(.12, .24):.2f}"/>', i))
    elif kind == "bars":
        for i in range(9):
            x, h = 80 + i * 125, rnd.uniform(120, 520)
            out.append(g(f'<rect x="{x:.0f}" y="{700 - h:.0f}" width="70" height="{h:.0f}" rx="12" fill="{(a, b)[i % 2]}" opacity="{rnd.uniform(.10, .2):.2f}"/>', i))
    elif kind == "confetti":
        for i in range(26):
            x, y, s, rot = rnd.uniform(0, 1200), rnd.uniform(0, 700), rnd.uniform(10, 34), rnd.uniform(0, 90)
            shape = rnd.choice(["rect", "circle", "tri"])
            col = (a, b)[i % 2]
            if shape == "rect":
                el = f'<rect x="{x:.0f}" y="{y:.0f}" width="{s:.0f}" height="{s * .45:.0f}" rx="3" fill="{col}" transform="rotate({rot:.0f} {x:.0f} {y:.0f})"/>'
            elif shape == "circle":
                el = f'<circle cx="{x:.0f}" cy="{y:.0f}" r="{s / 2:.0f}" fill="{col}"/>'
            else:
                el = f'<path d="M{x:.0f} {y:.0f}l{s:.0f} 0l{-s / 2:.0f} {-s:.0f}z" fill="{col}"/>'
            out.append(g(f'<g opacity="{rnd.uniform(.22, .45):.2f}">{el}</g>', i))
    elif kind == "dots":
        out.append('<g opacity=".18">' + "".join(f'<circle cx="{x}" cy="{y}" r="2.4" fill="{a}"/>' for x in range(20, 1200, 40) for y in range(20, 700, 40)) + '</g>')
        for i in range(4):
            out.append(g(f'<circle cx="{rnd.uniform(0, 1200):.0f}" cy="{rnd.uniform(0, 700):.0f}" r="{rnd.uniform(70, 180):.0f}" fill="{(b, a)[i % 2]}" opacity=".16"/>', i))
    elif kind == "arcs":
        for i in range(7):
            cx, cy, r = rnd.uniform(0, 1200), rnd.uniform(200, 900), rnd.uniform(140, 420)
            out.append(g(f'<circle cx="{cx:.0f}" cy="{cy:.0f}" r="{r:.0f}" fill="none" stroke="{(a, b)[i % 2]}" stroke-width="{rnd.uniform(10, 34):.0f}" opacity="{rnd.uniform(.12, .24):.2f}"/>', i))
    else:  # stripes
        for i in range(8):
            y = rnd.uniform(-100, 700)
            out.append(g(f'<rect x="-200" y="{y:.0f}" width="1700" height="{rnd.uniform(18, 60):.0f}" fill="{(a, b)[i % 2]}" opacity="{rnd.uniform(.10, .2):.2f}" transform="rotate(-14 600 350)"/>', i))
    return ('<svg class="motif" viewBox="0 0 1200 700" preserveAspectRatio="xMidYMid slice" aria-hidden="true" focusable="false">' + "".join(out) + "</svg>")


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
<p>{n} is a trading name of {html.escape(legal['operator'])}, {html.escape(legal['country'])}. Registration: {html.escape(legal['registration'])}. Address: {html.escape(legal['address'])}. Contact: via the <a href="contact.html">contact form</a>.</p>
<h2>Products and prices</h2>
<p>All products are digital files described on their product pages, including format and compatibility. Prices are in South African rand (ZAR) and include any applicable taxes we're required to charge. Your bank sets the exchange rate for non-ZAR cards.</p>
<h2>Payment and delivery</h2>
<p>Payment is processed by PayFast. An order is only confirmed once PayFast notifies us that payment is complete; your download link then appears on the confirmation page.</p>
<h2>Licence</h2>
<p>Your purchase gives you a licence to use the files, not ownership of the copyright. See the <a href="licence.html">licence</a>.</p>
<h2>Liability</h2>
<p>Templates and calculators are tools. Check results before relying on them; nothing we sell is legal, tax or financial advice. To the extent the law allows, our liability is limited to the price you paid.</p>
<p class="muted small">Last updated 28 October 2026.</p>"""),
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
    fdst = os.path.join(SITE, "assets", "fonts")
    shutil.rmtree(fdst, ignore_errors=True)
    shutil.copytree(os.path.join(ROOT, "engine", "static", "fonts"), fdst)
    by_slug = {p["slug"]: p for p in cat}
    built, pages = [], 0
    for st in cfg["stores"]:
        st = dict(st)
        base_url = f"{cfg['site_base']}/{st['path']}"
        prods = [p for p in cat if p["store"] == st["id"] and p["validation"].get("ok") and p["images"].get("cover")]
        for p in prods:
            n = p["file"]["bytes"] or 0
            p["file_mb"] = f"{n / 1e6:.1f} MB" if n >= 1e6 else f"{max(1, round(n / 1e3))} KB"
            p["bundle_items"] = [by_slug[s] for s in p.get("bundle_of", [])]
            p["bundle_sum"] = sum(b["price_zar"] for b in p["bundle_items"])
        for p in prods:
            if p["bundle_items"] and p["bundle_sum"]:
                p["saving_pct"] = round(100 * (1 - p["price_zar"] / p["bundle_sum"]))
        singles = [p for p in prods if not p["bundle_items"]]
        hero = []
        for p in singles:  # three covers from different categories for the 3D fan
            if p["category"] not in [h["category"] for h in hero]:
                hero.append(p)
            if len(hero) == 3:
                break
        font, motif = STYLE.get(st["id"], ("outfit", "soft"))
        fmts = sorted({f.split(" ")[0] for p in prods for f in p["formats"]})
        bundle = next((p for p in prods if p["bundle_items"]), None)
        ctx = dict(legal=cfg["legal"], hero=hero, bundle=bundle, formats_all=fmts,
                   store={**st, "accent_btn": BTN.get(st["id"]) or btn_colour(st["accent"]), "display": font, "motif": motif_svg(st),
                          "n_products": len(prods)}, api=cfg["api_base"], staging=staging, base=f"/{st['path']}", root="/")
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
        built.append({"id": st["id"], "path": st["path"], "name": st["name"], "url": base_url, "products": len(prods), "tagline": st["tagline"],
                      "accent": st["accent"], "accent2": st["accent2"], "ink": st["ink"], "light": st["light"],
                      "cover": (hero[0]["images"]["cover"] if hero else None)})
    # network home: a showcase of every studio
    open(os.path.join(SITE, "index.html"), "w").write(env.get_template("network.html").render(
        stores=built, total=sum(b["products"] for b in built), staging=staging, legal=cfg["legal"], api=cfg["api_base"]))
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
