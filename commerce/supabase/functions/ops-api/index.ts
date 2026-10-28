// Operations API: scheduled jobs (pg_cron → here), daily owner report, admin dashboard data, catalogue sync & file upload.
// Auth: cron/sync/upload use secrets stored in the private config table; admin uses an owner key (SHA-256 hash in config).
import { createClient } from "jsr:@supabase/supabase-js@2";

const db = createClient(Deno.env.get("SUPABASE_URL")!, Deno.env.get("SUPABASE_SERVICE_ROLE_KEY")!, { auth: { persistSession: false } });
const CORS = { "Access-Control-Allow-Origin": "*", "Access-Control-Allow-Headers": "content-type, x-admin-key", "Access-Control-Allow-Methods": "GET, POST, PUT, OPTIONS" };
const json = (b: unknown, s = 200) => new Response(JSON.stringify(b), { status: s, headers: { ...CORS, "Content-Type": "application/json" } });
const TZ = "Africa/Johannesburg";
const money = (c: number) => "R " + (c / 100).toLocaleString("en-ZA", { minimumFractionDigits: 2, maximumFractionDigits: 2 });

async function cfg(key: string) {
  const { data } = await db.from("config").select("value").eq("key", key).maybeSingle();
  return data?.value;
}
async function sha256(s: string) {
  const b = await crypto.subtle.digest("SHA-256", new TextEncoder().encode(s));
  return [...new Uint8Array(b)].map((x) => x.toString(16).padStart(2, "0")).join("");
}
function safeEq(a: string, b: string) {
  if (!a || !b || a.length !== b.length) return false;
  let r = 0;
  for (let i = 0; i < a.length; i++) r |= a.charCodeAt(i) ^ b.charCodeAt(i);
  return r === 0;
}
async function secretOk(req: Request, key: "cron_secret" | "upload_secret") {
  return safeEq(req.headers.get("x-secret") ?? "", (await cfg(key)) ?? "");
}
async function adminOk(req: Request) {
  const h = await cfg("admin_key_sha256");
  const k = req.headers.get("x-admin-key") ?? "";
  return !!h && k.length >= 24 && safeEq(await sha256(k), h);
}
function today() {
  return new Intl.DateTimeFormat("en-CA", { timeZone: TZ }).format(new Date()); // YYYY-MM-DD
}
function dayStartUtc(d: string) {
  return new Date(`${d}T00:00:00+02:00`).toISOString(); // SAST has no DST
}

async function jobStart(job: string) {
  const kill = await cfg("kill_switch");
  if (kill?.automation && job !== "daily_report") {
    await db.from("job_runs").insert({ job, status: "skipped", finished_at: new Date().toISOString(), detail: { reason: "automation kill switch on" } });
    return null;
  }
  const b = await cfg("budgets");
  const max = b?.max_jobs_per_day?.[job] ?? 24;
  const { count } = await db.from("job_runs").select("id", { count: "exact", head: true }).eq("job", job).gte("started_at", dayStartUtc(today()));
  if ((count ?? 0) >= max) return null; // frequency cap
  const { data } = await db.from("job_runs").insert({ job }).select("id").single();
  return data!.id as number;
}
async function jobEnd(id: number, status: "ok" | "error", detail: unknown, error?: string) {
  await db.from("job_runs").update({ status, detail, error: error ?? null, finished_at: new Date().toISOString() }).eq("id", id);
  if (status === "error") {
    // repeated-error threshold → pause automation
    const b = await cfg("budgets");
    const { data } = await db.from("job_runs").select("status").order("started_at", { ascending: false }).limit(b?.max_error_streak ?? 5);
    if (data && data.length >= (b?.max_error_streak ?? 5) && data.every((r) => r.status === "error")) {
      await db.from("config").update({ value: { checkout: false, automation: true, reason: "repeated job errors — check job_runs" } }).eq("key", "kill_switch");
    }
  }
}

