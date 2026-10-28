(() => {
  const body = document.body;
  const API = body.dataset.api, STORE = body.dataset.store, PID = body.dataset.product || null;
  const $ = (s) => document.querySelector(s);

  // privacy-light analytics: no cookies, no IPs stored — page type, path, product and referrer host only
  try {
    const type = PID ? "product_view" : "page_view";
    const data = JSON.stringify({ store: STORE, type, path: location.pathname, product_id: PID, ref: document.referrer || null });
    navigator.sendBeacon ? navigator.sendBeacon(API + "/store-api/track", data) : fetch(API + "/store-api/track", { method: "POST", body: data, keepalive: true });
  } catch (e) {}

  // catalogue search + category filter
  const grid = $("#grid");
  if (grid) {
    let cat = "";
    const q = $("#q");
    const apply = () => {
      const t = (q.value || "").toLowerCase().trim();
      let n = 0;
      grid.querySelectorAll(".card").forEach((c) => {
        const show = (!cat || c.dataset.cat === cat) && (!t || t.split(/\s+/).every((w) => c.dataset.text.includes(w)));
        c.hidden = !show;
        if (show) n++;
      });
      $("#empty").hidden = n > 0;
    };
    q.addEventListener("input", apply);
    document.querySelectorAll(".chip").forEach((b) => b.addEventListener("click", () => {
      document.querySelectorAll(".chip").forEach((x) => x.classList.remove("on"));
      b.classList.add("on");
      cat = b.dataset.cat;
      apply();
    }));
  }

  // product gallery
  document.querySelectorAll(".thumbs button").forEach((b) => b.addEventListener("click", () => { $("#main-img").src = b.dataset.src; }));

  // checkout → PayFast hosted payment page (we never handle card details)
  const buy = $("#buy");
  if (buy) {
    if (new URLSearchParams(location.search).get("cancelled")) $("#buy-msg").textContent = "Payment was cancelled — you have not been charged.";
    buy.addEventListener("submit", async (e) => {
      e.preventDefault();
      const msg = $("#buy-msg"), btn = buy.querySelector("button");
      const email = $("#email").value.trim();
      msg.className = "msg";
      if (!/^[^\s@]+@[^\s@]+\.[^\s@]{2,}$/.test(email)) { msg.textContent = "Please enter a valid email address."; msg.className = "msg err"; return; }
      btn.disabled = true; msg.textContent = "Starting secure checkout…";
      try { navigator.sendBeacon(API + "/store-api/track", JSON.stringify({ store: STORE, type: "checkout_start", product_id: PID, path: location.pathname })); } catch (_) {}
      try {
        const r = await fetch(API + "/store-api/checkout", { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ product_id: PID, email, store: STORE }) });
        const d = await r.json();
        if (!r.ok) throw new Error(d.error || "Checkout failed");
        const f = document.createElement("form");
        f.method = "POST"; f.action = d.action;
        for (const [k, v] of Object.entries(d.fields)) { const i = document.createElement("input"); i.type = "hidden"; i.name = k; i.value = v; f.appendChild(i); }
        document.body.appendChild(f);
        f.submit();
      } catch (err) { msg.textContent = err.message; msg.className = "msg err"; btn.disabled = false; }
    });
  }

  // thank-you page: wait for the payment provider's confirmation, then show the download
  const st = $("#order-status");
  if (st) {
    const p = new URLSearchParams(location.search);
    const ref = p.get("ref"), k = p.get("k");
    if (!ref || !k) { st.textContent = "We couldn't find your order details in this link."; return; }
    $("#order-ref").textContent = ref;
    let tries = 0;
    const poll = async () => {
      tries++;
      try {
        const r = await fetch(`${API}/store-api/order?ref=${encodeURIComponent(ref)}&k=${encodeURIComponent(k)}`);
        const d = await r.json();
        if (d.status === "paid" && d.download) {
          st.innerHTML = `<p><strong>Payment confirmed.</strong> Your download is ready.</p><p><a class="btn inline" href="${d.download}">Download your files (ZIP)</a></p>` +
            `<p class="small muted">Link valid until ${new Date(d.expires_at).toLocaleDateString()} · ${d.downloads_left} downloads left. Bookmark this page to download again.</p>` +
            (d.mode === "sandbox" ? `<p class="small muted">Test-mode order (PayFast sandbox) — no real payment was taken.</p>` : "");
          return;
        }
        if (["cancelled", "failed", "expired"].includes(d.status)) { st.innerHTML = `<p>This payment was <strong>${d.status}</strong>. You have not been charged.</p>`; return; }
        st.innerHTML = `<p>Waiting for payment confirmation from PayFast… (this usually takes a few seconds)</p>`;
      } catch (e) { st.textContent = "Checking your order…"; }
      if (tries < 60) setTimeout(poll, tries < 10 ? 3000 : 10000);
      else st.innerHTML = "<p>We haven't received confirmation yet. If you were charged, please contact us with your order number — we'll sort it out.</p>";
    };
    poll();
  }

  // contact form
  const cf = $("#contact");
  if (cf) cf.addEventListener("submit", async (e) => {
    e.preventDefault();
    const m = $("#contact-msg");
    const data = Object.fromEntries(new FormData(cf));
    data.store = STORE;
    const r = await fetch(API + "/store-api/contact", { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(data) }).catch(() => null);
    const d = r ? await r.json() : { error: "Network error" };
    m.textContent = r && r.ok ? "Thanks — we've received your message and will reply by email." : (d.error || "Something went wrong.");
    m.className = r && r.ok ? "msg" : "msg err";
    if (r && r.ok) cf.reset();
  });
})();
