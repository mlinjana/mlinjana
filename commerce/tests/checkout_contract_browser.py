"""Isolated browser contract tests for the payment initiation journey.

Intercepts the Supabase checkout endpoint and external payment target in Chromium.
No real PayFast request is made and no production backend is contacted. This is NOT
a substitute for the end-to-end live ITN, receipt and download acceptance test.
"""
from functools import partial
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from threading import Thread
import json

from playwright.sync_api import sync_playwright

SITE = Path(__file__).resolve().parents[1] / "site"
API = "https://mrunxptxavtompcnegkr.supabase.co/functions/v1"


def do_case(page, mode, calls):
    page.goto(page.context._test_base + "/abacus/p/inventory-management-spreadsheet", wait_until="domcontentloaded")
    page.locator("#buy").click()
    page.locator("#bk-email").fill("tester@example.invalid")
    page.locator("#bk-form button[type=submit]").click()
    if mode == "failure":
        page.locator("#bk-msg.err").wait_for()
        assert "Online checkout opens soon" in page.locator("#bk-msg").inner_text()
        assert page.locator("#bk-form button[type=submit]").is_enabled(), "Retry button should recover"
        assert page.evaluate("JSON.parse(localStorage.getItem('mls:basket'))") == ["ABL-009"]
    else:
        page.wait_for_function("() => !!localStorage.getItem('mls:orders')")
        saved = page.evaluate("JSON.parse(localStorage.getItem('mls:orders'))")
        outbound = page.evaluate("window.__mockPayfast")
        assert outbound["action"] == "https://example.invalid/mock-payment", outbound
        assert outbound["method"] == "post"
        assert outbound["fields"]["amount"] == "149.00"
        assert saved[0]["ref"] == "ORD-TESTONLY"
        assert saved[0]["url"].startswith("https://example.invalid/thanks?"), saved
    events = page.evaluate("window.__trackingEvents || []")
    types = [e.get("type") for e in events]
    expected = ["product_view", "basket_add", "checkout_start",
                "checkout_error" if mode == "failure" else "checkout_handoff"]
    for event_type in expected:
        assert types.count(event_type) == 1, f"{mode}: expected exactly one {event_type}, got {types}"
    assert all(e.get("product_id") == "ABL-009" for e in events), events
    # Event data must not include customer email, tokens or payment details.
    assert all("email" not in e and "token" not in e for e in events), events
    assert all("tester@example.invalid" not in json.dumps(e) for e in events), events

    assert calls, "Expected checkout initiation request"
    assert calls[0]["product_id"] == "ABL-009"
    assert calls[0]["licence"] == "standard"
    assert calls[0]["email"] == "tester@example.invalid"


def main():
    class Handler(SimpleHTTPRequestHandler):
        def do_GET(self):
            p = self.path.split("?")[0]
            if p != "/" and (SITE / (p.lstrip("/") + ".html")).is_file():
                self.path = p + ".html"
            super().do_GET()

        def log_message(self, *args):
            pass

    server = ThreadingHTTPServer(("127.0.0.1", 0), partial(Handler, directory=str(SITE)))
    Thread(target=server.serve_forever, daemon=True).start()
    base = f"http://127.0.0.1:{server.server_port}"

    try:
        with sync_playwright() as pw:
            browser = pw.chromium.launch(headless=True)
            for mode in ("failure", "handoff"):
                context = browser.new_context()
                # Keep the browser on the local origin: capture the generated form
                # instead of submitting it to a payment provider or leaving the page.
                context.add_init_script("""(() => {
                    // Capture analytics in memory, never post to Supabase.
                    Object.defineProperty(navigator, 'webdriver', { configurable: true, get: () => undefined });
                    window.__trackingEvents = [];
                    navigator.sendBeacon = function (url, body) {
                        if (url.endsWith('/store-api/track')) {
                            window.__trackingEvents.push(JSON.parse(body));
                            return true;
                        }
                        return false;
                    };
                    HTMLFormElement.prototype.submit = function () {
                        window.__mockPayfast = {
                          action: this.action, method: this.method,
                          fields: Object.fromEntries([...this.elements].filter(x => x.name).map(x => [x.name, x.value]))
                        };
                    };
                })()""")
                context._test_base = base
                calls = []

                def intercept(route):
                    url = route.request.url
                    if url.startswith(base + "/"):
                        return route.continue_()
                    if url == API + "/store-api/checkout":
                        if route.request.method == "OPTIONS":
                            return route.fulfill(status=204, headers={"access-control-allow-origin": "*",
                                "access-control-allow-methods": "POST, OPTIONS",
                                "access-control-allow-headers": "content-type"})
                        calls.append(route.request.post_data_json)
                        if mode == "failure":
                            return route.fulfill(status=503, headers={"access-control-allow-origin": "*", "content-type": "application/json"},
                                body=json.dumps({"error": "Checkout is temporarily unavailable"}))
                        return route.fulfill(status=200, headers={"access-control-allow-origin": "*", "content-type": "application/json"},
                            body=json.dumps({"action": "https://example.invalid/mock-payment",
                                             "fields": {"return_url": "https://example.invalid/thanks?ref=ORD-TESTONLY&k=FAKE",
                                                        "amount": "149.00"}, "ref": "ORD-TESTONLY"}))
                    return route.abort()  # Includes PayFast; absolutely no real external requests.

                context.route("**/*", intercept)
                page = context.new_page()
                do_case(page, mode, calls)
                context.close()
            browser.close()
    finally:
        server.shutdown()

    print("Mocked checkout recovery, payment handoff and event sequence passed without touching production.")


if __name__ == "__main__":
    main()
