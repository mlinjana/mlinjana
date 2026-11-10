"""Build every storefront in config/stores.json, the network index and the owner dashboard from catalogue/products.json.

Deterministic: same catalogue + config → same site. No AI calls.
Usage: python3 engine/build_sites.py
"""
import collections, json, os, shutil, html, re
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
<p>Links last 7 days and 5 downloads. If yours has expired, use the <a href="/help/contact">contact form</a> with your order number and we'll send a new one.</p>
<p class="muted small">This policy does not limit any rights you have under the law of your country, including the South African Consumer Protection Act and Electronic Communications and Transactions Act where they apply.</p>"""),
        "privacy": ("Privacy", f"""
<p>We collect as little personal information as possible.</p>
<h2>What we collect</h2>
<ul><li><strong>Orders:</strong> your email address, the product, amount, date and payment status. We need these to deliver your files and keep tax records.</li>
<li><strong>Payments:</strong> handled entirely by PayFast. We never see or store your card or bank details. PayFast's own privacy policy applies to the payment step.</li>
<li><strong>Messages:</strong> what you send through the contact form.</li>
<li><strong>Visit statistics:</strong> page path, product viewed, and the website that referred you. We store no cookies and no IP addresses for this, and use no advertising trackers.</li>
<li><strong>Site speed and visits (Cloudflare Web Analytics):</strong> Cloudflare hosts this site and counts page views and page loading times for us. Cloudflare states that this service doesn't use cookies or track you across other websites. Like any web host, Cloudflare handles technical details of each request, such as your IP address, to deliver and protect the site.</li></ul>
<h2>How we use it</h2>
<p>Only to deliver your order, provide support, keep business records and understand which products are useful. We don't sell or share your information for marketing, and we don't send newsletters unless you ask to join one.</p>
<h2>Where it's stored</h2>
<p>Order data is stored with our hosting provider (Supabase, EU data centre) with access restricted to the store owner.</p>
<h2>Your rights</h2>
<p>You can ask us what information we hold about you, ask us to correct it, or ask us to delete it (we may need to keep order records for tax law). Use the <a href="/help/contact">contact form</a>. South African customers may also contact the Information Regulator.</p>
<p class="muted small">Responsible party: {html.escape(legal['operator'])}. Address: {html.escape(legal['address'])}.</p>"""),
        "terms": ("Terms of sale", f"""
<p>These terms apply when you buy from {n}.</p>
<h2>Seller</h2>
<p>{n} is a trading name of {html.escape(legal['operator'])}, {html.escape(legal['country'])}. Registration: {html.escape(legal['registration'])}. Address: {html.escape(legal['address'])}. Contact: via the <a href="/help/contact">contact form</a>.</p>
<h2>Products and prices</h2>
<p>All products are digital files described on their product pages, including format and compatibility. Prices are in South African rand (ZAR) and include any applicable taxes we're required to charge. Your bank sets the exchange rate for non-ZAR cards.</p>
<h2>Payment and delivery</h2>
<p>Payment is processed by PayFast. An order is only confirmed once PayFast notifies us that payment is complete; your download link then appears on the confirmation page.</p>
<h2>Licence</h2>
<p>Your purchase gives you a licence to use the files, not ownership of the copyright. See the <a href="/help/licence">licence</a>.</p>
<h2>Liability</h2>
<p>Templates and calculators are tools. Check results before relying on them; nothing we sell is legal, tax or financial advice. To the extent the law allows, our liability is limited to the price you paid.</p>
<p class="muted small">Last updated 28 October 2026.</p>"""),
        "licence": ("Licence", f"""
