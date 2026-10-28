// Public storefront API: checkout, PayFast ITN, order status, secure download, analytics beacon, contact form.
// Payment state changes ONLY on a verified ITN (signature + PayFast server validation + amount + merchant check).
import { createClient } from "npm:@supabase/supabase-js@2";
import { createHash } from "node:crypto";

const db = createClient(Deno.env.get("SUPABASE_URL")!, Deno.env.get("SUPABASE_SERVICE_ROLE_KEY")!, {
  auth: { persistSession: false },
});
const FN_URL = `${Deno.env.get("SUPABASE_URL")}/functions/v1/store-api`;
const CORS = {
  "Access-Control-Allow-Origin": "*",
  "Access-Control-Allow-Headers": "content-type",
  "Access-Control-Allow-Methods": "GET, POST, OPTIONS",
};
const json = (body: unknown, status = 200) =>
  new Response(JSON.stringify(body), { status, headers: { ...CORS, "Content-Type": "application/json" } });
const EMAIL_RE = /^[^\s@]{1,64}@[^\s@]{1,190}\.[^\s@]{2,24}$/;

async function cfg(key: string) {
  const { data } = await db.from("config").select("value").eq("key", key).maybeSingle();
  return data?.value;
}

function randHex(n: number) {
  const b = crypto.getRandomValues(new Uint8Array(n));
  return [...b].map((x) => x.toString(16).padStart(2, "0")).join("");
}

