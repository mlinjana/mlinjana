(() => {
  const body = document.body;
  const API = body.dataset.api, STORE = body.dataset.store, PID = body.dataset.product || null;
  const $ = (s) => document.querySelector(s);

  // privacy-light analytics: no cookies, no IPs stored — page type, path, product and referrer host only
  try {
    if (navigator.webdriver) throw 0; // skip automated browsers (tests, most bots) so analytics reflect people
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

  // ---- motion & 3D (skipped entirely when the visitor prefers reduced motion) ----
  window.__rv = 1;
  const calm = matchMedia("(prefers-reduced-motion: reduce)").matches;
  const fine = matchMedia("(hover: hover) and (pointer: fine)").matches;
  const rv = document.querySelectorAll(".rv");
  if (calm || !("IntersectionObserver" in window)) rv.forEach((e) => e.classList.add("in"));
  else {
    const io = new IntersectionObserver((es) => es.forEach((e) => { if (e.isIntersecting) { e.target.classList.add("in"); io.unobserve(e.target); } }), { rootMargin: "0px 0px -8% 0px", threshold: 0.08 });
    rv.forEach((e) => io.observe(e));
  }
  const tilt = (el, max, scene) => {
    let raf = 0;
    el.addEventListener("pointermove", (ev) => {
      const r = el.getBoundingClientRect(), x = (ev.clientX - r.left) / r.width, y = (ev.clientY - r.top) / r.height;
      cancelAnimationFrame(raf);
      raf = requestAnimationFrame(() => {
        el.style.setProperty("--ry", `${(x - 0.5) * max * 2 + (scene ? -10 : 0)}deg`);
        el.style.setProperty("--rx", `${(0.5 - y) * max * 2 + (scene ? 6 : 0)}deg`);
        el.querySelectorAll(".glare,.shine").forEach((g) => { g.style.setProperty("--gx", `${x * 100}%`); g.style.setProperty("--gy", `${y * 100}%`); });
      });
    });
    el.addEventListener("pointerleave", () => { el.style.removeProperty("--rx"); el.style.removeProperty("--ry"); });
  };
  if (!calm && fine) {
    document.querySelectorAll("[data-tilt]").forEach((el) => tilt(el, 6, false));
    document.querySelectorAll("[data-tilt-scene]").forEach((el) => tilt(el, 10, true));
  }

  // ---- product gallery + lightbox ----
  const thumbs = [...document.querySelectorAll(".thumbs button")];
  const srcs = thumbs.map((b) => b.dataset.src);
  let cur = 0;
  const show = (i) => {
    if (!srcs.length) return;
    cur = (i + srcs.length) % srcs.length;
    const m = $("#main-img");
    m.style.opacity = 0.3;
    m.onload = () => { m.style.opacity = 1; };
    m.src = srcs[cur];
    thumbs.forEach((b, k) => b.classList.toggle("on", k === cur));
    const lb = $("#lb-img");
    if (lb) { lb.src = srcs[cur]; $("#lb-count").textContent = `${cur + 1} / ${srcs.length}`; }
  };
  thumbs.forEach((b, k) => b.addEventListener("click", () => show(k)));
  const dlg = $("#lightbox");
  if (dlg && dlg.showModal) {
    document.querySelectorAll("[data-open-lightbox]").forEach((b) => b.addEventListener("click", () => { show(cur); dlg.showModal(); }));
    dlg.querySelector("[data-lb-close]").addEventListener("click", () => dlg.close());
    dlg.querySelector("[data-lb-prev]").addEventListener("click", () => show(cur - 1));
    dlg.querySelector("[data-lb-next]").addEventListener("click", () => show(cur + 1));
    dlg.addEventListener("click", (e) => { if (e.target === dlg) dlg.close(); });
    dlg.addEventListener("keydown", (e) => { if (e.key === "ArrowLeft") show(cur - 1); if (e.key === "ArrowRight") show(cur + 1); });
    let sx = 0;
    dlg.addEventListener("touchstart", (e) => { sx = e.touches[0].clientX; }, { passive: true });
    dlg.addEventListener("touchend", (e) => { const dx = e.changedTouches[0].clientX - sx; if (Math.abs(dx) > 40) show(cur + (dx < 0 ? 1 : -1)); });
  }

  // ---- sticky buy bar on phones: visible while the buy box is off screen ----
  const bar = $("#buybar"), buyBox = $("#buy");
  if (bar && buyBox && "IntersectionObserver" in window) {
    bar.hidden = false;
    let seen = false;
    new IntersectionObserver(([e]) => { if (e.isIntersecting) seen = true; bar.classList.toggle("show", !e.isIntersecting && seen); }).observe(buyBox);
    bar.querySelector("[data-goto-buy]").addEventListener("click", () => { buyBox.scrollIntoView({ behavior: calm ? "auto" : "smooth", block: "center" }); setTimeout(() => $("#email").focus({ preventScroll: true }), calm ? 0 : 450); });
  }

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
      try { if (!navigator.webdriver) navigator.sendBeacon(API + "/store-api/track", JSON.stringify({ store: STORE, type: "checkout_start", product_id: PID, path: location.pathname })); } catch (_) {}
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