<p>Every product comes with a licence to use the files, not ownership of the copyright. Choose the licence that fits how you'll use it when you add the product to your basket. Your receipt shows which licence you bought: keep it as proof.</p>
<table class="lic-table"><thead><tr><th scope="col">Licence</th><th scope="col">Who can use it</th><th scope="col">Price</th></tr></thead><tbody>
<tr><th scope="row">Standard</th><td>You, your household and one business you own or work for</td><td>The listed price</td></tr>
<tr><th scope="row">Team</th><td>Up to 10 people in one organisation (one company, school, church or non-profit)</td><td>2.5 times the listed price</td></tr>
<tr><th scope="row">Commercial or enterprise</th><td>More than 10 people, several organisations, or the files inside products you sell</td><td>By quote: <a href="/help/contact?topic=licence">ask us</a></td></tr>
</tbody></table>
<h2>With every licence you may</h2><ul><li>Use the product for the people your licence covers, including to serve your own customers (for example, sending invoices made with an invoice template).</li><li>Print it as often as you need for that use and edit it for yourselves.</li></ul>
<h2>With a Team licence you may also</h2><ul><li>Keep the files on your organisation's shared drive, as long as only the people the licence covers (up to 10) can open them.</li></ul>
<h2>You may not</h2><ul><li>Resell, share, give away or upload the files, original or edited, where people outside your licence can download them.</li><li>Sell printed copies or include the files in a product you sell, unless we agreed a commercial licence with you in writing.</li><li>Claim the design or content as your own.</li></ul>
<p>Not sure which licence you need? <a href="/help/contact?topic=licence">Ask us</a> before using a product that way.</p>"""),
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


def about_page(legal, n_shops, n_products, depts):
    e = html.escape
    return f"""
<p><strong>Mlinjana Studios</strong> is the online shop of {e(legal['operator'])}, a registered South African company
(registration {e(legal['registration'].split(' ')[0])}), at {e(legal['address'])}.</p>
<p>We make practical digital tools: printable planners, spreadsheets and document templates, organised into
three areas: {", ".join(e(d['name']) for d in depts[:-1])} and {e(depts[-1]['name'])}. Today that's {n_products} products,
all made, sold and supported by us.</p>
<h2>How we make and check our products</h2>
<ul><li>Every product is built from the ground up for its job, not resold from somewhere else.</li>
<li>Spreadsheets are recalculated and checked for formula errors before release.</li>
<li>Printables come in A4 and US Letter; Word templates are checked in Word-compatible software.</li>
<li>Each listing shows the real pages inside, the file types and what it works with.</li></ul>
<h2>Our promises</h2>
<ul><li>No fake reviews, countdown timers or made-up discounts. Bundle savings are calculated against the real prices of the items inside.</li>
<li>Secure payment on PayFast's page: we never see or store your card details.</li>
<li>If a file doesn't work as described, contact us within 14 days and we'll fix it or refund you.</li>
<li>We collect as little personal information as possible. See our <a href="/help/privacy">privacy notice</a>.</li></ul>
<h2>Get in touch</h2>
<p>Use the <a href="/help/contact">contact form</a>. Quote your order number if your message is about an order.</p>"""


def ld(obj):
    """Serialise structured data for a <script type="application/ld+json"> block (no "</" can close the tag)."""
    return json.dumps(obj, ensure_ascii=False).replace("</", "<\\/")


def slugify(text):
    return re.sub(r"[^a-z0-9]+", "-", text.lower().replace("&", " ")).strip("-")


def jsonld(p, store, url, trail, site_base):
    """Product + BreadcrumbList for a product page. Only facts we hold: no ratings or reviews.
    trail: [(name, absolute url), ...] from Home to the product's category; the product is appended."""
    crumbs = list(trail) + [(p["name"], url)]
    return ld({"@context": "https://schema.org", "@graph": [
        {"@type": "Product", "name": p["name"], "description": p["summary"], "sku": p["id"],
         "image": f"{site_base}/{p['images']['cover']}", "category": p["category"],
         "brand": {"@type": "Brand", "name": store["name"]},
         "offers": {"@type": "Offer", "price": f"{p['price_zar']:.2f}", "priceCurrency": "ZAR",
                    "availability": "https://schema.org/InStock", "url": url,
                    "seller": {"@type": "Organization", "name": store["name"]}}},
        {"@type": "BreadcrumbList", "itemListElement": [
            {"@type": "ListItem", "position": i + 1, "name": n, "item": u} for i, (n, u) in enumerate(crumbs)]}]})


def site_jsonld(site_base, legal):
    """Organization + WebSite (with the site search) for the home page."""
    return ld({"@context": "https://schema.org", "@graph": [
        {"@type": "Organization", "@id": site_base + "/#org", "name": MARKET["name"], "url": site_base + "/",
         "logo": site_base + "/assets/brand/icon-512.png", "legalName": legal["operator"],
         "description": MARKET["tagline"]},
        {"@type": "WebSite", "@id": site_base + "/#website", "name": MARKET["name"], "url": site_base + "/",
         "publisher": {"@id": site_base + "/#org"},
         "potentialAction": {"@type": "SearchAction",
                             "target": {"@type": "EntryPoint", "urlTemplate": site_base + "/search?q={search_term_string}"},
                             "query-input": "required name=search_term_string"}}]})