// ------------------------------------------------------------------ health / maintenance job
async function health() {
  const id = await jobStart("health");
  if (!id) return { skipped: true };
  const out: Record<string, unknown> = {};
  try {
    // expire abandoned checkouts
    const cutoff = new Date(Date.now() - 6 * 3600_000).toISOString();
    const { data: exp } = await db.from("orders").update({ status: "expired" }).eq("status", "pending").lt("created_at", cutoff).select("ref");
    out.expired_orders = exp?.length ?? 0;
    // paid orders without a download token (delivery check)
    const { data: paid } = await db.from("orders").select("id,ref").eq("status", "paid");
    const missing: string[] = [];
    for (const o of paid ?? []) {
      const { count } = await db.from("download_tokens").select("token", { count: "exact", head: true }).eq("order_id", o.id);
      if (!count) missing.push(o.ref);
    }
    out.paid_without_delivery = missing;
    // storefront + listing link checks (own store pages and any marketplace URLs we hold)
    const { data: stores } = await db.from("stores").select("id,url");
    const storeRes: Record<string, number> = {};
    for (const s of stores ?? []) if (s.url) storeRes[s.id] = await fetch(s.url, { redirect: "follow" }).then((r) => r.status).catch(() => 0);
    out.stores = storeRes;
    const { data: lst } = await db.from("listings").select("id,url,status,channel").not("url", "is", null).in("status", ["live", "pending_verification", "failed"]);
    let ok = 0, bad = 0;
    for (const l of lst ?? []) {
      const code = await fetch(l.url, { method: "GET", redirect: "follow" }).then((r) => r.status).catch(() => 0);
      const good = code >= 200 && code < 400;
      good ? ok++ : bad++;
      await db.from("listings").update({ status: good ? "live" : "failed", last_checked_at: new Date().toISOString(), last_error: good ? null : `HTTP ${code}` }).eq("id", l.id);
    }
    out.listings_checked = { ok, bad };
    // weekly budget check
    const b = await cfg("budgets");
    const { data: wk } = await db.rpc("weekly_costs_usd");
    out.weekly_costs_usd = wk;
    if (typeof wk === "number" && b && wk > (b.weekly_ai_usd + b.weekly_infra_usd)) {
      out.budget = "exceeded";
      await db.from("work_log").insert({ kind: "decision_needed", text: `Weekly recorded costs (US$${wk}) exceed the configured budget. Automated generation is paused.` });
      await db.from("config").update({ value: { checkout: false, automation: true, reason: "weekly budget exceeded" } }).eq("key", "kill_switch");
    }
    await jobEnd(id, "ok", out);
  } catch (e) {
    await jobEnd(id, "error", out, String(e));
  }
  return out;
}

