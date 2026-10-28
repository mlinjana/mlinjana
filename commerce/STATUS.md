# STATUS — 2026-10-28

**Overall:** built, validated and **deployed as a public test site**. Payments run in the PayFast **sandbox** — no real sales are possible yet.

| Phase | State | Verified evidence |
|---|---|---|
| 1 Foundation | ✅ Done | Supabase project `commerce-network` (free tier): 13 tables with RLS, private buckets `products`, `backups` |
| 2 Stores | ✅ Deployed (staging) | https://commerce-network.vercel.app — 3 storefronts, 81 pages, dashboard; security headers (CSP, X-Frame-Options, nosniff) verified; mobile 390 px no overflow |
| 3 Product factory | ✅ 60/60 validated | 1,394 PDF pages; 82,863 formulas, 0 error cells after LibreOffice recalculation; 4 numeric regression tests pass |
| 4 Publishing | ✅ Own store 60/60 URL-verified · ⏳ marketplaces awaiting your accounts | 60 own-store listings `live` (HTTP 200 verified, test mode); 240 `awaiting_authorisation` |
| 5 Transactions | ✅ Sandbox end-to-end verified (2026-10-28) | Browser test: checkout → PayFast sandbox → wallet payment → return → verified ITN → order `paid` (gross R59.00, fee R1.36, net R57.64 from PayFast) → download; ZIP SHA-256 identical to original. Forged ITN, fake token, wrong order secret and unknown product all rejected |
| 6 Operations | ✅ Scheduled | pg_cron: report 16:00 UTC (18:00 SAST), health 4×/day; test run of report → stored (2026-10-28) |
| 7 Verification | ⏳ Partial | Report generation verified; email delivery via Gmail verified; sandbox purchase verified locally **and on the public site** (BZW-015, ZIP checksum identical); admin API rejects missing/wrong keys |

**Live URLs (test mode, sandbox payments):** https://commerce-network.vercel.app/plainday/ · /bizwright/ · /abacus/ · owner dashboard /dashboard/

**Blocked on owner:** PayFast live account · Resend key (email) · legal disclosures · hosting choice for live sales. See TASKS.md.