def crumbs_jsonld(site_base, trail):
    """BreadcrumbList for category pages: trail is [(name, absolute url), ...]."""
    return ld({"@context": "https://schema.org", "@type": "BreadcrumbList", "itemListElement": [
        {"@type": "ListItem", "position": i + 1, "name": n, "item": u} for i, (n, u) in enumerate(trail)]})


MARKET = {"name": "Mlinjana Studios",
          "tagline": "Printable planners, templates and spreadsheets for the jobs of everyday life. Made, sold and supported in South Africa."}
FMT_ORDER = ["PDF", "XLSX", "DOCX"]


def rotate(items, key, n):
    """A deterministic, page-specific selection (so neighbouring pages don't all show the same picks)."""
    if not items:
        return []
    k = sum(map(ord, key)) % len(items)
    return (items[k:] + items[:k])[:n]


def main():
    cfg = json.load(open(os.path.join(ROOT, "config", "stores.json")))
    cat = json.load(open(os.path.join(ROOT, "catalogue", "products.json")))["products"]
    dcfg = json.load(open(os.path.join(ROOT, "config", "departments.json")))
    depts, colls = dcfg["departments"], dcfg["collections"]
    tcfg = json.load(open(os.path.join(ROOT, "config", "taxonomy.json")))  # 2.0 divisions: Business, Life, Education
    staging = cfg["mode"] != "live"
    dept_of = {sid: d for d in depts for sid in d["stores"]}
    missing = [st["id"] for st in cfg["stores"] if st["id"] not in dept_of]
    assert not missing, f"stores without a department in config/departments.json: {missing}"
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
    # brand: logo (brand/make_logo.py, concept D), favicons, social card, web app manifest
    bdst = os.path.join(SITE, "assets", "brand")
    shutil.rmtree(bdst, ignore_errors=True)
    shutil.copytree(os.path.join(ROOT, "engine", "static", "brand"), bdst)
    shutil.copy(os.path.join(bdst, "favicon.ico"), os.path.join(SITE, "favicon.ico"))
    json.dump({"name": "Mlinjana Studios", "short_name": "Mlinjana", "start_url": "/", "display": "browser",
               "background_color": "#f1f3f6", "theme_color": "#0b6b57",
               "icons": [{"src": "/assets/brand/icon-192.png", "sizes": "192x192", "type": "image/png"},
                         {"src": "/assets/brand/icon-512.png", "sizes": "512x512", "type": "image/png"},
                         {"src": "/assets/brand/icon.svg", "sizes": "any", "type": "image/svg+xml"}]},
              open(os.path.join(SITE, "site.webmanifest"), "w"), indent=1)
    by_slug = {p["slug"]: p for p in cat}

    # ---- pass 1: prepare every store and product (pages link across stores, so all data comes first) ----
    shops, prods_of = {}, {}
    for st in cfg["stores"]:
        prods = [p for p in cat if p["store"] == st["id"] and p["validation"].get("ok") and p["images"].get("cover")]
        for p in prods:
            n = p["file"]["bytes"] or 0
            p["file_mb"] = f"{n / 1e6:.1f} MB" if n >= 1e6 else f"{max(1, round(n / 1e3))} KB"
            p["bundle_items"] = [by_slug[s] for s in p.get("bundle_of", [])]
            p["bundle_sum"] = sum(b["price_zar"] for b in p["bundle_items"])
            p["fmt_keys"] = [k for k in FMT_ORDER if any(f.split(" ")[0] == k for f in p["formats"])]
            p["free"] = bool(p.get("free"))
            p["price_team"] = (p["price_zar"] * 5 + 1) // 2  # Team licence: 2.5x, nearest whole rand (same rule as store-api)
            if p["free"]:
                p["free_url"] = f"/free/{p['slug']}.zip"
        for p in prods:
            if p["bundle_items"] and p["bundle_sum"]:
                p["saving_pct"] = round(100 * (1 - p["price_zar"] / p["bundle_sum"]))
        singles = [p for p in prods if not p["bundle_items"]]
        hero = []
        for p in singles:  # covers from different categories, for the shop strip and department circles
            if p["category"] not in [h["category"] for h in hero]:
                hero.append(p)
            if len(hero) == 3:
                break
        font, motif = STYLE.get(st["id"], ("outfit", "soft"))
        prods_of[st["id"]] = prods
        shops[st["id"]] = {**st, "display": font, "motif": motif_svg(st), "n_products": len(prods), "products": len(prods),
                           "accent_btn": BTN.get(st["id"]) or btn_colour(st["accent"]), "hero": hero,
                           "covers": [h["images"]["cover"] for h in hero], "url": f"{cfg['site_base']}/{st['path']}",
                           "dept": dept_of[st["id"]], "coll": colls[st["id"]]}
    allp = [p for st in cfg["stores"] for p in prods_of[st["id"]]]
    total = len(allp)
    for d in depts:
        d["cover"] = shops[d["stores"][0]]["covers"][0]
        d["count"] = sum(len(prods_of[s]) for s in d["stores"])
        d["shop_list"] = [{"name": shops[s]["coll"], "path": shops[s]["path"], "count": shops[s]["n_products"]} for s in d["stores"]]
    # ---- 2.0 divisions and categories (config/taxonomy.json) ----
    unmapped = sorted({(p["store"], p["category"]) for p in allp if p["category"] not in tcfg["map"].get(p["store"], {})})
    assert not unmapped, f"products without a 2.0 category in config/taxonomy.json: {unmapped}"
    for p in allp:
        p["division"], p["cat2"] = tcfg["map"][p["store"]][p["category"]]
        p["cat2_slug"] = slugify(p["cat2"])
    divisions = []
    for dv in tcfg["divisions"]:
        items = [p for p in allp if p["division"] == dv["slug"]]
        by_cat = {}
        for p in items:
            by_cat.setdefault(p["cat2"], []).append(p)
        order = sorted((n for n in by_cat if n != "Bundles"), key=lambda n: -len(by_cat[n])) + (["Bundles"] if "Bundles" in by_cat else [])
        cats = []
        for n in order:
            singles = [p for p in by_cat[n] if not p["bundle_items"]] or by_cat[n]
            cats.append({"name": n, "slug": slugify(n), "count": len(by_cat[n]), "href": f"/{dv['slug']}/{slugify(n)}/",
                         "cover": singles[0]["images"]["cover"], "items": by_cat[n]})
        divisions.append({**dv, "href": f"/{dv['slug']}/", "count": len(items), "categories": cats, "items": items})
    div_by = {d["slug"]: d for d in divisions}
    for p in allp:
        p["cat2_href"] = f"/{p['division']}/{p['cat2_slug']}/"
    for sid, shop in shops.items():
        shop["division"] = div_by[collections.Counter(p["division"] for p in prods_of[sid]).most_common(1)[0][0]]
    import hashlib
    asset_v = hashlib.sha256(b"".join(open(os.path.join(ROOT, "engine", "static", f), "rb").read() for f in ("site.css", "site.js"))).hexdigest()[:10]
    common = dict(legal=cfg["legal"], api=cfg["api_base"], staging=staging, checkout_paused=cfg.get("checkout") == "paused", depts=depts, divisions=divisions, shops=shops, asset_v=asset_v,
                  site_base=cfg["site_base"], market={**MARKET, "total": total})

    def cat_counts(items, order=None):
        counts = {}
        for p in items:
            counts[p["category"]] = counts.get(p["category"], 0) + 1
        keys = [c for c in (order or []) if c in counts] + [c for c in counts if c not in (order or []) and c != "Bundles"]
        if "Bundles" in counts and "Bundles" not in keys:
            keys.append("Bundles")
        return [(c, counts[c]) for c in keys]

    # ---- pass 2: shop, product and policy pages ----
    pages = 0
    for st in cfg["stores"]:
        shop, prods = shops[st["id"]], prods_of[st["id"]]
        base_url = shop["url"]
        bundle = next((p for p in prods if p["bundle_items"]), None)
        fmts = sorted({f.split(" ")[0] for p in prods for f in p["formats"]})
        ctx = dict(common, store=shop, dept=shop["dept"], bundle=bundle, formats_all=fmts, base=f"/{st['path']}", root="/")
        out = os.path.join(SITE, st["path"])
        os.makedirs(os.path.join(out, "p"), exist_ok=True)
        sb = cfg["site_base"]
        sdiv = shop["division"]
        open(os.path.join(out, "index.html"), "w").write(env.get_template("store_index.html").render(
            products=prods, categories=cat_counts(prods, st["categories"]), canonical=base_url + "/",
            jsonld=crumbs_jsonld(sb, [("Home", sb + "/"), (sdiv["name"], sb + sdiv["href"]), (shop["coll"], base_url + "/")]), **ctx))
        pages += 1
        for p in prods:
            others = [r for r in prods if r["id"] != p["id"]]
            more = [r for r in others if r["category"] == p["category"]][:4]
            more += rotate([r for r in others if r not in more], p["id"], 8 - len(more))
            pdiv = div_by[p["division"]]
            alike_pool = [q for q in allp if q["cat2"] == p["cat2"] and q["division"] == p["division"] and q["store"] != st["id"]]
            if len(alike_pool) < 4:
                alike_pool = [q for q in pdiv["items"] if q["store"] != st["id"]]
            alike = rotate(alike_pool, p["id"], 8)
            trail = [("Home", sb + "/"), (pdiv["name"], sb + pdiv["href"]), (p["cat2"], sb + p["cat2_href"])]
            open(os.path.join(out, "p", p["slug"] + ".html"), "w").write(env.get_template("product.html").render(
                p=p, more=more, alike=alike, division=pdiv, jsonld=jsonld(p, {"name": MARKET["name"]}, f"{base_url}/p/{p['slug']}", trail, sb),
                canonical=f"{base_url}/p/{p['slug']}", **ctx))
            pages += 1
        for key, (title, body) in policies({"name": MARKET["name"]}, cfg["legal"]).items():
            if key != "thanks":  # one copy of each policy lives in /help/; the shop path 301s there (see _redirects)
                stale = os.path.join(out, key + ".html")
                if os.path.exists(stale): os.remove(stale)
                continue
            open(os.path.join(out, key + ".html"), "w").write(env.get_template("page.html").render(
                title=title, body=body, canonical=f"{cfg['site_base']}/" + ("thanks" if key == "thanks" else f"help/{key}"), **ctx))
            pages += 1

    # ---- marketplace pages: home, divisions, categories, legacy departments, search, favourites, help ----
    def mix_cats(cats, n):
        """Round-robin across categories (bundles last), so a row shows the range of a division."""
        pools = [[p for p in c["items"] if not p["bundle_items"]] for c in cats if c["name"] != "Bundles"]
        out = []
        for k in range(max(map(len, pools)) if pools else 0):
            out += [pl[k] for pl in pools if k < len(pl)]
        return out[:n]
    picks = mix_cats([c for d in divisions for c in d["categories"][:4]], 12)
    bundles = sorted([p for p in allp if p.get("saving_pct")], key=lambda p: -p["saving_pct"])
    under50 = [p for p in allp if p["price_zar"] < 50]
    under50_pick, seen = [], set()
    for p in under50:  # one per product line, so the row shows the range
        if p["store"] not in seen:
            under50_pick.append(p); seen.add(p["store"])
    hero_covers = [d["categories"][0]["cover"] for d in divisions]  # one real product per division, no text baked in
    div_rows = [{"title": f"Popular in {d['name']}", "name": d["name"], "href": d["href"], "products": mix_cats(d["categories"], 12)}
                for d in divisions]
    open(os.path.join(SITE, "index.html"), "w").write(env.get_template("home.html").render(
        store=None, picks=picks, bundles=bundles[:12], best_saving=bundles[0]["saving_pct"] if bundles else 0,
        under50=under50_pick[:12], under50_total=len(under50), min_price=min(p["price_zar"] for p in allp),
        hero_covers=hero_covers, div_rows=div_rows,
        canonical=cfg["site_base"] + "/", jsonld=site_jsonld(cfg["site_base"], cfg["legal"]), **common))
    # ---- 2.0 division and category pages ----
    sb = cfg["site_base"]
    for d in divisions:
        out = os.path.join(SITE, d["slug"])
        os.makedirs(out, exist_ok=True)
        # rows for the 6 largest categories, 8 products each (every category is still one click away in the tiles above);
        # 12 full rows made the Business page ~220 KB with 115 cards (LCP 2.4 s, TBT 240 ms on 6 Nov)
        rows = [{"title": c["name"], "href": c["href"], "count": c["count"], "products": c["items"][:8]} for c in d["categories"][:6]]
        open(os.path.join(out, "index.html"), "w").write(env.get_template("division.html").render(
            store=None, division=d, category=None, rows=rows, page_div=d["slug"], art=[c["cover"] for c in d["categories"][:3]],
            canonical=f"{sb}{d['href']}",
            jsonld=crumbs_jsonld(sb, [("Home", sb + "/"), (d["name"], sb + d["href"])]), **common))
        pages += 1
        for c in d["categories"]:
            os.makedirs(os.path.join(out, c["slug"]), exist_ok=True)
            lines = sorted({shops[p["store"]]["coll"] for p in c["items"]})
            open(os.path.join(out, c["slug"], "index.html"), "w").write(env.get_template("division.html").render(
                store=None, division=d, category=c, products=c["items"], categories=cat_counts(c["items"]), lines=lines,
                art=[p["images"]["cover"] for p in ([q for q in c["items"] if not q["bundle_items"]] or c["items"])[:2]],
                canonical=f"{sb}{c['href']}",
                jsonld=crumbs_jsonld(sb, [("Home", sb + "/"), (d["name"], sb + d["href"]), (c["name"], sb + c["href"])]), **common))
            pages += 1
    # Retired department pages (/c/<dept>/, 5 Nov design): a 301 to the 2.0 category holding at least 60% of the
    # department's products, else to the division holding most of them (DECISIONS.md #40). Written to _redirects below.
    dept_redirects = []
    for d in depts:
        items = [p for s in d["stores"] for p in prods_of[s]]
        (dv, cname), k = collections.Counter((p["division"], p["cat2"]) for p in items).most_common(1)[0]
        if k / len(items) >= 0.6:
            target = next(c["href"] for c in div_by[dv]["categories"] if c["name"] == cname)
        else:
            target = div_by[collections.Counter(p["division"] for p in items).most_common(1)[0][0]]["href"]
        dept_redirects.append((f"/c/{d['slug']}", target))
    for name in ("search", "favourites"):
        open(os.path.join(SITE, name + ".html"), "w").write(env.get_template(name + ".html").render(
            store=None, canonical=f"{cfg['site_base']}/{name}", **common))
    os.makedirs(os.path.join(SITE, "help"), exist_ok=True)
    pages_global = policies({"name": MARKET["name"]}, cfg["legal"])
    pages_global["about"] = ("About us", about_page(cfg["legal"], len(shops), total, divisions))
    for key, (title, body) in pages_global.items():
        out = os.path.join(SITE, "thanks.html") if key == "thanks" else os.path.join(SITE, "help", key + ".html")
        open(out, "w").write(env.get_template("page.html").render(
            store=None, title=title, body=body, canonical=f"{cfg['site_base']}/" + ("thanks" if key == "thanks" else f"help/{key}"), **common))
    open(os.path.join(SITE, "404.html"), "w").write(env.get_template("page.html").render(
        store=None, noindex=True, title="Page not found", canonical=f"{cfg['site_base']}/", body="""
<p>Sorry, we couldn't find that page. It may have moved, or the link may be mistyped.</p>
<form class="nf-search" action="/search" method="get" role="search"><label for="nf-q">Search all 600 downloads</label>
<div class="nf-row"><input id="nf-q" name="q" type="search" placeholder="Try invoice, budget or lesson plan"><button class="btn btn-dark" type="submit">Search</button></div></form>
<p>Or browse <a href="/business/">Business</a>, <a href="/life/">Life</a> or <a href="/education/">Education</a>, go to the <a href="/">home page</a>, or <a href="/help/contact">contact us</a> if you were looking for an order.</p>""", **common))
    # search index for /search and /favourites (short keys keep it small)
    json.dump({"shops": {s["id"]: {"n": s["coll"], "p": s["path"]} for s in shops.values()},
               "items": [{"i": p["id"], "n": p["name"], "s": p["store"], "u": f"/{shops[p['store']]['path']}/p/{p['slug']}",
                          "img": "/" + p["images"]["cover"], "c": p["category"], "d": shops[p["store"]]["dept"]["slug"],
                          "v": p["division"], "k": p["cat2"],
                          "p": p["price_zar"], "b": p["bundle_sum"] if p.get("saving_pct") else 0, "o": p.get("saving_pct", 0),
                          "f": p["fmt_keys"], "fr": 1 if p["free"] else 0,
                          "t": " ".join([p["name"], p["category"], p["cat2"], p["summary"], " ".join(p["tags"]), shops[p["store"]]["coll"]]).lower()}
                         for p in allp]},
              open(os.path.join(SITE, "assets", "catalogue.json"), "w"), separators=(",", ":"))
    built = [{"id": s["id"], "path": s["path"], "name": s["name"], "url": s["url"], "products": s["products"], "tagline": s["tagline"],
              "accent": s["accent"], "accent2": s["accent2"], "ink": s["ink"], "light": s["light"],
              "cover": s["covers"][0] if s["covers"] else None} for s in shops.values()]
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
        urls = ([cfg["site_base"] + "/"] + [cfg["site_base"] + d["href"] for d in divisions] + [cfg["site_base"] + c["href"] for d in divisions for c in d["categories"]] +
                [s["url"] + "/" for s in shops.values()] +
                [f"{cfg['site_base']}/{shops[p['store']]['path']}/p/{p['slug']}" for p in allp] +
                [f"{cfg['site_base']}/help/{k}" for k in pages_global if k != "thanks"])
        open(os.path.join(SITE, "sitemap.xml"), "w").write('<?xml version="1.0" encoding="UTF-8"?><urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">' +
                                                          "".join(f"<url><loc>{u}</loc></url>" for u in urls) + "</urlset>")
    # Cloudflare Web Analytics (owner decision #39): beacon script from static.cloudflareinsights.com, reports to cloudflareinsights.com
    csp = ("default-src 'self'; img-src 'self' data:; style-src 'self' 'unsafe-inline'; script-src 'self' 'unsafe-inline' https://static.cloudflareinsights.com; "
           f"connect-src 'self' {cfg['api_base'].split('/functions')[0]} https://cloudflareinsights.com; form-action 'self' https://sandbox.payfast.co.za https://www.payfast.co.za; "
           "frame-ancestors 'none'; base-uri 'self'")
    redirects = [{"source": f"/{old}/:rest*", "destination": f"/{st['path']}/:rest*", "permanent": True}
                 for st in cfg["stores"] for old in st.get("former_paths", [])]
    if "vercel.app" not in cfg["site_base"]:  # the Vercel copy is retired: send every request to the live host
        # a regex catch-all: ":path*" missed "/" and folder paths ending in "/", which Vercel still served
        redirects = [{"source": "/(.*)", "destination": cfg["site_base"] + "/$1", "permanent": True}]
    retired = "vercel.app" not in cfg["site_base"]
    json.dump({"cleanUrls": False, **({} if retired else {"trailingSlash": False}), "redirects": redirects,
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
        "  Strict-Transport-Security: max-age=31536000\n"
        "/assets/p/*\n  Cache-Control: public, max-age=604800\n"
        # site.css and site.js are requested as ?v=<content hash>, so a new build always gets a new URL
        "/assets/site.css\n  Cache-Control: public, max-age=31536000, immutable\n"
        "/assets/site.js\n  Cache-Control: public, max-age=31536000, immutable\n"
        "/assets/fonts/*\n  Cache-Control: public, max-age=31536000, immutable\n"
        "/assets/brand/*\n  Cache-Control: public, max-age=604800\n")
    open(os.path.join(SITE, "_redirects"), "w").write(
        "".join(f"/{old}/* /{st['path']}/:splat 301\n" for st in cfg["stores"] for old in st.get("former_paths", [])) +
        "".join(f"{src}/ {dst} 301\n{src} {dst} 301\n" for src, dst in dept_redirects) +
        "".join(f"/{st['path']}/{k} /help/{k} 301\n" for st in cfg["stores"] for k in pages_global if k not in ("thanks", "about")))
    print(f"built {pages} shop pages for {len(built)} shops in {len(divisions)} divisions ({total} products):", ", ".join(f"{b['name']} ({b['products']})" for b in built))


if __name__ == "__main__":
    main()