// ------------------------------------------------------------------ daily report
async function buildReport(day: string) {
  const start = dayStartUtc(day);
  const end = new Date(new Date(start).getTime() + 86400_000).toISOString();
  const [{ data: stores }, { data: products }, { data: listings }, { data: orders }, { data: events }, { data: jobs }, { data: work }, { data: costs }, { data: msgs }] =
    await Promise.all([
      db.from("stores").select("*").order("id"),
      db.from("products").select("id,store_id,status,active"),
      db.from("listings").select("product_id,channel,status,url,last_error"),
      db.from("orders").select("store_id,status,gross_cents,fee_cents,net_cents,refunded_cents,paid_at,provider_mode,created_at"),
      db.from("events").select("store_id,type,product_id").gte("ts", start).lt("ts", end),
      db.from("job_runs").select("job,status,error,started_at").gte("started_at", new Date(Date.now() - 86400_000).toISOString()),
      db.from("work_log").select("kind,text,logged_on,resolved").or(`logged_on.eq.${day},and(kind.in.(decision_needed,blocker),resolved.eq.false)`),
      db.from("costs").select("incurred_on,category,description,amount_cents,currency,basis").gte("incurred_on", new Date(Date.now() - 7 * 86400_000).toISOString().slice(0, 10)),
      db.from("contact_messages").select("id").eq("status", "new"),
    ]);
  const P = products ?? [], L = listings ?? [], O = orders ?? [], E = events ?? [];
  const live = (l: any) => l.status === "live";
  const sum = {
    stores_created: stores?.length ?? 0,
    stores_live: (stores ?? []).filter((s: any) => s.status === "live").length,
    stores_staging: (stores ?? []).filter((s: any) => s.status === "staging").length,
    products_generated: P.length,
    products_validated: P.filter((p: any) => p.status === "validated").length,
    products_published_any_channel: new Set(L.filter(live).map((l: any) => l.product_id)).size,
    listings_live: L.filter(live).length,
    listings_failed: L.filter((l: any) => l.status === "failed").length,
    listings_awaiting_authorisation: L.filter((l: any) => l.status === "awaiting_authorisation").length,
    new_contact_messages: msgs?.length ?? 0,
  };
  const paidToday = O.filter((o: any) => o.status === "paid" && o.paid_at >= start && o.paid_at < end);
  const lines: string[] = [];
  lines.push(`# Daily report — ${day}`, "", `_Generated ${new Date().toLocaleString("en-ZA", { timeZone: TZ })} SAST from live database records. Nothing in this report is estimated unless marked._`, "");
  lines.push("## Business overview", "",
    `| Measure | Value |`, `|---|---|`,
    `| Stores built | ${sum.stores_created} |`, `| Stores live (verified public & taking real payments) | ${sum.stores_live} |`,
    `| Stores in staging (sandbox payments) | ${sum.stores_staging} |`,
    `| Products generated | ${sum.products_generated} |`, `| Products validated | ${sum.products_validated} |`,
    `| Products published (≥1 verified live listing) | ${sum.products_published_any_channel} |`,
    `| Failed listings | ${sum.listings_failed} |`, `| Listings awaiting your authorisation | ${sum.listings_awaiting_authorisation} |`,
    `| New customer messages | ${sum.new_contact_messages} |`, "");
  lines.push("## Stores", "");
  for (const s of stores ?? []) {
    const so = O.filter((o: any) => o.store_id === s.id);
    const realPaid = so.filter((o: any) => o.status === "paid" && o.provider_mode === "live");
    const sandboxPaid = so.filter((o: any) => o.status === "paid" && o.provider_mode === "sandbox");
    const gross = realPaid.reduce((a: number, o: any) => a + (o.gross_cents ?? 0), 0);
    const fees = realPaid.reduce((a: number, o: any) => a + (o.fee_cents ?? 0), 0);
    const refunds = so.reduce((a: number, o: any) => a + (o.refunded_cents ?? 0), 0);
    const views = E.filter((e: any) => e.store_id === s.id && e.type === "page_view").length;
    const pviews = E.filter((e: any) => e.store_id === s.id && e.type === "product_view").length;
    const todayPaid = paidToday.filter((o: any) => o.store_id === s.id && o.provider_mode === "live").length;
    const sp = P.filter((p: any) => p.store_id === s.id);
    const sl = L.filter((l: any) => sp.some((p: any) => p.id === l.product_id));
    lines.push(`### ${s.name} — ${s.status}`, `- URL: ${s.url ?? "not deployed"}`,
      `- Products: ${sp.length} created, ${sp.filter((p: any) => p.status === "validated").length} validated, ${new Set(sl.filter(live).map((l: any) => l.product_id)).size} with a verified live listing`,
      `- Real orders (all time): ${realPaid.length} · today: ${todayPaid} · sandbox test orders: ${sandboxPaid.length}`,
      `- Gross sales ${money(gross)} · refunds ${money(refunds)} · payment fees ${money(fees)} · net ${money(gross - refunds - fees)}`,
      `- Today: ${views} page views, ${pviews} product views, conversion ${pviews ? ((todayPaid / pviews) * 100).toFixed(1) + "%" : "n/a (no product views)"}`,
      `- Problems: ${sl.filter((l: any) => l.status === "failed").map((l: any) => `${l.product_id}/${l.channel}: ${l.last_error}`).join("; ") || "none detected"}`, "");
  }
  const W = work ?? [];
  const list = (k: string, filt = (w: any) => w.logged_on === day) => W.filter((w: any) => w.kind === k && filt(w)).map((w: any) => `- ${w.text}`);
  lines.push("## Progress", "", "**Done today**", ...(list("done").length ? list("done") : ["- (nothing logged)"]), "",
    "**Planned next**", ...(list("planned").length ? list("planned") : ["- (nothing logged)"]), "");
  const J = jobs ?? [];
  lines.push("## Automation health (last 24 h)", "",
    `- Job runs: ${J.length} · ok ${J.filter((j: any) => j.status === "ok").length} · errors ${J.filter((j: any) => j.status === "error").length} · skipped ${J.filter((j: any) => j.status === "skipped").length}`,
    ...J.filter((j: any) => j.status === "error").slice(0, 5).map((j: any) => `- ⚠ ${j.job}: ${j.error}`));
  const kill = await cfg("kill_switch");
  if (kill?.automation || kill?.checkout) lines.push(`- ⚠ Kill switch active: ${kill.reason}`);
  lines.push("", "## Costs (last 7 days, recorded entries)", "");
  const C = costs ?? [];
  if (!C.length) lines.push("- No cost entries recorded.");
  for (const c of C) lines.push(`- ${c.incurred_on} · ${c.category} · ${c.description}: ${c.currency} ${(c.amount_cents / 100).toFixed(2)} (${c.basis})`);
  lines.push("", "## Needs your decision or action", "",
    ...(W.filter((w: any) => (w.kind === "decision_needed" || w.kind === "blocker") && !w.resolved).map((w: any) => `- ${w.text}`)), "");
  return { md: lines.join("\n"), summary: sum };
}

