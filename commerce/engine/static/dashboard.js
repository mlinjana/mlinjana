(() => {
  const D = window.DASH, $ = (s) => document.querySelector(s);
  const esc = (s) => String(s ?? "").replace(/[&<>"']/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c]));
  const R = (c) => "R " + ((c || 0) / 100).toLocaleString("en-ZA", { minimumFractionDigits: 2, maximumFractionDigits: 2 });
  const CHANNELS = ["own_store", "etsy", "gumroad", "payhip", "shopify"];
  const NEEDS = {
    own_store: "Live verification by the health check (automatic once deployed publicly)",
    etsy: "Etsy shop + approved Etsy API app (OAuth) — owner sign-up & identity verification",
    gumroad: "Gumroad account + access token (Settings → Advanced → Applications)",
    payhip: "Payhip account; no public listing API found — CSV-assisted manual upload",
    shopify: "Shopify plan upgrade (store is on trial) + digital downloads app",
  };
  let live = null;

  function listingMap(listings) {
    const m = {};
    for (const l of listings) (m[l.product_id] ||= {})[l.channel] = l;
    return m;
  }
  function pill(l) { return l ? `<span class="pill ${esc(l.status)}" title="${esc(l.last_error || l.url || "")}">${esc(l.status.replace(/_/g, " "))}</span>` : `<span class="pill">—</span>`; }

  function renderStatic(listings) {
    const lm = listingMap(listings);
    $("#storecards").innerHTML = D.stores.map((s) => {
      const st = live?.stores?.find((x) => x.id === s.id);
      return `<div class="card"><strong>${esc(s.name)}</strong><div class="small muted">${esc(s.tagline)}</div>
        <div class="kpi">${s.products}</div><div class="small">products on the storefront</div>
        <div class="small">Status: <span class="pill ${st?.status === "live" ? "live" : "pending_verification"}">${esc(st?.status || "staging")}</span></div>
        <div class="small"><a href="${esc(s.url)}/" target="_blank" rel="noopener">Open storefront ↗</a></div></div>`;
    }).join("");
    $("#cat tbody").innerHTML = D.catalogue.map((p) => `<tr><td>${esc(p.id)}</td><td>${esc(p.name)}<div class="small muted">${esc(p.category)}</div></td>
      <td>R${p.price_zar}<div class="small muted">US$${p.price_usd}</div></td><td>${p.valid ? '<span class="ok">✓ passed</span>' : '<span class="bad">✗ ' + esc(p.errors.join("; ")) + "</span>"}</td>
      ${CHANNELS.map((c) => `<td>${pill(lm[p.id]?.[c])}</td>`).join("")}</tr>`).join("");
    $("#queue-t tbody").innerHTML = CHANNELS.map((c) => {
      const ls = listings.filter((l) => l.channel === c);
      const n = (s) => ls.filter((l) => l.status === s).length;
      return `<tr><td>${c.replace("_", " ")}</td><td class="ok">${n("live")}</td><td class="warn">${n("pending_verification")}</td><td class="warn">${n("awaiting_authorisation")}</td><td class="bad">${n("failed")}</td><td class="small">${esc(NEEDS[c])}</td></tr>`;
    }).join("");
  }

  function md(src) { // tiny markdown renderer for the reports (headings, lists, tables, bold, italics)
    const lines = esc(src).split("\n"), out = [];
    let inList = false, table = [];
    const flushTable = () => {
      if (!table.length) return;
      const rows = table.filter((r) => !/^\|[-| ]+\|$/.test(r)).map((r) => r.split("|").slice(1, -1).map((c) => c.trim()));
      out.push("<table>" + rows.map((r, i) => "<tr>" + r.map((c) => i ? `<td>${c}</td>` : `<th>${c}</th>`).join("") + "</tr>").join("") + "</table>");
      table = [];
    };
    for (let l of lines) {
      l = l.replace(/\*\*(.+?)\*\*/g, "<strong>$1</strong>").replace(/_(.+?)_/g, "<em>$1</em>");
      if (l.startsWith("|")) { table.push(l); continue; } else flushTable();
      if (l.startsWith("- ")) { if (!inList) { out.push("<ul>"); inList = true; } out.push(`<li>${l.slice(2)}</li>`); continue; }
      if (inList) { out.push("</ul>"); inList = false; }
      const h = l.match(/^(#{1,3}) (.*)/);
      if (h) out.push(`<h${h[1].length + 1}>${h[2]}</h${h[1].length + 1}>`);
      else if (l.trim()) out.push(`<p>${l}</p>`);
    }
    flushTable(); if (inList) out.push("</ul>");
    return out.join("");
  }

  function renderLive(d) {
    live = d;
    renderStatic(d.listings || D.listings);
    const O = d.orders || [];
    const real = O.filter((o) => o.provider_mode === "live" && ["paid", "refunded"].includes(o.status));
    const sb = O.filter((o) => o.provider_mode === "sandbox" && o.status === "paid");
    const g = real.reduce((a, o) => a + (o.gross_cents || 0), 0), f = real.reduce((a, o) => a + (o.fee_cents || 0), 0), rf = O.reduce((a, o) => a + (o.refunded_cents || 0), 0);
    $("#salescards").innerHTML = [["Real paid orders", real.length], ["Gross sales", R(g)], ["Refunds", R(rf)], ["Payment fees", R(f)], ["Net proceeds", R(g - rf - f)], ["Sandbox test orders", sb.length]]
      .map(([k, v]) => `<div class="card"><div class="small muted">${k}</div><div class="kpi">${v}</div></div>`).join("");
    $("#orders tbody").innerHTML = O.slice(0, 50).map((o) => `<tr><td>${esc(o.ref)}</td><td>${esc(o.store_id)}</td><td>${esc(o.product_id)}</td><td>${esc(o.status)}</td><td>${esc(o.provider_mode)}</td><td>${o.gross_cents != null ? R(o.gross_cents) : "—"}</td><td>${o.fee_cents != null ? R(o.fee_cents) : "—"}</td><td>${o.net_cents != null ? R(o.net_cents) : "—"}</td><td class="small">${esc((o.paid_at || o.created_at || "").slice(0, 16).replace("T", " "))}</td></tr>`).join("") || `<tr><td colspan=9 class="muted">No orders yet.</td></tr>`;
    $("#jobs tbody").innerHTML = (d.jobs || []).map((j) => `<tr><td>${esc(j.job)}</td><td class="${j.status === "ok" ? "ok" : j.status === "error" ? "bad" : "warn"}">${esc(j.status)}</td><td class="small">${esc(j.started_at.slice(0, 16).replace("T", " "))}</td><td class="small">${esc(j.error || JSON.stringify(j.detail || {})).slice(0, 220)}</td></tr>`).join("") || `<tr><td colspan=4 class="muted">No job runs yet.</td></tr>`;
    $("#costs-t tbody").innerHTML = (d.costs || []).map((c) => `<tr><td>${esc(c.incurred_on)}</td><td>${esc(c.category)}</td><td>${esc(c.description)}</td><td>${esc(c.currency)} ${(c.amount_cents / 100).toFixed(2)}</td><td>${esc(c.basis)}</td></tr>`).join("") || `<tr><td colspan=5 class="muted">No costs recorded.</td></tr>`;
    const rep = (d.reports || [])[0];
    $("#report").innerHTML = rep ? `<p class="small muted">Latest: ${esc(rep.report_date)} · email: ${esc(rep.email_status)}</p>${md(rep.body_md)}<p class="small muted">Earlier: ${(d.reports || []).slice(1).map((r) => esc(r.report_date)).join(", ") || "none"}</p>` : "<p class='muted'>No reports yet.</p>";
    $("#msgs tbody").innerHTML = (d.messages || []).map((m) => `<tr><td class="small">${esc(m.received_at.slice(0, 16).replace("T", " "))}</td><td>${esc(m.store_id)}</td><td>${esc(m.email)}</td><td>${esc(m.order_ref)}</td><td>${esc(m.message)}</td><td>${esc(m.status)}</td></tr>`).join("") || `<tr><td colspan=6 class="muted">No messages.</td></tr>`;
    const attn = [];
    if (d.kill_switch?.automation || d.kill_switch?.checkout) attn.push(`<li class="bad">Kill switch on: ${esc(d.kill_switch.reason)}</li>`);
    const failed = (d.listings || []).filter((l) => l.status === "failed");
    if (failed.length) attn.push(`<li class="bad">${failed.length} failed listing(s) — see catalogue.</li>`);
    const errs = (d.jobs || []).filter((j) => j.status === "error");
    if (errs.length) attn.push(`<li class="bad">${errs.length} recent job error(s) — see automation.</li>`);
    const newMsgs = (d.messages || []).filter((m) => m.status === "new");
    if (newMsgs.length) attn.push(`<li class="warn">${newMsgs.length} new customer message(s).</li>`);
    for (const w of (d.work || []).filter((w) => ["decision_needed", "blocker"].includes(w.kind) && !w.resolved)) attn.push(`<li class="warn">${esc(w.text)}</li>`);
    if (d.payment?.mode !== "live") attn.push(`<li class="warn">Payments are in PayFast <strong>sandbox</strong> mode — no real sales possible until you connect a live PayFast account.</li>`);
    $("#attn").innerHTML = attn.join("") || `<li class="ok">Nothing needs your attention.</li>`;
  }

  async function load() {
    let key = $("#key").value.trim();
    if (!key) { try { key = localStorage.getItem("ownerKey") || ""; } catch (e) {} }
    if (!key) return;
    $("#lstatus").textContent = "Loading…";
    try {
      const r = await fetch(D.api + "/ops-api/admin/summary", { headers: { "x-admin-key": key } });
      if (r.status === 401) { $("#lstatus").textContent = "Key not accepted."; return; }
      const d = await r.json();
      try { localStorage.setItem("ownerKey", key); } catch (e) {}
      $("#lstatus").textContent = "Live data loaded " + new Date().toLocaleTimeString();
      renderLive(d);
    } catch (e) { $("#lstatus").textContent = "Could not load live data: " + e.message; }
  }
  renderStatic(D.listings);
  $("#go").addEventListener("click", load);
  load();
})();
