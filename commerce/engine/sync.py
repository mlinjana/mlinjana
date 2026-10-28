"""Push products, listings and files to the backend (idempotent; skips files whose SHA-256 is unchanged).

Needs COMMERCE_UPLOAD_SECRET in the environment or in commerce/.env (never committed).
Usage: python3 engine/sync.py [--files] [--work done|planned|decision_needed|blocker "text"]
"""
import json, os, sys, urllib.request, hashlib

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CFG = json.load(open(os.path.join(ROOT, "config", "stores.json")))
STATE = os.path.join(ROOT, "build", "uploaded.json")


def secret():
    s = os.environ.get("COMMERCE_UPLOAD_SECRET")
    envf = os.path.join(ROOT, ".env")
    if not s and os.path.exists(envf):
        for line in open(envf):
            if line.startswith("COMMERCE_UPLOAD_SECRET="):
                s = line.split("=", 1)[1].strip()
    if not s:
        sys.exit("COMMERCE_UPLOAD_SECRET not set")
    return s


def call(path, body, ctype="application/json", method="POST"):
    data = body if isinstance(body, bytes) else json.dumps(body).encode()
    req = urllib.request.Request(f"{CFG['api_base']}/ops-api{path}", data=data, method=method,
                                 headers={"Content-Type": ctype, "x-secret": secret()})
    for attempt in range(3):
        try:
            with urllib.request.urlopen(req, timeout=120) as r:
                return json.load(r)
        except urllib.error.HTTPError as e:
            if e.code < 500 or attempt == 2:
                raise RuntimeError(f"{path}: HTTP {e.code} {e.read()[:300]}")
        except urllib.error.URLError:
            if attempt == 2:
                raise


def upload_files(products):
    """Upload changed ZIPs (4 in parallel); each upload is checked against the server-side SHA-256."""
    from concurrent.futures import ThreadPoolExecutor
    import threading
    done = json.load(open(STATE)) if os.path.exists(STATE) else {}
    lock = threading.Lock()
    todo = []
    for p in products:
        if not p["validation"].get("ok"):
            continue
        local = os.path.join(ROOT, "build", "products", p["id"], p["slug"] + ".zip")
        sha = hashlib.sha256(open(local, "rb").read()).hexdigest()
        if done.get(p["file"]["key"]) != sha:
            todo.append((p, local, sha))

    def up(item):
        p, local, sha = item
        r = call(f"/admin/upload?key={p['file']['key']}", open(local, "rb").read(), "application/zip")
        if r.get("sha256") != sha:
            raise RuntimeError(f"upload checksum mismatch for {p['id']}")
        with lock:
            done[p["file"]["key"]] = sha
            json.dump(done, open(STATE, "w"), indent=1)

    with ThreadPoolExecutor(4) as ex:
        list(ex.map(up, todo))
    return len(todo)


def main():
    products = json.load(open(os.path.join(ROOT, "catalogue", "products.json")))["products"]
    if "--work" in sys.argv:
        i = sys.argv.index("--work")
        print(call("/admin/sync", {"work": [{"kind": sys.argv[i + 1], "text": sys.argv[i + 2]}]}))
        return
    uploaded = upload_files(products) if "--files" in sys.argv else 0
    listings_path = os.path.join(ROOT, "catalogue", "listings.json")
    listings = json.load(open(listings_path)) if os.path.exists(listings_path) else []
    status = "staging" if CFG["mode"] != "live" else "live"
    body = {
        "stores": [{"id": s["id"], "name": s["name"], "tagline": s["tagline"], "url": f"{CFG['site_base']}/{s['path']}/", "status": status} for s in CFG["stores"]],
        "products": [{"id": p["id"], "store_id": p["store"], "slug": p["slug"], "title": p["name"], "price_zar_cents": p["price_zar"] * 100,
                      "price_usd_cents": int(round(p["price_usd"] * 100)), "file_key": p["file"]["key"], "file_sha256": p["file"]["sha256"],
                      "file_bytes": p["file"]["bytes"], "version": p["version"], "status": "validated" if p["validation"].get("ok") else "failed",
                      "validation": {"ok": p["validation"].get("ok"), "errors": p["validation"].get("errors", [])[:5]},
                      "active": bool(p["validation"].get("ok"))} for p in products],
        "listings": [{k: l.get(k) for k in ("product_id", "channel", "external_id", "url", "price_cents", "currency", "status", "last_error")} for l in listings],
        "site": {"base_url": CFG["site_base"], "stores": {s["id"]: f"{CFG['site_base']}/{s['path']}" for s in CFG["stores"]}},
    }
    r = call("/admin/sync", body)
    print(f"uploaded {uploaded} file(s); synced {len(body['products'])} products, {len(body['listings'])} listings: {r}")


if __name__ == "__main__":
    main()
