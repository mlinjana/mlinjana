"""Check every internal link in the built site the way Cloudflare Workers static assets serves it.

Cloudflare's default html_handling ("auto-trailing-slash"):
  /x        -> serves x.html (200)
  /folder/  -> serves folder/index.html (200)
  /x.html   -> 307 to /x            (works, but costs a redirect: reported as a warning)
  /folder   -> 307 to /folder/      (reported as a warning)
Run after build_sites.py:  python3 engine/check_links.py   (exit code 1 if any link is broken)
"""
import json
import os
import re
import sys
from html.parser import HTMLParser
from urllib.parse import urlsplit, unquote

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SITE = os.path.join(ROOT, "site")
SITE_BASE = json.load(open(os.path.join(ROOT, "config", "stores.json")))["site_base"].rstrip("/") \
    if os.path.exists(os.path.join(ROOT, "config", "stores.json")) else "https://mlinjanastudios.com"


def resolve(path):
    """Return (status, file) for a site path: 200 served, 307 redirected, 404 missing."""
    path = unquote(path)
    rel = path.lstrip("/")
    full = os.path.join(SITE, rel)
    if path.endswith("/"):
        return (200, full + "index.html") if os.path.isfile(full + "index.html") else (404, None)
    if rel.endswith(".html"):
        return (307, full) if os.path.isfile(full) else (404, None)
    if os.path.isfile(full):          # an asset such as /assets/site.css or /favicon.ico
        return 200, full
    if os.path.isfile(full + ".html"):
        return 200, full + ".html"
    if os.path.isfile(os.path.join(full, "index.html")):
        return 307, os.path.join(full, "index.html")
    return 404, None


class Links(HTMLParser):
    def __init__(self):
        super().__init__()
        self.found = []

    def handle_starttag(self, tag, attrs):
        a = dict(attrs)
        for key in ("href", "src", "action"):
            if a.get(key):
                self.found.append((tag, key, a[key], a.get("rel")))


def internal(url):
    if url.startswith(SITE_BASE):
        url = url[len(SITE_BASE):] or "/"
    if url.startswith(("http:", "https:", "mailto:", "tel:", "data:", "#", "javascript:", "//")) or "{{" in url or "${" in url:
        return None
    return urlsplit(url).path or None


def main():
    broken, redirects, checked = [], [], 0
    pages = [os.path.join(d, f) for d, _, fs in os.walk(SITE) for f in fs if f.endswith(".html")]
    for page in pages:
        if "/dashboard/" in page:
            continue
        rel_dir = os.path.relpath(os.path.dirname(page), SITE)
        here = "/" if rel_dir == "." else "/" + rel_dir + "/"
        parser = Links()
        parser.feed(open(page, encoding="utf-8").read())
        for tag, key, url, rel in parser.found:
            path = internal(url)
            if path is None:
                continue
            if not path.startswith("/"):
                path = re.sub(r"/+", "/", here + path)
            status, _ = resolve(path)
            checked += 1
            where = os.path.relpath(page, SITE)
            if status == 404:
                broken.append(f"{where}: {key}={url}")
            elif status == 307 and key in ("href", "action"):
                redirects.append(f"{where}: {'canonical ' if rel == 'canonical' else ''}{url}")
    # catalogue.json product URLs (used by search, favourites and the basket)
    cat = json.load(open(os.path.join(SITE, "assets", "catalogue.json")))
    for it in cat["items"]:
        status, _ = resolve(it["u"])
        checked += 1
        if status == 404:
            broken.append(f"catalogue.json: {it['u']}")
        elif status == 307:
            redirects.append(f"catalogue.json: {it['u']}")
    # sitemap
    sm = os.path.join(SITE, "sitemap.xml")
    if os.path.exists(sm):
        for loc in re.findall(r"<loc>([^<]+)</loc>", open(sm).read()):
            status, _ = resolve(internal(loc) or "/")
            checked += 1
            if status == 404:
                broken.append(f"sitemap.xml: {loc}")
            elif status == 307:
                redirects.append(f"sitemap.xml: {loc}")
    print(f"pages: {len(pages)}  links checked: {checked}  broken: {len(broken)}  redirecting: {len(redirects)}")
    for line in broken[:40]:
        print("  BROKEN  ", line)
    for line in redirects[:20]:
        print("  REDIRECT", line)
    return 1 if broken else 0


if __name__ == "__main__":
    sys.exit(main())
