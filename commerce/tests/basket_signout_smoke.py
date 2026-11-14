"""Regression: signing out clears the device-local basket and checkout email.

All authentication and commerce API traffic is intercepted. No real users,
orders, Supabase requests or PayFast traffic are used.
"""
from functools import partial
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from threading import Thread
from urllib.parse import urlsplit
from playwright.sync_api import sync_playwright

SITE = Path(__file__).resolve().parents[1] / "site"
PRODUCTS = ["ABL-009", "BZW-003", "ABL-025", "CHK-011"]


class Handler(SimpleHTTPRequestHandler):
    def do_GET(self):
        p = urlsplit(self.path).path
        if p != "/" and (SITE / (p.lstrip("/") + ".html")).is_file():
            self.path = p + ".html"
        super().do_GET()

    def log_message(self, *_):
        pass


def main():
    server = ThreadingHTTPServer(("127.0.0.1", 0), partial(Handler, directory=str(SITE)))
    Thread(target=server.serve_forever, daemon=True).start()
    base = f"http://127.0.0.1:{server.server_port}"
    try:
        with sync_playwright() as pw:
            browser = pw.chromium.launch(headless=True)
            for logout_fails in (False, True):
                context = browser.new_context()
                context.add_init_script("""(() => {
                    if (location.pathname !== '/account') return;
                    if (sessionStorage.getItem('seeded')) return;
                    sessionStorage.setItem('seeded', '1');
                    localStorage.setItem('mls:session', JSON.stringify({
                      access_token: 'FAKE',
                      refresh_token: 'FAKE',
                      expires_at: Math.floor(Date.now() / 1000) + 3600,
                      user: {id:'fake-user-id',email:'first@example.invalid',name:'First'}
                    }));
                    localStorage.setItem('mls:basket', JSON.stringify(
                      ['ABL-009','BZW-003','ABL-025','CHK-011']));
                })()""")

                def intercept(route):
                    url = route.request.url
                    if url.startswith(base + "/"):
                        return route.continue_()
                    if "/auth/v1/logout" in url:
                        return route.fulfill(status=500 if logout_fails else 204,
                            headers={"access-control-allow-origin":"*"}, body="error" if logout_fails else "")
                    if "/rest/v1/" in url:
                        return route.fulfill(status=200,
                            headers={"access-control-allow-origin":"*","content-type":"application/json"},body="[]")
                    return route.abort()

                context.route("**/*", intercept)
                page = context.new_page()
                page.goto(base + "/account", wait_until="domcontentloaded")
                page.locator("#acct-in:visible").wait_for()
                page.wait_for_function("() => document.querySelector('.bk-count')?.textContent === '4'")
                assert page.locator("#bk-email").input_value() == "first@example.invalid"
                page.locator("#acct-signout").click()
                page.locator("#acct-signin:visible").wait_for()
                assert page.evaluate("JSON.parse(localStorage.getItem('mls:basket'))") == []
                assert page.locator(".bk-count:visible").count() == 0
                assert page.locator("#bk-email").input_value() == ""
                assert page.evaluate("localStorage.getItem('mls:session')") is None

                # No stale cart after refresh on a shared device.
                page.reload(wait_until="domcontentloaded")
                page.locator("#acct-signin:visible").wait_for()
                assert page.locator(".bk-count:visible").count() == 0
                assert page.evaluate("JSON.parse(localStorage.getItem('mls:basket'))") == []

                # Guest shopping should continue to work after signing out.
                page.goto(base + "/abacus/p/inventory-management-spreadsheet", wait_until="domcontentloaded")
                page.locator("#buy").click()
                assert page.evaluate("JSON.parse(localStorage.getItem('mls:basket'))") == ["ABL-009"]
                page.wait_for_function("() => document.querySelector('.bk-count')?.textContent === '1'")
                context.close()
            browser.close()
    finally:
        server.shutdown()
    print("PASS: sign-out clears four-item basket, empty count persists after reload, guest basket still works")


if __name__ == "__main__":
    main()