// PHP urlencode() equivalent — PayFast signatures are defined in terms of it.
function phpEncode(s: string) {
  return encodeURIComponent(s).replace(/[!'()*~]/g, (c) => "%" + c.charCodeAt(0).toString(16).toUpperCase())
    .replace(/%20/g, "+");
}

function md5(s: string) {
  return createHash("md5").update(s, "utf8").digest("hex");
}

async function payfastCreds() {
  const p = await cfg("payment");
  if (p?.mode === "live") {
    const id = Deno.env.get("PAYFAST_MERCHANT_ID"), key = Deno.env.get("PAYFAST_MERCHANT_KEY");
    if (!id || !key) throw new Error("live mode selected but PayFast live secrets are not set");
    return { mode: "live", merchant_id: id, merchant_key: key, passphrase: Deno.env.get("PAYFAST_PASSPHRASE") ?? "", host: p.live_host };
  }
  return { mode: "sandbox", ...p.sandbox };
}

async function logPaymentEvent(order_ref: string | null, verified: boolean, outcome: string, payload: Record<string, string>) {
  // never store card data — PayFast ITNs don't contain it; we still drop name/email fields to minimise personal data
  const safe = Object.fromEntries(Object.entries(payload).filter(([k]) => !/^(name_|email_|cell_)/.test(k)));
  await db.from("payment_events").insert({ provider: "payfast", order_ref, verified, outcome, payload: safe });
}

async function checkout(req: Request) {
  const kill = await cfg("kill_switch");
  if (kill?.checkout) return json({ error: "Checkout is temporarily paused. Please try again later." }, 503);
  const body = await req.json().catch(() => ({}));
  const email = String(body.email ?? "").trim().toLowerCase();
  const productId = String(body.product_id ?? "");
  if (!EMAIL_RE.test(email)) return json({ error: "Please enter a valid email address." }, 400);
  const { data: p } = await db.from("products").select("id,store_id,title,slug,price_zar_cents,active,status,file_key")
    .eq("id", productId).maybeSingle();
  if (!p || !p.active || p.status !== "validated" || !p.file_key) return json({ error: "This product is not available." }, 404);
  const budgets = await cfg("budgets");
  const since = new Date(Date.now() - 3600_000).toISOString();
  const { count } = await db.from("orders").select("id", { count: "exact", head: true }).eq("email", email).gte("created_at", since);
  if ((count ?? 0) >= (budgets?.max_pending_orders_per_email_per_hour ?? 10)) return json({ error: "Too many attempts. Please wait a while." }, 429);
  const site = await cfg("site");
  const base = site?.stores?.[p.store_id];
  if (!base) return json({ error: "Store URL not configured." }, 500);
  const pf = await payfastCreds();
  const ref = "ORD-" + randHex(6).toUpperCase();
  const secret = randHex(16);
  const amount = (p.price_zar_cents / 100).toFixed(2);
  const { error } = await db.from("orders").insert({
    ref, secret, product_id: p.id, store_id: p.store_id, email, amount_cents: p.price_zar_cents, currency: "ZAR",
    provider: "payfast", provider_mode: pf.mode,
  });
  if (error) return json({ error: "Could not start checkout." }, 500);
  // Field order matters for the signature (PayFast documented order).
  const fields: [string, string][] = [
    ["merchant_id", pf.merchant_id], ["merchant_key", pf.merchant_key],
    ["return_url", `${base}/thanks.html?ref=${ref}&k=${secret}`],
    ["cancel_url", `${base}/p/${p.slug}.html?cancelled=1`],
    ["notify_url", `${FN_URL}/payfast-itn`],
    ["email_address", email], ["m_payment_id", ref], ["amount", amount],
    ["item_name", p.title.slice(0, 100)], ["item_description", `Digital download ${p.id}`],
    ["custom_str1", p.id],
  ];
  // Live: always signed with the owner's passphrase. Sandbox without a configured passphrase (PayFast's shared
  // test merchant): PayFast accepts unsigned forms; the ITN is then trusted only after server-side validation.
  if (pf.mode === "live" || pf.passphrase) {
    let sigStr = fields.filter(([, v]) => v !== "").map(([k, v]) => `${k}=${phpEncode(v.trim())}`).join("&");
    if (pf.passphrase) sigStr += `&passphrase=${phpEncode(pf.passphrase.trim())}`;
    fields.push(["signature", md5(sigStr)]);
  }
  return json({ action: `https://${pf.host}/eng/process`, fields: Object.fromEntries(fields), ref, mode: pf.mode });
}

async function itn(req: Request) {
  const raw = await req.text();
  const pairs = raw.split("&").filter(Boolean).map((kv) => {
    const i = kv.indexOf("=");
    const k = decodeURIComponent(kv.slice(0, i));
    const v = decodeURIComponent(kv.slice(i + 1).replace(/\+/g, " "));
    return [k, v] as [string, string];
  });
  const data = Object.fromEntries(pairs);
  const ref = data.m_payment_id ?? null;
  const pf = await payfastCreds();
  // 1. signature over posted fields (in received order, excluding signature)
  const paramStr = pairs.filter(([k]) => k !== "signature").map(([k, v]) => `${k}=${phpEncode(v.trim())}`).join("&");
  const expected = md5(pf.passphrase ? `${paramStr}&passphrase=${phpEncode(pf.passphrase.trim())}` : paramStr);
  const sigRequired = pf.mode === "live" || !!pf.passphrase;
  if (sigRequired && expected !== data.signature) {
    await logPaymentEvent(ref, false, "bad_signature", data);
    return new Response("bad signature", { status: 400 });
  }
  // 2. confirm with PayFast's server
  const v = await fetch(`https://${pf.host}/eng/query/validate`, {
    method: "POST", headers: { "Content-Type": "application/x-www-form-urlencoded" }, body: paramStr,
  }).then((r) => r.text()).catch((e) => "ERROR " + e);
  if (v.trim() !== "VALID") {
    await logPaymentEvent(ref, false, "server_validation_failed:" + v.slice(0, 60), data);
    return new Response("not valid", { status: 400 });
  }
  // 3. order, merchant and amount checks
  const { data: order } = await db.from("orders").select("*").eq("ref", ref).maybeSingle();
  if (!order) { await logPaymentEvent(ref, true, "unknown_order", data); return new Response("ok"); }
  if (data.merchant_id !== pf.merchant_id || order.provider_mode !== pf.mode) {
    await logPaymentEvent(ref, true, "merchant_or_mode_mismatch", data);
    return new Response("ok");
  }
  const gross = Math.round(parseFloat(data.amount_gross) * 100);
  if (Math.abs(gross - order.amount_cents) > 1) {
    await logPaymentEvent(ref, true, "amount_mismatch", data);
    return new Response("ok");
  }
  const status = data.payment_status;
  if (status === "COMPLETE") {
    const fee = Math.round(Math.abs(parseFloat(data.amount_fee ?? "0")) * 100);
    const net = Math.round(parseFloat(data.amount_net ?? String(gross / 100)) * 100);
    // idempotent: only pending → paid
    const { data: upd } = await db.from("orders").update({
      status: "paid", paid_at: new Date().toISOString(), provider_payment_id: data.pf_payment_id,
      gross_cents: gross, fee_cents: fee, net_cents: net,
    }).eq("ref", ref).eq("status", "pending").select("id");
    if (upd && upd.length) {
      const b = await cfg("budgets");
      const token = randHex(24);
      await db.from("download_tokens").insert({
        token, order_id: order.id, max_downloads: b?.downloads_per_order ?? 5,
        expires_at: new Date(Date.now() + (b?.download_days ?? 7) * 86400_000).toISOString(),
      });
      await sendReceipt(order, token).catch(() => {});
    }
    await logPaymentEvent(ref, true, upd?.length ? "paid" : "duplicate_complete", data);
  } else if (status === "CANCELLED" || status === "FAILED") {
    await db.from("orders").update({ status: status === "CANCELLED" ? "cancelled" : "failed" }).eq("ref", ref).eq("status", "pending");
    await logPaymentEvent(ref, true, status.toLowerCase(), data);
  } else {
    await logPaymentEvent(ref, true, "status_" + status, data);
  }
  return new Response("ok");
}

async function sendReceipt(order: Record<string, any>, token: string) {
  const key = Deno.env.get("RESEND_API_KEY");
  const e = await cfg("email");
  if (!key || !e?.from) {
    await db.from("orders").update({ notes: "receipt email not sent: email provider not configured" }).eq("id", order.id);
    return;
  }
  const site = await cfg("site");
  const link = `${FN_URL}/download?t=${token}`;
  const { data: p } = await db.from("products").select("title").eq("id", order.product_id).single();
  const r = await fetch("https://api.resend.com/emails", {
    method: "POST", headers: { Authorization: `Bearer ${key}`, "Content-Type": "application/json" },
    body: JSON.stringify({
      from: e.from, to: [order.email], reply_to: e.reply_to ?? undefined,
      subject: `Your download: ${p?.title ?? order.product_id} (order ${order.ref})`,
      text: `Thank you for your order ${order.ref}.\n\nDownload your file here (valid 7 days, up to 5 downloads):\n${link}\n\n` +
        `Need help? Use the contact page: ${site?.stores?.[order.store_id] ?? ""}/contact.html and quote ${order.ref}.`,
    }),
  });
  await db.from("orders").update({ notes: r.ok ? "receipt emailed" : `receipt email failed: ${r.status}` }).eq("id", order.id);
}

async function orderStatus(url: URL) {
  const ref = url.searchParams.get("ref") ?? "", k = url.searchParams.get("k") ?? "";
  const { data: o } = await db.from("orders").select("id,ref,secret,status,product_id,provider_mode").eq("ref", ref).maybeSingle();
  if (!o || o.secret !== k) return json({ error: "Order not found" }, 404);
  if (o.status !== "paid") return json({ ref: o.ref, status: o.status, mode: o.provider_mode });
  const { data: t } = await db.from("download_tokens").select("token,expires_at,downloads,max_downloads,revoked")
    .eq("order_id", o.id).order("created_at", { ascending: false }).limit(1).maybeSingle();
  return json({ ref: o.ref, status: o.status, mode: o.provider_mode, download: t && !t.revoked ? `${FN_URL}/download?t=${t.token}` : null,
    expires_at: t?.expires_at, downloads_left: t ? t.max_downloads - t.downloads : 0 });
}

async function download(url: URL) {
  const tok = url.searchParams.get("t") ?? "";
  const { data: t } = await db.from("download_tokens").select("token,order_id,expires_at,downloads,max_downloads,revoked").eq("token", tok).maybeSingle();
  const page = (msg: string, s = 410) => new Response(msg, { status: s, headers: { "Content-Type": "text/plain; charset=utf-8" } });
  if (!t || t.revoked) return page("This download link is not valid. Please use the contact page and quote your order number.", 404);
  if (new Date(t.expires_at) < new Date() || t.downloads >= t.max_downloads) return page("This download link has expired. Please use the contact page and quote your order number and we'll send a new one.");
  const { data: o } = await db.from("orders").select("status,product_id").eq("id", t.order_id).single();
  if (o?.status !== "paid") return page("This order is not marked as paid.", 403);
  const { data: p } = await db.from("products").select("file_key,slug").eq("id", o.product_id).single();
  const { data: s, error } = await db.storage.from("products").createSignedUrl(p!.file_key, 120, { download: `${p!.slug}.zip` });
  if (error || !s) return page("The file is temporarily unavailable. Please try again shortly.", 503);
  await db.from("download_tokens").update({ downloads: t.downloads + 1 }).eq("token", tok).eq("downloads", t.downloads);
  return Response.redirect(s.signedUrl, 302);
}

async function track(req: Request) {
  const b = await req.json().catch(() => ({}));
  const type = ["page_view", "product_view", "checkout_start"].includes(b.type) ? b.type : null;
  if (!type) return json({ ok: false }, 400);
  let host: string | null = null;
  try { host = b.ref ? new URL(b.ref).hostname.slice(0, 120) : null; } catch { host = null; }
  await db.from("events").insert({ type, store_id: String(b.store ?? "").slice(0, 20) || null,
    product_id: b.product_id ? String(b.product_id).slice(0, 20) : null, path: String(b.path ?? "").slice(0, 200), referrer_host: host });
  return json({ ok: true });
}

async function contact(req: Request) {
  const b = await req.json().catch(() => ({}));
  const email = String(b.email ?? "").trim().toLowerCase();
  const msg = String(b.message ?? "").trim();
  if (!EMAIL_RE.test(email) || msg.length < 5 || msg.length > 4000) return json({ error: "Please enter your email and a message." }, 400);
  if (b.website) return json({ ok: true }); // honeypot
  await db.from("contact_messages").insert({ email, message: msg, store_id: String(b.store ?? "").slice(0, 20),
    product_id: b.product_id ? String(b.product_id).slice(0, 20) : null, order_ref: b.order_ref ? String(b.order_ref).slice(0, 20) : null });
  return json({ ok: true });
}

Deno.serve(async (req) => {
  if (req.method === "OPTIONS") return new Response(null, { headers: CORS });
  const url = new URL(req.url);
  const route = url.pathname.replace(/^.*\/store-api/, "") || "/";
  try {
    if (req.method === "POST" && route === "/checkout") return await checkout(req);
    if (req.method === "POST" && route === "/payfast-itn") return await itn(req);
    if (req.method === "GET" && route === "/order") return await orderStatus(url);
    if (req.method === "GET" && route === "/download") return await download(url);
    if (req.method === "POST" && route === "/track") return await track(req);
    if (req.method === "POST" && route === "/contact") return await contact(req);
    if (route === "/health") return json({ ok: true });
    return json({ error: "not found" }, 404);
  } catch (e) {
    console.error(route, e);
    return json({ error: "server error" }, 500);
  }
});
