"""Read-only browser QA for marketplace homepage, starter page and a real product.

Serves the freshly generated site locally. External requests (including the live
payment API) are blocked. No purchases, user accounts, or production mutations.
"""
from functools import partial
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from threading import Thread
from urllib.parse import unquote, urlsplit
import os

from playwright.sync_api import sync_playwright

SITE = Path(__file__).resolve().parents[1] / "site"
ARTIFACTS = Path(os.environ.get("BROWSER_ARTIFACTS", "/tmp/mlinjanastudios-browser-qa"))
ARTIFACTS.mkdir(parents=True, exist_ok=True)


class CloudflareLikeHandler(SimpleHTTPRequestHandler):
    """Emulate html_handling auto-trailing-slash for local smoke tests."""
    def do_GET(self):
        path = unquote(urlsplit(self.path).path)
        target = SITE / path.lstrip("/")
        if path != "/" and target.is_dir() and not path.endswith("/"):
            self.send_response(307)
            self.send_header("Location", path + "/")
            self.end_headers()
            return
        if path != "/" and not target.exists() and (SITE / (path.lstrip("/") + ".html")).is_file():
            self.path = path + ".html"
        super().do_GET()

    def log_message(self, format, *args):
        pass


def check(page, base, viewport, label):
    page.set_viewport_size(viewport)
    page.goto(base + "/", wait_until="domcontentloaded")
    page.locator("#shop-by-task").wait_for()
    page.locator('a[href="/start-here"]').first.wait_for()
    page.screenshot(path=str(ARTIFACTS / (label + "-home.png")), full_page=True)
    width = page.evaluate("document.documentElement.scrollWidth - window.innerWidth")
    assert width <= 2, f"{label}: homepage horizontal overflow {width}px"
    page.goto(base + "/start-here", wait_until="domcontentloaded")
    page.locator(".starter-item").first.wait_for()
    assert page.locator(".starter-item").count() == 5
    page.screenshot(path=str(ARTIFACTS / (label + "-start-here.png")), full_page=True)
    width = page.evaluate("document.documentElement.scrollWidth - window.innerWidth")
    assert width <= 2, f"{label}: curated page horizontal overflow {width}px"
    page.goto(base + "/abacus/p/inventory-management-spreadsheet", wait_until="domcontentloaded")
    page.locator("#buy").wait_for()
    assert page.locator('a[href="/help/downloads"]').count() >= 1
    page.screenshot(path=str(ARTIFACTS / (label + "-product.png")), full_page=True)
    width = page.evaluate("document.documentElement.scrollWidth - window.innerWidth")
    assert width <= 2, f"{label}: product page horizontal overflow {width}px"


def main():
    server = ThreadingHTTPServer(("127.0.0.1", 0), partial(CloudflareLikeHandler, directory=str(SITE)))
    thread = Thread(target=server.serve_forever, daemon=True)
    thread.start()
    base = f"http://127.0.0.1:{server.server_port}"
    try:
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            for label, viewport in [
                ("mobile", {"width": 375, "height": 812}),
                ("tablet", {"width": 768, "height": 1024}),
                ("desktop", {"width": 1366, "height": 900}),
            ]:
                context = browser.new_context(viewport=viewport, reduced_motion="reduce")
                # Prevent test browser from reaching production checkout / analytics.
                context.route("**/*", lambda route: route.continue_() if route.request.url.startswith(base + "/") else route.abort())
                page = context.new_page()
                check(page, base, viewport, label)
                context.close()
            browser.close()
    finally:
        server.shutdown()
    print("Browser smoke tests passed; screenshots saved to", ARTIFACTS)


if __name__ == "__main__":
    main()