async function dailyReport(force = false) {
  const id = await jobStart("daily_report");
  if (!id) return { skipped: true };
  try {
    const day = today();
    const { md, summary } = await buildReport(day);
    await db.from("daily_reports").upsert({ report_date: day, body_md: md, summary, created_at: new Date().toISOString() });
    let email = "not_configured";
    const key = Deno.env.get("RESEND_API_KEY"), e = await cfg("email"), owner = await cfg("owner_email");
    if (key && e?.from && owner) {
      const r = await fetch("https://api.resend.com/emails", { method: "POST", headers: { Authorization: `Bearer ${key}`, "Content-Type": "application/json" },
        body: JSON.stringify({ from: e.from, to: [owner], subject: `Daily commerce report — ${day}`, text: md }) });
      email = r.ok ? "sent" : `failed_${r.status}`;
      await db.from("daily_reports").update({ email_status: email, emailed_at: r.ok ? new Date().toISOString() : null }).eq("report_date", day);
    }
    await jobEnd(id, "ok", { day, email });
    return { day, email, summary };
  } catch (err) {
    await jobEnd(id, "error", null, String(err));
    throw err;
  }
}

// ------------------------------------------------------------------ admin
async function adminSummary() {
  const [stores, products, listings, orders, jobs, reports, costs, msgs, work, kill] = await Promise.all([
    db.from("stores").select("*").order("id"),
    db.from("products").select("id,store_id,title,status,active,price_zar_cents"),
    db.from("listings").select("product_id,channel,status,url,last_checked_at,last_error"),
    db.from("orders").select("ref,store_id,product_id,email,amount_cents,status,provider_mode,created_at,paid_at,gross_cents,fee_cents,net_cents,refunded_cents,notes").order("created_at", { ascending: false }).limit(200),
    db.from("job_runs").select("job,status,started_at,finished_at,error,detail").order("started_at", { ascending: false }).limit(50),
    db.from("daily_reports").select("report_date,body_md,email_status,emailed_at").order("report_date", { ascending: false }).limit(14),
    db.from("costs").select("*").order("incurred_on", { ascending: false }).limit(100),
    db.from("contact_messages").select("*").order("received_at", { ascending: false }).limit(50),
    db.from("work_log").select("*").order("id", { ascending: false }).limit(60),
    cfg("kill_switch"),
  ]);
  return { stores: stores.data, products: products.data, listings: listings.data, orders: orders.data, jobs: jobs.data,
    reports: reports.data, costs: costs.data, messages: msgs.data, work: work.data, kill_switch: kill, budgets: await cfg("budgets"),
    payment: { ...(await cfg("payment")), sandbox: undefined } };
}

