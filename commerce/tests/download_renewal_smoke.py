"""Account download renewal: intercepted HTTP only, no live API, auth or paid files."""
from functools import partial
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from threading import Thread
from urllib.parse import urlsplit
from playwright.sync_api import sync_playwright
import json

SITE = Path(__file__).resolve().parents[1] / "site"
API = "https://mrunxptxavtompcnegkr.supabase.co"
FN = API + "/functions/v1"
ACCOUNT_ID = "11111111-1111-4111-8111-111111111111"
REF = "ORD-AAAAAAAAAAAA"
TOKEN = "a" * 48
CURRENT = "b" * 48

class Handler(SimpleHTTPRequestHandler):
    def do_GET(self):
        path = urlsplit(self.path).path
        if path != "/" and (SITE / (path.lstrip("/") + ".html")).is_file():
            self.path = path + ".html"
        super().do_GET()
    def log_message(self, *args):
        pass

def main():
    server = ThreadingHTTPServer(("127.0.0.1", 0), partial(Handler, directory=str(SITE)))
    Thread(target=server.serve_forever, daemon=True).start()
    origin = f"http://127.0.0.1:{server.server_port}"
    requests = []
    state = {"fail":True}
    try:
        with sync_playwright() as pw:
            browser = pw.chromium.launch(headless=True)
            ctx = browser.new_context()
            ctx.add_init_script("""(() => {
              if (sessionStorage.getItem('seed')) return;
              sessionStorage.setItem('seed','1');
              localStorage.setItem('mls:session',JSON.stringify({
                access_token:'MOCK-ACCESS',refresh_token:'MOCK-REFRESH',
                expires_at:Math.floor(Date.now()/1000)+3600,
                user:{id:'11111111-1111-4111-8111-111111111111',
                  email:'buyer@example.invalid',name:'Buyer'}
              }));
            })()""")

            def intercept(route):
                req = route.request
                url = req.url
                if url.startswith(origin + "/"):
                    return route.continue_()
                cors = {"access-control-allow-origin":"*","content-type":"application/json",
                        "access-control-allow-methods":"GET,POST,OPTIONS",
                        "access-control-allow-headers":"authorization,apikey,content-type,prefer"}
                if req.method == "OPTIONS":
                    return route.fulfill(status=204,headers=cors,body="")
                if "/rest/v1/rpc/my_orders" in url:
                    body = [
                      {"ref":REF,"title":"Example Workbook","licence":"standard",
                       "amount_cents":14900,"paid_at":"2026-11-07T09:00:00Z",
                       "status":"paid","download_token":None},
                      {"ref":"ORD-BBBBBBBBBBBB","title":"Current Workbook","licence":"standard",
                       "amount_cents":8900,"paid_at":"2026-11-07T09:00:00Z",
                       "status":"paid","download_token":CURRENT},
                      {"ref":"ORD-CCCCCCCCCCCC","title":"Refunded Workbook","licence":"standard",
                       "amount_cents":5900,"paid_at":"2026-11-07T09:00:00Z",
                       "status":"refunded","download_token":None}
                    ]
                    return route.fulfill(status=200,headers=cors,body=json.dumps(body))
                if "/rest/v1/rpc/renew_my_download" in url:
                    requests.append((req.method, req.post_data_json, req.headers.get("authorization")))
                    assert req.post_data_json == {"p_ref":REF}
                    assert req.headers.get("authorization") == "Bearer MOCK-ACCESS"
                    if state["fail"]:
                        return route.fulfill(status=429,headers=cors,body='{"message":"Daily limit"}')
                    return route.fulfill(status=200,headers=cors,body=json.dumps(TOKEN))
                if "/rest/v1/profiles" in url or "/rest/v1/account_favourites" in url:
                    return route.fulfill(status=200,headers=cors,body="[]")
                if "/rest/v1/account_baskets" in url:
                    return route.fulfill(status=200 if req.method=="GET" else 204,headers=cors,
                                         body='[{"items":[]}]' if req.method=="GET" else "")
                if "/functions/v1/store-api/download" in url:
                    assert "t="+TOKEN in url, url
                    return route.fulfill(status=200,headers={"content-type":"text/plain"},
                                         body="Mock download complete")
                return route.abort()

            ctx.route("**/*",intercept)
            page = ctx.new_page()
            page.goto(origin + "/account", wait_until="domcontentloaded")
            button = page.locator(f'[data-renew-order="{REF}"]')
            button.wait_for()
            assert button.inner_text().strip() == "Renew & download"
            assert page.locator('a[href*="store-api/download?t='+CURRENT+'"]').count() == 1
            assert page.locator('[data-renew-order="ORD-CCCCCCCCCCCC"]').count() == 0

            # A failed renewal must show an actionable inline error and permit retry.
            button.click()
            page.locator("#acct-download-msg.err").wait_for()
            assert "try again" in page.locator("#acct-download-msg").inner_text().lower()
            assert button.is_enabled()
            assert len(requests) == 1

            # On retry a valid token is returned, with the browser following the
            # existing download endpoint. Never call a real Supabase or file URL.
            state["fail"] = False
            button.click()
            page.wait_for_url("**/store-api/download?t=*")
            assert len(requests) == 2
            assert "Mock download complete" in page.locator("body").inner_text()
            ctx.close()
            browser.close()
    finally:
        server.shutdown()
    print("PASS: expired paid order renews, failed requests retry, active links and refunded orders unchanged")

if __name__ == "__main__":
    main()
