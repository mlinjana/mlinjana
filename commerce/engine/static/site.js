(() => {
  const body = document.body;
  const API = body.dataset.api, STORE = body.dataset.store, PID = body.dataset.product || null;
  const $ = (s) => document.querySelector(s);
  const $$ = (s, el = document) => [...el.querySelectorAll(s)];
  const calm = matchMedia("(prefers-reduced-motion: reduce)").matches;
  const esc = (s) => String(s).replace(/[&<>"']/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" })[c]);

  // privacy-light analytics: no cookies, no IPs stored — page type, path, product and referrer host only
  try {
    if (navigator.webdriver) throw 0; // skip automated browsers (tests, most bots) so analytics reflect people
    const type = PID ? "product_view" : "page_view";
    const data = JSON.stringify({ store: STORE, type, path: location.pathname, product_id: PID, ref: document.referrer || null });
    navigator.sendBeacon ? navigator.sendBeacon(API + "/store-api/track", data) : fetch(API + "/store-api/track", { method: "POST", body: data, keepalive: true });
  } catch (e) {}

  // ---- favourites: kept in this browser only (localStorage), never sent anywhere ----
  const FKEY = "mls:favs";
  const getFavs = () => { try { return JSON.parse(localStorage.getItem(FKEY) || "[]"); } catch (e) { return []; } };
  const setFavs = (a) => { try { localStorage.setItem(FKEY, JSON.stringify(a)); } catch (e) {} };
  const syncFavs = () => {
    const f = new Set(getFavs());
    $$("[data-fav]").forEach((b) => {
      const on = f.has(b.dataset.fav);
      b.setAttribute("aria-pressed", on ? "true" : "false");
      const t = b.querySelector("span");
      if (t) t.textContent = on ? "Saved to favourites" : "Add to favourites";
    });
    $$(".fav-count").forEach((c) => { c.hidden = !f.size; c.textContent = f.size; });
  };
  document.addEventListener("click", (e) => {
    const b = e.target.closest("[data-fav]");
    if (!b) return;
    e.preventDefault();
    const id = b.dataset.fav, f = getFavs(), i = f.indexOf(id);
    i >= 0 ? f.splice(i, 1) : f.unshift(id);
    setFavs(f.slice(0, 500));
    syncFavs();
    if (!calm) { b.classList.remove("pop"); void b.offsetWidth; b.classList.add("pop"); }
    if ($("#fav-page") && i >= 0) renderFavs();
  });
  syncFavs();

  // ---- card markup for search results and favourites (same as the server-rendered cards) ----
  const heart = '<svg viewBox="0 0 24 24" aria-hidden="true"><path d="M12 20.5s-7.5-4.6-9.3-9.2C1.4 7.9 3.6 4.5 7 4.5c2 0 3.4 1.1 5 3 1.6-1.9 3-3 5-3 3.4 0 5.6 3.4 4.3 6.8-1.8 4.6-9.3 9.2-9.3 9.2z"/></svg>';
  const cardHTML = (p, shops) => {
    const s = shops[p.s] || { n: "", p: "" };
    return `<article class="card" data-id="${esc(p.i)}"><a class="card-link" href="${esc(p.u)}"><div class="card-media"><img src="${esc(p.img)}" alt="${esc(p.n)}" loading="lazy" width="600" height="450">` +
      (p.o ? `<span class="tag-save">Bundle · save ${p.o}%</span>` : "") + `</div><h3 class="card-title">${esc(p.n)}</h3></a>` +
      `<p class="card-shop"><a href="/${esc(s.p)}/">${esc(s.n)}</a></p>` +
      `<p class="card-price">${p.fr ? "<strong>Free</strong>" : `<strong>R${p.p}</strong>` + (p.o ? ` <s>R${p.b}</s> <span class="off">(${p.o}% off)</span>` : "")}</p>` +
      `<p class="card-meta">Digital download · ${esc(p.f.join(", "))}</p>` +
      `<button type="button" class="fav" data-fav="${esc(p.i)}" aria-pressed="false" aria-label="Save ${esc(p.n)} to favourites">${heart}</button></article>`;
  };
  let catalogue = null;
  const loadCatalogue = async () => catalogue || (catalogue = await fetch("/assets/catalogue.json").then((r) => r.json()));

  // ---- filters on shop and department pages (server-rendered #grid) ----
  const grid = $("#shop .grid");
  if (grid && $("#q")) {
    const cards = $$(".card", grid);
    cards.forEach((c, k) => { c.dataset.k = k; });
    let cat = "";
    const apply = () => {
      const t = ($("#q").value || "").toLowerCase().trim().split(/\s+/).filter(Boolean);
      const fmt = $("#f-fmt").value, max = +$("#f-price").value || 0, sort = $("#f-sort").value;
      let n = 0;
      cards.forEach((c) => {
        const show = (!cat || c.dataset.cat === cat) && (!fmt || c.dataset.fmt.split(" ").includes(fmt)) &&
          (!max || +c.dataset.price < max) && t.every((w) => c.dataset.text.includes(w));
        c.hidden = !show;
        if (show) n++;
      });
      const order = [...cards].sort((a, b) => sort === "lo" ? a.dataset.price - b.dataset.price : sort === "hi" ? b.dataset.price - a.dataset.price : a.dataset.k - b.dataset.k);
      order.forEach((c) => grid.appendChild(c));
      $("#empty").hidden = n > 0;
      $("#count").textContent = `${n} ${n === 1 ? "item" : "items"}`;
    };
    $("#q").addEventListener("input", apply);
    ["#f-fmt", "#f-price", "#f-sort"].forEach((s) => $(s).addEventListener("change", apply));
    $$(".chip").forEach((b) => b.addEventListener("click", () => {
      $$(".chip").forEach((x) => x.classList.remove("on"));
      b.classList.add("on");
      cat = b.dataset.cat;
      apply();
    }));
    apply();
  }

  // ---- site-wide search page ----
  const sp = $("#search-page");
  if (sp) {
    const params = new URLSearchParams(location.search);
    const state = { q: (params.get("q") || "").trim(), dept: params.get("dept") || "", max: params.get("max") || "", fmt: params.get("fmt") || "",
      bundles: params.get("bundles") === "1", free: params.get("free") === "1", sort: params.get("sort") || "", shown: 48 };
    $("#hq").value = state.q;
    const setRadio = (name, v) => { const el = sp.querySelector(`input[name=${name}][value="${v}"]`); if (el) el.checked = true; };
    setRadio("dept", state.dept); setRadio("max", state.max); setRadio("fmt", state.fmt);
    sp.querySelector("input[name=bundles]").checked = state.bundles;
    sp.querySelector("input[name=free]").checked = state.free;
    $("#s-sort").value = state.sort;
    const stem = (w) => (w.length > 3 && w.endsWith("s") ? w.slice(0, -1) : w);
    const render = async () => {
      const { items, shops } = await loadCatalogue();
      const words = state.q.toLowerCase().split(/[^a-z0-9]+/).filter((w) => w.length > 1).map(stem);
      let res = items.filter((p) => (!state.dept || p.d === state.dept) && (!state.max || p.p < +state.max) && (!state.fmt || p.f.includes(state.fmt)) &&
        (!state.bundles || p.o) && (!state.free || p.fr));
      let loose = false;
      if (words.length) {
        const score = (p) => { const n = p.n.toLowerCase(); let s = 0; for (const w of words) { if (n.includes(w)) s += 3; else if (p.t.includes(w)) s += 1; else return -1; } return s; };
        let hit = res.map((p) => [score(p), p]).filter(([s]) => s >= 0);
        if (!hit.length) { // no item has every word: show items matching any of them
          loose = true;
          hit = res.map((p) => [words.filter((w) => p.t.includes(w)).length, p]).filter(([s]) => s > 0);
        }
        res = hit.sort((a, b) => b[0] - a[0]).map(([, p]) => p);
      }
      if (state.sort === "lo") res.sort((a, b) => a.p - b.p);
      if (state.sort === "hi") res.sort((a, b) => b.p - a.p);
      $("#s-title").textContent = state.q ? `Results for “${state.q}”` : "All downloads";
      $("#s-count").textContent = `${res.length} ${res.length === 1 ? "item" : "items"}` + (loose ? " matching some of your words" : "");
      $("#results").innerHTML = res.slice(0, state.shown).map((p) => cardHTML(p, shops)).join("");
      $("#s-empty").hidden = res.length > 0;
      $("#s-more").hidden = res.length <= state.shown;
      syncFavs();
    };
    const push = () => {
      const u = new URLSearchParams();
      if (state.q) u.set("q", state.q);
      ["dept", "max", "fmt", "sort"].forEach((k) => state[k] && u.set(k, state[k]));
      if (state.bundles) u.set("bundles", "1");
      if (state.free) u.set("free", "1");
      history.replaceState(null, "", "?" + u.toString());
      state.shown = 48;
      render();
    };
    sp.addEventListener("change", (e) => {
      const t = e.target;
      if (t.type === "radio") state[t.name] = t.value;
      else if (t.type === "checkbox") state[t.name] = t.checked;
      else if (t.id === "s-sort") state.sort = t.value;
      push();
    });
    $("#s-more").addEventListener("click", () => { state.shown += 48; render(); });
    render().catch(() => { $("#s-count").textContent = "Search couldn't load. Please refresh the page."; });
  }

  // ---- favourites page ----
  async function renderFavs() {
    const { items, shops } = await loadCatalogue();
    const ids = getFavs(), by = new Map(items.map((p) => [p.i, p]));
    const res = ids.map((i) => by.get(i)).filter(Boolean);
    $("#results").innerHTML = res.map((p) => cardHTML(p, shops)).join("");
    $("#s-empty").hidden = res.length > 0;
    syncFavs();
  }
  if ($("#fav-page")) renderFavs();

  // ---- product gallery + lightbox ----
  const thumbs = $$(".thumbs button");
  const srcs = thumbs.map((b) => b.dataset.src);
  let cur = 0;
  const show = (i) => {
    if (!srcs.length) return;
    cur = (i + srcs.length) % srcs.length;
    const m = $("#main-img");
    m.style.opacity = 0.35;
    m.onload = () => { m.style.opacity = 1; };
    m.src = srcs[cur];
    thumbs.forEach((b, k) => b.classList.toggle("on", k === cur));
    const lb = $("#lb-img");
    if (lb) { lb.src = srcs[cur]; $("#lb-count").textContent = `${cur + 1} / ${srcs.length}`; }
  };
  thumbs.forEach((b, k) => b.addEventListener("click", () => show(k)));
  $$("[data-g-prev]").forEach((b) => b.addEventListener("click", () => show(cur - 1)));
  $$("[data-g-next]").forEach((b) => b.addEventListener("click", () => show(cur + 1)));
  const stage = $(".stage");
  if (stage) {
    let sx = 0;
    stage.addEventListener("touchstart", (e) => { sx = e.touches[0].clientX; }, { passive: true });
    stage.addEventListener("touchend", (e) => { const dx = e.changedTouches[0].clientX - sx; if (Math.abs(dx) > 40) show(cur + (dx < 0 ? 1 : -1)); });
  }
  const dlg = $("#lightbox");
  if (dlg && dlg.showModal) {
    $$("[data-open-lightbox]").forEach((b) => b.addEventListener("click", () => { show(cur); dlg.showModal(); }));
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
  const bar = $("#buybar"), buyBox = $("#buy") || $("#free-dl");
  if (bar && buyBox && "IntersectionObserver" in window) {
    bar.hidden = false;
    let seen = false;
    new IntersectionObserver(([e]) => { if (e.isIntersecting) seen = true; bar.classList.toggle("show", !e.isIntersecting && seen); }).observe(buyBox);
    bar.querySelector("[data-goto-buy]").addEventListener("click", () => {
      buyBox.scrollIntoView({ behavior: calm ? "auto" : "smooth", block: "center" });
      const em = $("#email");
      if (em) setTimeout(() => em.focus({ preventScroll: true }), calm ? 0 : 450);
    });
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
