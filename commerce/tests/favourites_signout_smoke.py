"""Test shared-device favourites are cleared at sign-out without deleting account favourites."""
from functools import partial
from http.server import SimpleHTTPRequestHandler,ThreadingHTTPServer
from pathlib import Path
from threading import Thread
from urllib.parse import urlsplit
from playwright.sync_api import sync_playwright
import json

SITE=Path(__file__).resolve().parents[1]/"site"
class Handler(SimpleHTTPRequestHandler):
    def do_GET(self):
        p=urlsplit(self.path).path
        if p!="/" and (SITE/(p.lstrip("/")+".html")).is_file(): self.path=p+".html"
        super().do_GET()
    def log_message(self,*args): pass

def main():
    server=ThreadingHTTPServer(("127.0.0.1",0),partial(Handler,directory=str(SITE)))
    Thread(target=server.serve_forever,daemon=True).start()
    origin=f"http://127.0.0.1:{server.server_port}"
    try:
        with sync_playwright() as pw:
            browser=pw.chromium.launch(headless=True)
            for logout_error in (False,True):
                context=browser.new_context()
                context.add_init_script("""(() => {
                  if (sessionStorage.getItem('seeded')) return;
                  sessionStorage.setItem('seeded','1');
                  localStorage.setItem('mls:session',JSON.stringify({
                    access_token:'FAKE',refresh_token:'FAKE',
                    expires_at:Math.floor(Date.now()/1000)+3600,
                    user:{id:'test-user',email:'test@example.invalid',name:'Test'}
                  }));
                  localStorage.setItem('mls:favs',JSON.stringify(['ABL-009','BZW-003']));
                  localStorage.setItem('mls:basket',JSON.stringify(['ABL-009']));
                })()""")
                remote=[]
                def route_fn(route):
                    url=route.request.url
                    if url.startswith(origin+"/"): return route.continue_()
                    if "/auth/v1/logout" in url:
                        return route.fulfill(status=500 if logout_error else 204,
                          headers={"access-control-allow-origin":"*"},body="failure" if logout_error else "")
                    if "/rest/v1/account_favourites" in url:
                        remote.append((route.request.method,url))
                        return route.fulfill(status=200,headers={
                          "access-control-allow-origin":"*","content-type":"application/json"},
                          body='[{"product_id":"ABL-009"},{"product_id":"BZW-003"}]')
                    if "/rest/v1/" in url:
                        return route.fulfill(status=200,headers={
                          "access-control-allow-origin":"*","content-type":"application/json"},body="[]")
                    return route.abort()
                context.route("**/*",route_fn)
                page=context.new_page()
                page.goto(origin+"/account",wait_until="domcontentloaded")
                page.locator("#acct-in:visible").wait_for()
                page.wait_for_function("() => document.querySelector('.fav-count')?.textContent === '2'")
                page.locator("#acct-signout").click()
                page.locator("#acct-signin:visible").wait_for()
                page.wait_for_function("() => !localStorage.getItem('mls:session')")
                assert page.evaluate("JSON.parse(localStorage.getItem('mls:favs'))")==[]
                assert page.evaluate("JSON.parse(localStorage.getItem('mls:basket'))")==[]
                assert page.locator(".fav-count:visible").count()==0
                assert page.locator(".bk-count:visible").count()==0
                # Frontend sign-out must not issue DELETE for persisted favourites.
                assert not any(method=="DELETE" for method,_ in remote),remote
                page.reload(wait_until="domcontentloaded")
                page.locator("#acct-signin:visible").wait_for()
                assert page.locator(".fav-count:visible").count()==0
                assert page.evaluate("JSON.parse(localStorage.getItem('mls:favs'))")==[]
                context.close()
            browser.close()
    finally: server.shutdown()
    print("PASS: sign-out clears local basket and favourites in success and failure cases")

if __name__=="__main__": main()
