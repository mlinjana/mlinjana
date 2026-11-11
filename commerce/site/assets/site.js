(() => {
  const body = document.body;
  const API = body.dataset.api, STORE = body.dataset.store, PID = body.dataset.product || null;
  const $ = (s, el = document) => el.querySelector(s);
  const $$ = (s, el = document) => [...el.querySelectorAll(s)];
  const calm = matchMedia("(prefers-reduced-motion: reduce)").matches;
  const esc = (s) => String(s).replace(/[&<>"']/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" })[c]);
  const store = { // localStorage can be unavailable (private mode, blocked storage): every access is guarded
    get(k, d) { try { return JSON.parse(localStorage.getItem(k)) ?? d; } catch (e) { return d; } },
    set(k, v) { try { localStorage.setItem(k, JSON.stringify(v)); } catch (e) {} },
  };
  const beacon = (data) => { try { if (!navigator.webdriver) navigator.sendBeacon(API + "/store-api/track", JSON.stringify(data)); } catch (e) {} };

  // privacy-light analytics: no cookies, no IPs stored — page type, path, product and referrer host only
  beacon({ store: STORE, type: PID ? "product_view" : "page_view", path: location.pathname, product_id: PID, ref: document.referrer || null });

  // ---- catalogue index (lazy): used by search, favourites and the basket ----
  let catalogue = null;
  const loadCatalogue = async () => catalogue || (catalogue = await fetch("/assets/catalogue.json").then((r) => r.json()));
  const icon = {
    heart: '<svg viewBox="0 0 24 24" aria-hidden="true"><path d="M12 20.5s-7.5-4.6-9.3-9.2C1.4 7.9 3.6 4.5 7 4.5c2 0 3.4 1.1 5 3 1.6-1.9 3-3 5-3 3.4 0 5.6 3.4 4.3 6.8-1.8 4.6-9.3 9.2-9.3 9.2z"/></svg>',
    bag: '<svg viewBox="0 0 24 24" aria-hidden="true"><path d="M5 8h14l-1.2 12.1a1 1 0 0 1-1 .9H7.2a1 1 0 0 1-1-.9L5 8z"/><path d="M9 8V6a3 3 0 0 1 6 0v2"/></svg>',
    bolt: '<svg viewBox="0 0 24 24" aria-hidden="true"><path d="M13 2 4 14h7l-1 8 9-12h-7l1-8z"/></svg>',
  };
  const cardHTML = (p, shops) => {
    const s = shops[p.s] || { n: "", p: "" };
    return `<article class="card" data-id="${esc(p.i)}"><a class="card-link" href="${esc(p.u)}"><div class="card-media"><img src="${esc(p.img)}" alt="${esc(p.n)}" loading="lazy" width="600" height="450">` +
      (p.o ? `<span class="badge-off">-${p.o}%</span>` : "") + (p.fr ? `<span class="badge-free">Free</span>` : "") + `</div><div class="card-body">` +
      `<p class="card-shop">${esc(p.c)}</p><h3 class="card-title">${esc(p.n)}</h3>` +
      `<p class="card-meta">${icon.bolt}Instant download · ${esc(p.f.join(", "))}</p></div></a>` +
      `<div class="card-foot"><p class="card-price">${p.fr ? "<strong>Free</strong>" : `<strong>R${p.p}</strong>` + (p.o ? `<s>R${p.b}</s>` : "")}</p>` +
      (p.fr ? "" : `<button type="button" class="add" data-add="${esc(p.i)}" aria-label="Add ${esc(p.n)} to basket">${icon.bag}<span>Add</span></button>`) + `</div>` +
      `<button type="button" class="fav" data-fav="${esc(p.i)}" aria-pressed="false" aria-label="Save ${esc(p.n)} to favourites">${icon.heart}</button></article>`;
  };

  // ---- toast ----
  let toastTimer = 0;
  const toast = (html, action) => {
    const t = $("#toast");
    if (!t) return;
    t.innerHTML = html + (action ? ` <button type="button">${action[0]}</button>` : "");
    if (action) t.querySelector("button").onclick = () => { t.hidden = true; action[1](); };
    t.hidden = false;
    clearTimeout(toastTimer);
    toastTimer = setTimeout(() => { t.hidden = true; }, 4200);
  };
  const bump = (sel) => $$(sel).forEach((el) => { const b = el.closest(".hbtn"); if (b && !calm) { b.classList.remove("bump"); void b.offsetWidth; b.classList.add("bump"); } });

  // ---- favourites: kept in this browser only, never sent anywhere ----
  const FKEY = "mls:favs";
  const syncFavs = () => {
    const f = new Set(store.get(FKEY, []));
    $$("[data-fav]").forEach((b) => {
      const on = f.has(b.dataset.fav);
      b.setAttribute("aria-pressed", on ? "true" : "false");
      const t = b.querySelector("span");
      if (t) t.textContent = on ? "Saved to favourites" : "Save to favourites";
    });
    $$(".fav-count").forEach((c) => { c.hidden = !f.size; c.textContent = f.size; });
  };

  // ---- basket: entries "ID" (Standard licence) or "ID:team" (Team licence) in this browser; one entry per product.
  // Prices shown here use the same rule as store-api (Team = 2.5x, nearest whole rand); only the server's price is charged.
  const BKEY = "mls:basket";
  const idOf = (e) => e.split(":")[0];
  const licOf = (e) => (e.endsWith(":team") ? "team" : "standard");
  const entry = (id, lic) => (lic === "team" ? `${id}:team` : id);
  const tierPrice = (price, lic) => (lic === "team" ? Math.round(price * 2.5) : price);
  const LIC_LABEL = { standard: "Standard licence", team: "Team licence (up to 10 people)" };
  const chosenLicence = () => { const r = document.querySelector("input[name=licence]:checked"); return r && r.value === "team" ? "team" : "standard"; };
  const getBasket = () => store.get(BKEY, []).filter((x) => typeof x === "string" && /^[A-Z]{2,5}-\d{3,4}(:team)?$/.test(x)).slice(0, 25);
  const setBasket = (a) => {
    const m = new Map();
    a.forEach((e) => { m.delete(idOf(e)); m.set(idOf(e), e); }); // the latest licence choice for a product wins
    store.set(BKEY, [...m.values()].slice(0, 25)); syncBasket();
  };
  const syncBasket = () => {
    const b = getBasket().map(idOf);
    $$(".bk-count").forEach((c) => { c.hidden = !b.length; c.textContent = b.length; });
    $$("[data-add]").forEach((el) => { if (el.classList.contains("add")) el.classList.toggle("in", b.includes(el.dataset.add)); });
  };
  const dlg = $("#basket");
  const renderBasket = async () => {
    const ids = getBasket();
    $("#bk-empty").hidden = ids.length > 0;
    $("#bk-foot").hidden = !ids.length;
    if (!ids.length) { $("#bk-items").innerHTML = ""; return; }
    const { items, shops } = await loadCatalogue();
    const by = new Map(items.map((p) => [p.i, p]));
    const rows = ids.map((e) => ({ e, lic: licOf(e), p: by.get(idOf(e)) })).filter((r) => r.p);
    if (rows.length !== ids.length) setBasket(rows.map((r) => r.e)); // drop items that no longer exist
    rows.forEach((r) => { r.price = tierPrice(r.p.p, r.lic); });
    $("#bk-items").innerHTML = rows.map(({ e, lic, p, price }) => `<div class="bk-item"><img src="${esc(p.img)}" alt="" width="600" height="450"><div><a href="${esc(p.u)}">${esc(p.n)}</a>` +
      `<small>${esc(LIC_LABEL[lic])} · ${esc(p.f.join(", "))}</small></div>` +
      `<div class="bk-p">R${price}<button type="button" class="bk-rm" data-rm="${esc(e)}" aria-label="Remove ${esc(p.n)}">Remove</button></div></div>`).join("");
    const total = rows.reduce((a, r) => a + r.price, 0);
    $("#bk-total").textContent = "R" + total;
    if ($("#bk-form")) $("#bk-form button").querySelector("span").textContent = `Checkout securely · R${total}`;
  };
  const openBasket = async (focusEmail) => {
    if (!dlg) return;
    await renderBasket().catch(() => {});
    if (!dlg.open) dlg.showModal ? dlg.showModal() : dlg.setAttribute("open", "");
    if (focusEmail && $("#bk-email") && getBasket().length) setTimeout(() => $("#bk-email").focus(), calm ? 0 : 250);
  };
  if (dlg) {
    dlg.addEventListener("click", (e) => { if (e.target === dlg || e.target.closest("[data-close-basket]")) dlg.close(); });
    $("#bk-items").addEventListener("click", (e) => {
      const r = e.target.closest("[data-rm]");
      if (r) { setBasket(getBasket().filter((i) => i !== r.dataset.rm)); renderBasket(); }
    });
    $("#bk-form")?.addEventListener("submit", async (e) => {
      e.preventDefault();
      const msg = $("#bk-msg"), btn = $("#bk-form button"), email = $("#bk-email").value.trim(), ids = getBasket();
      msg.className = "msg";
      if (!/^[^\s@]+@[^\s@]+\.[^\s@]{2,}$/.test(email)) { msg.textContent = "Please enter a valid email address."; msg.className = "msg err"; return; }
      btn.disabled = true; msg.textContent = "Starting secure checkout…";
      ids.forEach((i) => beacon({ store: STORE, type: "checkout_start", product_id: idOf(i), path: location.pathname }));
      try {
        const one = ids.length === 1;
        const r = await fetch(API + (one ? "/store-api/checkout" : "/store-api/basket-checkout"), { method: "POST", headers: { "Content-Type": "application/json" },
          body: JSON.stringify(one ? { product_id: idOf(ids[0]), licence: licOf(ids[0]), email } : { items: ids, email }) });
        const d = await r.json();
        if (!r.ok) {
          if (d.unavailable) { setBasket(ids.filter((i) => !d.unavailable.includes(idOf(i)))); renderBasket(); }
          throw new Error(r.status === 503 ? "Online checkout opens soon. Your basket is saved on this device, so please check back shortly." : (d.error || "Checkout failed"));
        }
        const f = document.createElement("form");
        f.method = "POST"; f.action = d.action;
        for (const [k, v] of Object.entries(d.fields)) { const i = document.createElement("input"); i.type = "hidden"; i.name = k; i.value = v; f.appendChild(i); }
        document.body.appendChild(f);
        f.submit();
      } catch (err) { msg.textContent = err.message; msg.className = "msg err"; btn.disabled = false; }
    });
  }
  $$("[data-open-basket]").forEach((b) => b.addEventListener("click", () => openBasket(false)));

  document.addEventListener("click", (e) => {
    const f = e.target.closest("[data-fav]");
    if (f) {
      e.preventDefault();
      const id = f.dataset.fav, list = store.get(FKEY, []), i = list.indexOf(id);
      i >= 0 ? list.splice(i, 1) : list.unshift(id);
      store.set(FKEY, list.slice(0, 500));
      syncFavs();
      if (!calm) { f.classList.remove("pop"); void f.offsetWidth; f.classList.add("pop"); }
      if (i < 0) { bump(".fav-count"); toast("Saved to favourites.", ["View", () => { location.href = "/favourites"; }]); }
      if ($("#fav-page") && i >= 0) renderFavs();
      return;
    }
    const a = e.target.closest("[data-add]");
    if (a) {
      e.preventDefault();
      const id = a.dataset.add, b = getBasket();
      const e2 = entry(id, id === PID ? chosenLicence() : "standard"), had = b.includes(e2);
      if (!had) setBasket([...b, e2]); // replaces the same product with another licence
      if (!calm) { a.classList.remove("pop"); void a.offsetWidth; a.classList.add("pop"); }
      bump(".bk-count");
      if (a.hasAttribute("data-open")) openBasket(true);
      else toast(had ? "Already in your basket." : "Added to your basket.", ["View basket", () => openBasket(true)]);
    }
  });
  syncFavs();
  syncBasket();
  const qs = new URLSearchParams(location.search);
  if (qs.get("basket") === "cancelled" || qs.get("cancelled")) {
    if (qs.get("cancelled") && PID && !getBasket().map(idOf).includes(PID)) setBasket([...getBasket(), entry(PID, qs.get("licence"))]);
    toast("Payment cancelled. You haven't been charged, and your basket is saved.", ["View basket", () => openBasket(true)]);
  }

  // ---- mega menu ----
  const mb = $(".mega-btn"), mp = $("#mega-panel");
  if (mb && mp) {
    const set = (open) => { mp.hidden = !open; mb.setAttribute("aria-expanded", open ? "true" : "false"); };
    mb.addEventListener("click", (e) => { e.stopPropagation(); set(mp.hidden); });
    document.addEventListener("click", (e) => { if (!mp.hidden && !e.target.closest(".mega")) set(false); });
    document.addEventListener("keydown", (e) => { if (e.key === "Escape" && !mp.hidden) { set(false); mb.focus(); } });
  }
  // ---- licence choice on the product page (Standard / Team); the price shown follows the choice ----
  const licRadios = $$("input[name=licence]");
  if (licRadios.length) {
    if (qs.get("licence") === "team") licRadios.forEach((r) => { r.checked = r.value === "team"; });
    const showPrice = () => {
      const r = licRadios.find((x) => x.checked);
      if (!r) return;
      const amt = $("#pp-amount"); if (amt) amt.textContent = "R" + r.dataset.price;
      $$(".bb-amount").forEach((x) => { x.textContent = "R" + r.dataset.price; });
    };
    licRadios.forEach((r) => r.addEventListener("change", showPrice));
    showPrice();
  }

  // keep the header "Search in" picker in step with the search page
  const hd = $("#hdiv");
  if (hd && qs.get("div")) hd.value = qs.get("div");

  // ---- product rails: arrow buttons appear only when there is more to scroll ----
  $$("[data-rail]").forEach((r) => {
    const t = $(".rail-track", r), prev = $(".rail-btn.prev", r), next = $(".rail-btn.next", r);
    const upd = () => { prev.hidden = t.scrollLeft < 8; next.hidden = t.scrollLeft + t.clientWidth >= t.scrollWidth - 8; };
    prev.addEventListener("click", () => t.scrollBy({ left: -t.clientWidth * 0.9, behavior: calm ? "auto" : "smooth" }));
    next.addEventListener("click", () => t.scrollBy({ left: t.clientWidth * 0.9, behavior: calm ? "auto" : "smooth" }));
    t.addEventListener("scroll", upd, { passive: true });
    addEventListener("resize", upd);
    upd();
  });

  // ---- filters on shop and department pages ----
  const grid = $("#shop .grid");
  if (grid && $("#q")) {
    const cards = $$(".card", grid);
    cards.forEach((c, k) => { c.dataset.k = k; });
    const facet = ($(".filters") || {}).dataset?.facet || "cat"; // chips filter on data-cat or data-cat2
    let cat = "";
    const apply = () => {
      const t = ($("#q").value || "").toLowerCase().trim().split(/\s+/).filter(Boolean);
      const fmt = $("#f-fmt").value, max = +$("#f-price").value || 0, sort = $("#f-sort").value;
      let n = 0;
      cards.forEach((c) => {
        const show = (!cat || c.dataset[facet] === cat) && (!fmt || c.dataset.fmt.split(" ").includes(fmt)) &&
          (!max || +c.dataset.price < max) && t.every((w) => c.dataset.text.includes(w));
        c.hidden = !show;
        if (show) n++;
      });
      const order = [...cards].sort((a, b) => sort === "lo" ? a.dataset.price - b.dataset.price : sort === "hi" ? b.dataset.price - a.dataset.price : a.dataset.k - b.dataset.k);
      order.forEach((c) => grid.appendChild(c));
      $("#empty").hidden = n > 0;
      $("#count").textContent = `Showing ${n} ${n === 1 ? "item" : "items"}`;
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
    const state = { q: (qs.get("q") || "").trim(), div: qs.get("div") || "", dept: qs.get("dept") || "", max: qs.get("max") || "", fmt: qs.get("fmt") || "",
      bundles: qs.get("bundles") === "1", free: qs.get("free") === "1", sort: qs.get("sort") || "", shown: 48 };
    $("#hq").value = state.q;
    const setRadio = (name, v) => { const el = sp.querySelector(`input[name=${name}][value="${v}"]`); if (el) el.checked = true; };
    setRadio("div", state.div); setRadio("max", state.max); setRadio("fmt", state.fmt);
    sp.querySelector("input[name=bundles]").checked = state.bundles;
    sp.querySelector("input[name=free]").checked = state.free;
    $("#s-sort").value = state.sort;
    const stem = (w) => (w.length > 3 && w.endsWith("s") ? w.slice(0, -1) : w);
    const render = async () => {
      const { items, shops } = await loadCatalogue();
      const words = state.q.toLowerCase().split(/[^a-z0-9]+/).filter((w) => w.length > 1).map(stem);
      let res = items.filter((p) => (!state.div || p.v === state.div) && (!state.dept || p.d === state.dept) && (!state.max || p.p < +state.max) && (!state.fmt || p.f.includes(state.fmt)) &&
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
      $("#s-title").textContent = state.q ? `Results for “${state.q}”` : state.bundles ? "Bundle deals" : state.max ? `Under R${state.max}` : "All downloads";
      $("#s-count").textContent = `${res.length} ${res.length === 1 ? "item" : "items"}` + (loose ? " matching some of your words" : "");
      $("#results").innerHTML = res.slice(0, state.shown).map((p) => cardHTML(p, shops)).join("");
      $("#s-empty").hidden = res.length > 0;
      $("#s-more").hidden = res.length <= state.shown;
      syncFavs(); syncBasket();
    };
    const push = () => {
      const u = new URLSearchParams();
      if (state.q) u.set("q", state.q);
      ["div", "dept", "max", "fmt", "sort"].forEach((k) => state[k] && u.set(k, state[k]));
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
      else return;
      push();
    });
    $("#s-more").addEventListener("click", () => { state.shown += 48; render(); });
    render().catch(() => { $("#s-count").textContent = "Search couldn't load. Please refresh the page."; });
  }

  // ---- favourites page ----
  async function renderFavs() {
    const { items, shops } = await loadCatalogue();
    const by = new Map(items.map((p) => [p.i, p]));
    const res = store.get(FKEY, []).map((i) => by.get(i)).filter(Boolean);
    $("#results").innerHTML = res.map((p) => cardHTML(p, shops)).join("");
    $("#s-empty").hidden = res.length > 0;
    syncFavs(); syncBasket();
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
  const lbx = $("#lightbox");
  if (lbx && lbx.showModal) {
    const zoom = $("#lb-zoom"), viewport = $(".lb-viewport", lbx);
    const resetZoom = () => { lbx.classList.remove("zoomed"); zoom.setAttribute("aria-pressed", "false"); zoom.textContent = "Zoom in"; viewport.scrollTop = viewport.scrollLeft = 0; };
    zoom.addEventListener("click", () => { const on = lbx.classList.toggle("zoomed"); zoom.setAttribute("aria-pressed", String(on)); zoom.textContent = on ? "Fit image" : "Zoom in"; });
    lbx.addEventListener("close", resetZoom);
    $$("[data-open-lightbox]").forEach((b) => b.addEventListener("click", () => { show(cur); lbx.showModal(); }));
    lbx.querySelector("[data-lb-close]").addEventListener("click", () => lbx.close());
    lbx.querySelector("[data-lb-prev]").addEventListener("click", () => show(cur - 1));
    lbx.querySelector("[data-lb-next]").addEventListener("click", () => show(cur + 1));
    lbx.addEventListener("click", (e) => { if (e.target === lbx) lbx.close(); });
    lbx.addEventListener("keydown", (e) => { if (e.key === "ArrowLeft") show(cur - 1); if (e.key === "ArrowRight") show(cur + 1); });
  }

  // ---- sticky buy bar on phones: visible while the buy box is off screen ----
  const bar = $("#buybar"), buyBox = $("#buy") || $("#free-dl");
  if (bar && buyBox && "IntersectionObserver" in window) {
    bar.hidden = false;
    let seen = false;
    new IntersectionObserver(([e]) => { if (e.isIntersecting) seen = true; bar.classList.toggle("show", !e.isIntersecting && seen); }).observe(buyBox);
  }

  // ---- thank-you page: wait for PayFast's confirmation, then show the downloads (single order or basket) ----
  const st = $("#order-status");
  if (st) {
    const ref = qs.get("ref"), k = qs.get("k");
    if (!ref || !k) { st.textContent = "We couldn't find your order details in this link."; return; }
    $("#order-ref").textContent = ref;
    const isBasket = ref.startsWith("BSK-");
    let tries = 0;
    const poll = async () => {
      tries++;
      try {
        const r = await fetch(`${API}/store-api/${isBasket ? "basket" : "order"}?ref=${encodeURIComponent(ref)}&k=${encodeURIComponent(k)}`);
        const d = await r.json();
        const items = isBasket ? (d.items || []) : (d.download ? [{ name: "Your files", licence: d.licence, download: d.download, expires_at: d.expires_at, downloads_left: d.downloads_left }] : []);
        if (d.status === "paid" && items.length && items.every((x) => x.download)) {
          setBasket([]);
          st.innerHTML = `<p><strong>Payment confirmed.</strong> ${items.length > 1 ? "Your downloads are" : "Your download is"} ready.</p><ul class="dl-list">` +
            items.map((x) => `<li><span>${esc(x.name)}<small>${esc(LIC_LABEL[x.licence === "team" ? "team" : "standard"])}</small></span><a class="btn btn-primary inline" href="${esc(x.download)}">Download ZIP</a></li>`).join("") + `</ul>` +
            `<p class="small muted">Links valid until ${new Date(items[0].expires_at).toLocaleDateString()} · ${items[0].downloads_left} downloads left each. Bookmark this page to download again.</p>` +
            (d.mode === "sandbox" ? `<p class="small muted">Test-mode order (PayFast sandbox): no real payment was taken.</p>` : "");
          return;
        }
        if (["cancelled", "failed", "expired"].includes(d.status)) { st.innerHTML = `<p>This payment was <strong>${esc(d.status)}</strong>. You have not been charged.</p>`; return; }
        st.innerHTML = `<p>Waiting for payment confirmation from PayFast… (this usually takes a few seconds)</p>`;
      } catch (e) { st.textContent = "Checking your order…"; }
      if (tries < 60) setTimeout(poll, tries < 10 ? 3000 : 10000);
      else st.innerHTML = "<p>We haven't received confirmation yet. If you were charged, please contact us with your order number. We'll sort it out.</p>";
    };
    poll();
  }

  // ---- contact form ----
  const cf = $("#contact");
  if (cf && qs.get("topic") === "licence" && !$("#c-msg").value) {
    const pid = (qs.get("product") || "").replace(/[^A-Z0-9-]/g, "").slice(0, 12);
    const ask = (name) => { $("#c-msg").value = `I'd like a quote for a commercial or enterprise licence${name ? ` for ${name} (${pid})` : ""}.\n\nHow we plan to use it (how many people, which organisations, or which products we'd sell):\n`; };
    ask("");
    if (pid) loadCatalogue().then(({ items }) => { const p = items.find((x) => x.i === pid); if (p) ask(p.n); }).catch(() => {});
  }
  if (cf) cf.addEventListener("submit", async (e) => {
    e.preventDefault();
    const m = $("#contact-msg");
    const data = Object.fromEntries(new FormData(cf));
    data.store = STORE;
    const r = await fetch(API + "/store-api/contact", { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(data) }).catch(() => null);
    const d = r ? await r.json() : { error: "Network error" };
    m.textContent = r && r.ok ? "Thanks. We've received your message and will reply by email." : (d.error || "Something went wrong.");
    m.className = r && r.ok ? "msg" : "msg err";
    if (r && r.ok) cf.reset();
  });
})();

// ---- 2.1 motion: header shadow, reveal on scroll, count-up, hero parallax, fly-to-basket. Skipped for reduced motion. ----
(() => {
  const calm = matchMedia("(prefers-reduced-motion: reduce)").matches;
  const hdr = document.querySelector(".hdr");
  if (hdr) { const f = () => hdr.classList.toggle("scrolled", scrollY > 8); f(); addEventListener("scroll", f, { passive: true }); }
  if (calm || !("IntersectionObserver" in window)) return;

  const io = new IntersectionObserver((es) => es.forEach((e) => {
    if (!e.isIntersecting) return;
    const el = e.target; io.unobserve(el); el.classList.add("in");
    setTimeout(() => { el.classList.remove("rv", "in"); el.style.transitionDelay = ""; }, 1300); // hand hover transitions back
  }), { rootMargin: "0px 0px -8% 0px" });
  document.querySelectorAll(".home .sec-head,.home .div-card,.home .usp,.home .rail-sec,.how .steps li,.home .why,.home .cta").forEach((el) => {
    if (el.getBoundingClientRect().top < innerHeight * 0.92) return;
    if (el.matches(".div-card,.steps li")) el.style.transitionDelay = [...el.parentNode.children].indexOf(el) * 90 + "ms";
    el.classList.add("rv"); io.observe(el);
  });

  document.querySelectorAll("[data-count]").forEach((el) => {
    const n = +el.dataset.count, pre = el.dataset.prefix || "";
    if (!(n > 9)) return;
    const t0 = performance.now();
    const step = (t) => { const k = Math.min(1, (t - t0) / 1400); el.textContent = pre + Math.round(n * (1 - Math.pow(1 - k, 3))); if (k < 1) requestAnimationFrame(step); };
    requestAnimationFrame(step);
  });

  const hero = document.querySelector(".hero2"), art = document.querySelector(".hero2-art"), glow = document.querySelector(".hero2-glow");
  if (hero && art && matchMedia("(hover:hover) and (pointer:fine)").matches) {
    let raf = 0;
    hero.addEventListener("pointermove", (e) => {
      if (raf) return;
      raf = requestAnimationFrame(() => {
        raf = 0;
        const r = hero.getBoundingClientRect(), x = (e.clientX - r.left) / r.width - 0.5, y = (e.clientY - r.top) / r.height - 0.5;
        art.style.setProperty("--mx", (-x * 24).toFixed(1) + "px"); art.style.setProperty("--my", (-y * 18).toFixed(1) + "px");
        if (glow) { glow.style.setProperty("--gx", (e.clientX - r.left).toFixed(0) + "px"); glow.style.setProperty("--gy", (e.clientY - r.top).toFixed(0) + "px"); }
      });
    });
  }

  document.addEventListener("click", (e) => {
    const a = e.target.closest(".card [data-add]"), bag = document.querySelector("[data-open-basket]");
    const img = a && a.closest(".card").querySelector(".card-media img");
    if (!img || !bag || !img.animate) return;
    const s = img.getBoundingClientRect(), d = bag.getBoundingClientRect(), c = img.cloneNode();
    Object.assign(c.style, { position: "fixed", left: s.left + "px", top: s.top + "px", width: s.width + "px", height: s.height + "px", zIndex: 80, borderRadius: "12px", pointerEvents: "none", objectFit: "cover", boxShadow: "0 12px 30px rgba(0,0,0,.3)" });
    c.removeAttribute("loading"); c.alt = "";
    document.body.appendChild(c);
    c.animate([{ transform: "none", opacity: 1 }, { transform: `translate(${d.left + d.width / 2 - s.left - s.width / 2}px,${d.top + d.height / 2 - s.top - s.height / 2}px) scale(.08)`, opacity: 0.25 }],
      { duration: 650, easing: "cubic-bezier(.5,0,.3,1)" }).onfinish = () => c.remove();
  });
})();