async function adminOrder(req: Request) {
  const b = await req.json();
  const { data: o } = await db.from("orders").select("id,status,amount_cents").eq("ref", b.ref).maybeSingle();
  if (!o) return json({ error: "order not found" }, 404);
  if (b.action === "mark_refunded") {
    // Record only: the refund itself must be issued in the PayFast dashboard.
    await db.from("orders").update({ status: "refunded", refunded_cents: o.amount_cents, notes: "refund recorded by owner" }).eq("id", o.id);
    await db.from("download_tokens").update({ revoked: true }).eq("order_id", o.id);
  } else if (b.action === "new_link" && o.status === "paid") {
    const token = [...crypto.getRandomValues(new Uint8Array(24))].map((x) => x.toString(16).padStart(2, "0")).join("");
    await db.from("download_tokens").insert({ token, order_id: o.id, max_downloads: 5, expires_at: new Date(Date.now() + 7 * 86400_000).toISOString() });
    return json({ link: `${Deno.env.get("SUPABASE_URL")}/functions/v1/store-api/download?t=${token}` });
  } else return json({ error: "unsupported action" }, 400);
  return json({ ok: true });
}

// ------------------------------------------------------------------ sync & upload (local factory → backend)
async function sync(req: Request) {
  const b = await req.json();
  if (b.stores?.length) await db.from("stores").upsert(b.stores.map((s: any) => ({ ...s, updated_at: new Date().toISOString() })));
  if (b.products?.length) await db.from("products").upsert(b.products.map((p: any) => ({ ...p, updated_at: new Date().toISOString() })));
  if (b.listings?.length) {
    const { error } = await db.from("listings").upsert(b.listings.map((l: any) => ({ ...l, updated_at: new Date().toISOString() })), { onConflict: "product_id,channel" });
    if (error) return json({ error: error.message }, 400);
  }
  if (b.work?.length) await db.from("work_log").insert(b.work);
  if (b.costs?.length) await db.from("costs").insert(b.costs);
  if (b.site) await db.from("config").update({ value: b.site, updated_at: new Date().toISOString() }).eq("key", "site");
  return json({ ok: true });
}

async function upload(req: Request, url: URL) {
  const key = url.searchParams.get("key") ?? "";
  const bucket = url.searchParams.get("bucket") === "backups" ? "backups" : "products";
  if (!/^[A-Za-z0-9._\-\/]{3,200}$/.test(key) || key.includes("..")) return json({ error: "bad key" }, 400);
  const body = new Uint8Array(await req.arrayBuffer());
  const { error } = await db.storage.from(bucket).upload(key, body, { upsert: true, contentType: "application/zip" });
  if (error) return json({ error: error.message }, 500);
  const sha = [...new Uint8Array(await crypto.subtle.digest("SHA-256", body))].map((x) => x.toString(16).padStart(2, "0")).join("");
  return json({ ok: true, key, bytes: body.length, sha256: sha });
}

Deno.serve(async (req) => {
  if (req.method === "OPTIONS") return new Response(null, { headers: CORS });
  const url = new URL(req.url);
  const route = url.pathname.replace(/^.*\/ops-api/, "") || "/";
  try {
    if (route.startsWith("/cron/")) {
      if (!(await secretOk(req, "cron_secret"))) return json({ error: "unauthorised" }, 401);
      if (route === "/cron/health") return json(await health());
      if (route === "/cron/daily-report") return json(await dailyReport());
    }
    if (route.startsWith("/admin/")) {
      if (route === "/admin/sync" || route === "/admin/upload") {
        if (!(await secretOk(req, "upload_secret"))) return json({ error: "unauthorised" }, 401);
        return route === "/admin/sync" ? await sync(req) : await upload(req, url);
      }
      if (!(await adminOk(req))) return json({ error: "unauthorised" }, 401);
      if (route === "/admin/summary") return json(await adminSummary());
      if (route === "/admin/order") return await adminOrder(req);
      if (route === "/admin/run-report") return json(await dailyReport(true));
      if (route === "/admin/message") {
        const b = await req.json();
        await db.from("contact_messages").update({ status: b.status }).eq("id", b.id);
        return json({ ok: true });
      }
    }
    return json({ error: "not found" }, 404);
  } catch (e) {
    console.error(route, e);
    return json({ error: "server error" }, 500);
  }
});
