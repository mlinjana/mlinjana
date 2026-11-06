// Public storefront API: checkout (single product or basket), PayFast ITN, order status, secure download, analytics beacon, contact form.
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

// ---- receipt emails: one branded design for single and basket orders (HTML + plain-text alternative) ----
const escH = (s: string) => String(s).replace(/[&<>"']/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c]!));
const rand = (cents: number) => "R" + (cents / 100).toFixed(2).replace(/\.00$/, "");

type ReceiptItem = { name: string; ref: string; cents: number; link: string };

async function renderReceipt(orderRef: string, items: ReceiptItem[], sandbox: boolean) {
  const site = await cfg("site"), legal = await cfg("legal");
  const base = site?.base_url ?? "https://mlinjanastudios.com";
  const total = items.reduce((a, x) => a + x.cents, 0);
  const date = new Date().toLocaleDateString("en-ZA", { day: "numeric", month: "long", year: "numeric", timeZone: "Africa/Johannesburg" });
  const reg = legal?.registration ? String(legal.registration).split(" (")[0] : "";
  const company = [legal?.operator && `Mlinjana Studios is a trading name of ${legal.operator}`, reg && `Reg. ${reg}`, legal?.address].filter(Boolean).join(" · ");
  const help = `${base}/help/contact`;
  const rows = items.map((x) => `
<tr><td style="padding:14px 0;border-bottom:1px solid #e7e2d7">
  <div style="font-size:15px;font-weight:700;color:#17243b;line-height:1.35">${escH(x.name)}</div>
  <div style="font-size:12.5px;color:#5c6370;margin-top:2px">Item ${escH(x.ref)} · ${rand(x.cents)}</div>
  <table role="presentation" cellpadding="0" cellspacing="0" style="margin-top:10px"><tr><td style="border-radius:10px;background:#17243b">
    <a href="${escH(x.link)}" style="display:inline-block;padding:11px 20px;font-size:14px;font-weight:700;color:#ffffff;text-decoration:none;border-radius:10px">Download ZIP</a>
  </td></tr></table>
</td></tr>`).join("");
  const html = `<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>Your Mlinjana Studios order</title></head>
<body style="margin:0;padding:0;background:#f8f6f0;font-family:-apple-system,'Segoe UI',Roboto,Helvetica,Arial,sans-serif;color:#252a32">
<div style="display:none;max-height:0;overflow:hidden">Payment received. Your ${items.length > 1 ? "downloads are" : "download is"} ready.</div>
<table role="presentation" width="100%" cellpadding="0" cellspacing="0" style="background:#f8f6f0;padding:24px 12px"><tr><td align="center">
<table role="presentation" width="100%" cellpadding="0" cellspacing="0" style="max-width:560px">
  <tr><td style="padding:4px 4px 18px"><a href="${base}"><img src="${base}/assets/brand/logo-email.png" width="158" height="42" alt="Mlinjana Studios" style="display:block;border:0"></a></td></tr>
  <tr><td style="background:#ffffff;border-radius:16px;padding:28px 28px 8px">
    ${sandbox ? `<div style="background:#f6eedc;color:#6b4c10;border-radius:8px;padding:8px 12px;font-size:12.5px;margin-bottom:16px">Test order (PayFast sandbox): no real payment was taken.</div>` : ""}
    <div style="font-size:12px;font-weight:800;letter-spacing:.08em;text-transform:uppercase;color:#8a6418">Payment received</div>
    <h1 style="margin:6px 0 6px;font-size:24px;line-height:1.25;color:#17243b">Thank you for your order</h1>
    <p style="margin:0 0 18px;font-size:15px;color:#4b515c;line-height:1.5">Your ${items.length > 1 ? "files are" : "file is"} ready. Tap the button to download${items.length > 1 ? " each one" : ""}.</p>
    <table role="presentation" width="100%" cellpadding="0" cellspacing="0" style="background:#fbfaf6;border-radius:10px;padding:12px 16px;font-size:13.5px;color:#3a404a">
      <tr><td>Order number</td><td align="right" style="font-weight:700;color:#17243b">${escH(orderRef)}</td></tr>
      <tr><td style="padding-top:4px">Date</td><td align="right" style="padding-top:4px">${date}</td></tr>
      <tr><td style="padding-top:4px">Total paid</td><td align="right" style="padding-top:4px;font-weight:700;color:#17243b">${rand(total)}</td></tr>
    </table>
    <table role="presentation" width="100%" cellpadding="0" cellspacing="0" style="margin-top:8px">${rows}</table>
    <p style="margin:16px 0 0;font-size:13px;color:#5c6370;line-height:1.5">Each link works 5 times over 7 days, so save your files somewhere safe. Open <b>Start Here.pdf</b> in each download for instructions and your licence.</p>
    <table role="presentation" width="100%" cellpadding="0" cellspacing="0" style="margin:20px 0 20px;background:#f6eedc;border-radius:10px"><tr><td style="padding:14px 16px;font-size:13.5px;color:#4b3608;line-height:1.5">
      <b>Need help?</b> Reply to this email or <a href="${help}" style="color:#17243b;font-weight:700">contact us</a> and quote order ${escH(orderRef)}. If a file doesn't work as described, we'll fix it or refund you within 14 days.
    </td></tr></table>
  </td></tr>
  <tr><td style="padding:18px 8px;font-size:11.5px;line-height:1.6;color:#5c6370;text-align:center">
    You're receiving this email because you bought from <a href="${base}" style="color:#5c6370">mlinjanastudios.com</a>.<br>${escH(company)}<br>Payments are processed securely by PayFast.
  </td></tr>
</table></td></tr></table></body></html>`;
  const text = [`Thank you for your order ${orderRef}`, sandbox ? "(Test order, PayFast sandbox: no real payment was taken.)" : "", "",
    `Date: ${date}`, `Total paid: ${rand(total)}`, "", items.length > 1 ? "Your downloads:" : "Your download:",
    ...items.map((x, i) => `${i + 1}. ${x.name} (${rand(x.cents)})\n   ${x.link}`), "",
    "Each link works 5 times over 7 days. Open Start Here.pdf in each download for instructions and your licence.", "",
    `Need help? Reply to this email or visit ${help} and quote order ${orderRef}.`, "", "Mlinjana Studios", company, base]
    .filter((l, i, a) => !(l === "" && a[i - 1] === "")).join("\n");
  return { html, text };
}

async function sendEmail(to: string, subject: string, body: { html: string; text: string }) {
  const key = Deno.env.get("RESEND_API_KEY");
  const e = await cfg("email");
  if (!key || !e?.from) return { ok: false, note: "receipt email not sent: email provider not configured" };
  const r = await fetch("https://api.resend.com/emails", {
    method: "POST", headers: { Authorization: `Bearer ${key}`, "Content-Type": "application/json" },
    body: JSON.stringify({ from: e.from, to: [to], reply_to: e.reply_to ?? undefined, subject, html: body.html, text: body.text }),
  });
  return { ok: r.ok, note: r.ok ? "receipt emailed" : `receipt email failed: ${r.status}` };
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
    ["return_url", `${base}/thanks?ref=${ref}&k=${secret}`],
    ["cancel_url", `${base}/p/${p.slug}?cancelled=1`],
    ["notify_url", `${FN_URL}/payfast-itn`],
    ["email_address", email], ["m_payment_id", ref], ["amount", amount],
    ["item_name", p.title.slice(0, 100)], ["item_description", `Digital download ${p.id}`],
    ["custom_str1", p.id],
  ];
  return json(payfastForm(fields, pf, ref));
}

function payfastForm(fields: [string, string][], pf: Record<string, string>, ref: string) {
  // Live: always signed with the owner's passphrase. Sandbox without a configured passphrase (PayFast's shared
  // test merchant): PayFast accepts unsigned forms; the ITN is then trusted only after server-side validation.
  if (pf.mode === "live" || pf.passphrase) {
    let sigStr = fields.filter(([, v]) => v !== "").map(([k, v]) => `${k}=${phpEncode(v.trim())}`).join("&");
    if (pf.passphrase) sigStr += `&passphrase=${phpEncode(pf.passphrase.trim())}`;
    fields.push(["signature", md5(sigStr)]);
  }
  return { action: `https://${pf.host}/eng/process`, fields: Object.fromEntries(fields), ref, mode: pf.mode };
}

// Basket: several products, one PayFast payment. Each product gets its own order row (same delivery path as a
// single purchase); the basket row carries the payment and is what PayFast's ITN refers to (m_payment_id BSK-…).
async function basketCheckout(req: Request) {
  const kill = await cfg("kill_switch");
  if (kill?.checkout) return json({ error: "Checkout is temporarily paused. Please try again later." }, 503);
  const body = await req.json().catch(() => ({}));
  const email = String(body.email ?? "").trim().toLowerCase();
  if (!EMAIL_RE.test(email)) return json({ error: "Please enter a valid email address." }, 400);
  const ids = [...new Set((Array.isArray(body.items) ? body.items : []).map((x: unknown) => String(x)))]
    .filter((x) => /^[A-Z]{2,5}-\d{3,4}$/.test(x)).slice(0, 25);
  if (!ids.length) return json({ error: "Your basket is empty." }, 400);
  const { data: ps } = await db.from("products").select("id,store_id,title,slug,price_zar_cents,active,status,file_key").in("id", ids);
  const ok = (ps ?? []).filter((p) => p.active && p.status === "validated" && p.file_key);
  if (ok.length !== ids.length) {
    return json({ error: "Some items in your basket are no longer available. Please remove them and try again.",
      unavailable: ids.filter((i) => !ok.some((p) => p.id === i)) }, 409);
  }
  const budgets = await cfg("budgets");
  const since = new Date(Date.now() - 3600_000).toISOString();
  const { count } = await db.from("baskets").select("id", { count: "exact", head: true }).eq("email", email).gte("created_at", since);
  if ((count ?? 0) >= (budgets?.max_pending_orders_per_email_per_hour ?? 10)) return json({ error: "Too many attempts. Please wait a while." }, 429);
  const site = await cfg("site");
  const base = site?.base_url;
  if (!base) return json({ error: "Store URL not configured." }, 500);
  const pf = await payfastCreds();
  const ref = "BSK-" + randHex(6).toUpperCase();
  const secret = randHex(16);
  const total = ok.reduce((a, p) => a + p.price_zar_cents, 0);
  const { data: bk, error } = await db.from("baskets").insert({ ref, secret, email, amount_cents: total, provider: "payfast", provider_mode: pf.mode })
    .select("id").single();
  if (error || !bk) return json({ error: "Could not start checkout." }, 500);
  const rows = ids.map((i) => ok.find((p) => p.id === i)!).map((p) => ({
    ref: "ORD-" + randHex(6).toUpperCase(), secret: randHex(16), product_id: p.id, store_id: p.store_id, email,
    amount_cents: p.price_zar_cents, currency: "ZAR", provider: "payfast", provider_mode: pf.mode, basket_id: bk.id,
  }));
  const { error: e2 } = await db.from("orders").insert(rows);
  if (e2) {
    await db.from("baskets").update({ status: "failed", notes: "order rows not created" }).eq("id", bk.id);
    return json({ error: "Could not start checkout." }, 500);
  }
  const fields: [string, string][] = [
    ["merchant_id", pf.merchant_id], ["merchant_key", pf.merchant_key],
    ["return_url", `${base}/thanks?ref=${ref}&k=${secret}`],
    ["cancel_url", `${base}/?basket=cancelled`],
    ["notify_url", `${FN_URL}/payfast-itn`],
    ["email_address", email], ["m_payment_id", ref], ["amount", (total / 100).toFixed(2)],
    ["item_name", `${rows.length} digital downloads from Mlinjana Studios`],
    ["item_description", ids.join(" ").slice(0, 255)],
    ["custom_str1", "basket"],
  ];
  return json(payfastForm(fields, pf, ref));
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
  if (ref?.startsWith("BSK-")) return await itnBasket(ref, data, pf);
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
  const { data: p } = await db.from("products").select("title").eq("id", order.product_id).single();
  const name = p?.title ?? order.product_id;
  const body = await renderReceipt(order.ref, [{ name, ref: order.ref, cents: order.amount_cents, link: `${FN_URL}/download?t=${token}` }],
    order.provider_mode === "sandbox");
  const r = await sendEmail(order.email, `Your download is ready: ${name} (order ${order.ref})`, body);
  await db.from("orders").update({ notes: r.note }).eq("id", order.id);
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

async function itnBasket(ref: string, data: Record<string, string>, pf: Record<string, string>) {
  const { data: bk } = await db.from("baskets").select("*").eq("ref", ref).maybeSingle();
  if (!bk) { await logPaymentEvent(ref, true, "unknown_basket", data); return new Response("ok"); }
  if (data.merchant_id !== pf.merchant_id || bk.provider_mode !== pf.mode) {
    await logPaymentEvent(ref, true, "merchant_or_mode_mismatch", data);
    return new Response("ok");
  }
  const gross = Math.round(parseFloat(data.amount_gross) * 100);
  if (Math.abs(gross - bk.amount_cents) > 1) {
    await logPaymentEvent(ref, true, "amount_mismatch", data);
    return new Response("ok");
  }
  const status = data.payment_status;
  if (status === "COMPLETE") {
    const fee = Math.round(Math.abs(parseFloat(data.amount_fee ?? "0")) * 100);
    const net = Math.round(parseFloat(data.amount_net ?? String(gross / 100)) * 100);
    const now = new Date().toISOString();
    // idempotent: only pending → paid
    const { data: upd } = await db.from("baskets").update({
      status: "paid", paid_at: now, provider_payment_id: data.pf_payment_id, gross_cents: gross, fee_cents: fee, net_cents: net,
    }).eq("id", bk.id).eq("status", "pending").select("id");
    if (upd && upd.length) {
      const { data: kids } = await db.from("orders").select("*").eq("basket_id", bk.id).order("created_at");
      const b = await cfg("budgets");
      const items: { order: Record<string, any>; token: string }[] = [];
      let feeLeft = fee;
      (kids ?? []).forEach((o, i, a) => { // split PayFast's fee across the items in proportion to price
        const f = i === a.length - 1 ? feeLeft : Math.round(fee * o.amount_cents / Math.max(1, bk.amount_cents));
        feeLeft -= f;
        o._fee = f;
      });
      for (const o of kids ?? []) {
        // a paid basket delivers every item, even if the 6-hour abandoned-checkout job already marked it expired
        const { data: ou } = await db.from("orders").update({
          status: "paid", paid_at: now, provider_payment_id: data.pf_payment_id,
          gross_cents: o.amount_cents, fee_cents: o._fee, net_cents: o.amount_cents - o._fee,
        }).eq("id", o.id).in("status", ["pending", "expired"]).select("id");
        if (ou && ou.length) {
          const token = randHex(24);
          await db.from("download_tokens").insert({
            token, order_id: o.id, max_downloads: b?.downloads_per_order ?? 5,
            expires_at: new Date(Date.now() + (b?.download_days ?? 7) * 86400_000).toISOString(),
          });
          items.push({ order: o, token });
        }
      }
      await sendBasketReceipt(bk, items).catch(() => {});
    }
    await logPaymentEvent(ref, true, upd?.length ? "paid" : "duplicate_complete", data);
  } else if (status === "CANCELLED" || status === "FAILED") {
    const st = status === "CANCELLED" ? "cancelled" : "failed";
    await db.from("baskets").update({ status: st }).eq("id", bk.id).eq("status", "pending");
    await db.from("orders").update({ status: st }).eq("basket_id", bk.id).eq("status", "pending");
    await logPaymentEvent(ref, true, status.toLowerCase(), data);
  } else {
    await logPaymentEvent(ref, true, "status_" + status, data);
  }
  return new Response("ok");
}

async function sendBasketReceipt(bk: Record<string, any>, items: { order: Record<string, any>; token: string }[]) {
  const ids = items.map((x) => x.order.product_id);
  const { data: ps } = await db.from("products").select("id,title").in("id", ids.length ? ids : ["-"]);
  const name = (id: string) => ps?.find((p) => p.id === id)?.title ?? id;
  const body = await renderReceipt(bk.ref, items.map((x) => ({ name: name(x.order.product_id), ref: x.order.ref, cents: x.order.amount_cents,
    link: `${FN_URL}/download?t=${x.token}` })), bk.provider_mode === "sandbox");
  const r = await sendEmail(bk.email, `Your ${items.length} downloads are ready (order ${bk.ref})`, body);
  await db.from("baskets").update({ notes: r.note }).eq("id", bk.id);
}

async function basketStatus(url: URL) {
  const ref = url.searchParams.get("ref") ?? "", k = url.searchParams.get("k") ?? "";
  const { data: bk } = await db.from("baskets").select("id,ref,secret,status,provider_mode").eq("ref", ref).maybeSingle();
  if (!bk || bk.secret !== k) return json({ error: "Order not found" }, 404);
  if (bk.status !== "paid") return json({ ref: bk.ref, status: bk.status, mode: bk.provider_mode });
  const { data: kids } = await db.from("orders").select("id,ref,product_id,status").eq("basket_id", bk.id).order("created_at");
  const { data: ps } = await db.from("products").select("id,title").in("id", (kids ?? []).map((o) => o.product_id));
  const items = [];
  for (const o of kids ?? []) {
    const { data: t } = await db.from("download_tokens").select("token,expires_at,downloads,max_downloads,revoked")
      .eq("order_id", o.id).order("created_at", { ascending: false }).limit(1).maybeSingle();
    items.push({ ref: o.ref, name: ps?.find((p) => p.id === o.product_id)?.title ?? o.product_id,
      download: o.status === "paid" && t && !t.revoked ? `${FN_URL}/download?t=${t.token}` : null,
      expires_at: t?.expires_at, downloads_left: t ? t.max_downloads - t.downloads : 0 });
  }
  return json({ ref: bk.ref, status: bk.status, mode: bk.provider_mode, items });
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
    if (req.method === "POST" && route === "/basket-checkout") return await basketCheckout(req);
    if (req.method === "GET" && route === "/basket") return await basketStatus(url);
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
