"""Local-only OAuth UX smoke tests. Never connects to Supabase or Google."""
from functools import partial
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from threading import Thread
from urllib.parse import urlsplit
from playwright.sync_api import sync_playwright

SITE=Path(__file__).resolve().parents[1]/"site"
API="https://mrunxptxavtompcnegkr.supabase.co"

class Handler(SimpleHTTPRequestHandler):
    def do_GET(self):
        path=urlsplit(self.path).path
        if path!="/" and (SITE/(path.lstrip("/")+".html")).is_file():
            self.path=path+".html"
        super().do_GET()
    def log_message(self,*args): pass

def main():
    server=ThreadingHTTPServer(("127.0.0.1",0),partial(Handler,directory=str(SITE)))
    Thread(target=server.serve_forever,daemon=True).start()
    base=f"http://127.0.0.1:{server.server_port}"
    try:
        with sync_playwright() as p:
            browser=p.chromium.launch(headless=True)
            for enabled in (False, True):
                ctx=browser.new_context()
                observed=[]
                def route_fn(route):
                    url=route.request.url
                    if url.startswith(base+"/"): return route.continue_()
                    if url.startswith(API+"/auth/v1/settings"):
                        return route.fulfill(status=200,headers={"access-control-allow-origin":"*","content-type":"application/json"},
                            body='{"external":{"google":'+str(enabled).lower()+'}}')
                    if url.startswith(API+"/auth/v1/authorize"):
                        observed.append(url)
                        return route.fulfill(status=200,headers={"content-type":"text/plain"},body="Mock OAuth endpoint")
                    return route.abort()
                ctx.route("**/*",route_fn)
                page=ctx.new_page()
                page.goto(base+"/account",wait_until="domcontentloaded")
                page.locator("#acct-signin:visible").wait_for()
                page.locator("#acct-google").click()
                if enabled:
                    page.wait_for_url("**/auth/v1/authorize?*")
                    assert len(observed)==1 and "provider=google" in observed[0],observed
                    assert "redirect_to=" in observed[0],observed
                else:
                    page.locator("#acct-google-msg.err").wait_for()
                    assert "unavailable" in page.locator("#acct-google-msg").inner_text()
                    assert page.locator("#acct-google").is_enabled()
                    assert not observed
                ctx.close()

            ctx=browser.new_context()
            ctx.route("**/*",lambda route: route.continue_() if route.request.url.startswith(base+"/") else route.abort())
            page=ctx.new_page()
            page.goto(base+"/account?error=access_denied&error_description=declined",wait_until="domcontentloaded")
            page.locator("#acct-google-msg.err").wait_for()
            assert "Sign-in could not be completed" in page.locator("#acct-google-msg").inner_text()
            assert "error=" not in page.url
            ctx.close()

            ctx=browser.new_context()
            ctx.add_init_script("""(() => {
              if (location.pathname === '/account') localStorage.setItem('mls:session',
                JSON.stringify({access_token:'FAKE',refresh_token:'FAKE',
                  expires_at:Math.floor(Date.now()/1000)+3600,user:null}));
            })()""")
            ctx.route("**/*",lambda route: route.continue_() if route.request.url.startswith(base+"/") else route.fulfill(status=401,headers={"access-control-allow-origin":"*"},body="unauthorized"))
            page=ctx.new_page()
            page.goto(base+"/account",wait_until="domcontentloaded")
            page.locator("#acct-signin:visible").wait_for()
            page.wait_for_function("() => !localStorage.getItem('mls:session')")
            ctx.close()
            browser.close()
    finally: server.shutdown()
    print("Google provider disabled/enabled, OAuth error, and stale-session UI tests passed")

if __name__=="__main__": main()
