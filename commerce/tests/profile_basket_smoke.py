"""Simulate account-owned carts without contacting production or storing real users.

Covers guest -> signed-in merge, updates, logout, other account isolation,
and same-user return with products restored from the mock database.
"""
from functools import partial
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from threading import Thread
from urllib.parse import urlsplit
from playwright.sync_api import sync_playwright
import json

SITE = Path(__file__).resolve().parents[1] / "site"
A = "aaaaaaaa-aaaa-4aaa-aaaa-aaaaaaaaaaaa"
B = "bbbbbbbb-bbbb-4bbb-bbbb-bbbbbbbbbbbb"
SERVER = {
    A: ["ABL-009:team"],
    B: ["CHK-011"],
}

class Handler(SimpleHTTPRequestHandler):
    def do_GET(self):
        path = urlsplit(self.path).path
        if path != "/" and (SITE / (path.lstrip("/") + ".html")).is_file():
            self.path = path + ".html"
        super().do_GET()
    def log_message(self, *_):
        pass

def assert_basket(page, expected):
    page.wait_for_function("(list) => JSON.stringify(JSON.parse(localStorage.getItem('mls:basket') || '[]')) === JSON.stringify(list)", expected)
    actual = page.evaluate("JSON.parse(localStorage.getItem('mls:basket') || '[]')")
    assert actual == expected, (actual, expected)

def sign_in(page, user_id, email):
    page.evaluate("""({id,email}) => {
      localStorage.setItem('mls:session', JSON.stringify({
        access_token:id,refresh_token:'mock-refresh',expires_at:Math.floor(Date.now()/1000)+3600,
        user:{id,email,name:'Buyer'}
      }));
      document.dispatchEvent(new Event('mls:account'));
    }""", {"id": user_id, "email": email})

def main():
    server = ThreadingHTTPServer(("127.0.0.1", 0), partial(Handler, directory=str(SITE)))
    Thread(target=server.serve_forever, daemon=True).start()
    origin = f"http://127.0.0.1:{server.server_port}"
    operations = []
    try:
        with sync_playwright() as pw:
            browser = pw.chromium.launch(headless=True)
            context = browser.new_context()

            def intercept(route):
                url = route.request.url
                req = route.request
                if url.startswith(origin + "/"):
                    return route.continue_()
                headers = {"access-control-allow-origin": "*", "content-type": "application/json"}
                if req.method == "OPTIONS":
                    return route.fulfill(status=204, headers={
                        **headers, "access-control-allow-methods": "GET,POST,OPTIONS",
                        "access-control-allow-headers": "apikey,authorization,content-type,prefer"
                    }, body="")
                if "/rest/v1/account_baskets" in url:
                    user_id = req.headers.get("authorization", "").replace("Bearer ", "")
                    assert user_id in (A, B), "Missing auth / unexpected customer"
                    if req.method == "GET":
                        operations.append(("read", user_id))
                        return route.fulfill(status=200, headers=headers,
                                             body=json.dumps([{"items": SERVER[user_id]}]))
                    if req.method == "POST":
                        obj = req.post_data_json
                        assert obj["user_id"] == user_id, "Cross-account update attempted"
                        assert len(obj["items"]) <= 25
                        SERVER[user_id] = obj["items"]
                        operations.append(("write", user_id, list(SERVER[user_id])))
                        return route.fulfill(status=204, headers=headers, body="")
                if "/auth/v1/logout" in url:
                    return route.fulfill(status=204, headers=headers, body="")
                if "/rest/v1/account_favourites" in url:
                    return route.fulfill(status=200, headers=headers, body="[]")
                if "/rest/v1/" in url:
                    return route.fulfill(status=200, headers=headers, body="[]")
                return route.abort()
            context.route("**/*", intercept)
            page = context.new_page()
            page.goto(origin+"/account", wait_until="domcontentloaded")
            page.locator("#acct-signin:visible").wait_for()

            # Guest adds a product before signing in. A already had a saved team item.
            page.evaluate("localStorage.setItem('mls:basket', JSON.stringify(['BZW-003']))")
            page.reload(wait_until="domcontentloaded")
            assert_basket(page, ["BZW-003"])
            sign_in(page, A, "buyer-a@example.invalid")
            page.wait_for_function("() => document.querySelector('.bk-count')?.textContent === '2'")
            assert_basket(page, ["BZW-003", "ABL-009:team"])
            page.wait_for_function("() => JSON.stringify(window.__nope) === undefined") if False else None
            # Wait for the remote upsert and verify it contains the merged cart.
            page.wait_for_timeout(150)
            assert SERVER[A] == ["BZW-003", "ABL-009:team"], SERVER[A]

            # Add another item: should be persisted without needing checkout.
            page.goto(origin+"/abacus/p/50-30-20-budget-calculator", wait_until="domcontentloaded")
            page.locator("#buy").click()
            page.wait_for_timeout(250)
            assert SERVER[A] == ["BZW-003", "ABL-009:team", "ABL-025"], SERVER[A]

            page.goto(origin+"/account", wait_until="domcontentloaded")
            page.locator("#acct-in:visible").wait_for()
            page.locator("#acct-signout").click()
            page.locator("#acct-signin:visible").wait_for()
            assert_basket(page, [])
            assert SERVER[A] == ["BZW-003", "ABL-009:team", "ABL-025"], SERVER[A]

            # Another account on the same device must not see A's items.
            sign_in(page, B, "buyer-b@example.invalid")
            assert_basket(page, ["CHK-011"])
            page.locator("#acct-signout").click()
            page.locator("#acct-signin:visible").wait_for()
            assert_basket(page, [])
            assert SERVER[B] == ["CHK-011"], SERVER[B]

            # A signs back in and gets the original cart from the account.
            sign_in(page, A, "buyer-a@example.invalid")
            assert_basket(page, ["BZW-003", "ABL-009:team", "ABL-025"])
            assert any(op[0]=="write" and op[1]==A for op in operations)
            assert ("read", B) in operations
            context.close()
            browser.close()
    finally:
        server.shutdown()
    print("PASS: guest cart merges, account basket persists, other customer isolated, return restores it")

if __name__=="__main__":
    main()
