# TASKS

## Owner (you) — needed to go live
- [x] Approve Vercel team access.
- [x] Install the Vercel GitHub app on `mlinjana/mlinjana` (https://github.com/apps/vercel/installations/new) → lets Vercel deploy on every push.
- [ ] Choose live hosting: **Cloudflare Pages** (free; share an API token) or **Vercel Pro** (~US$20/month — paid, needs your OK).
- [ ] PayFast: open/verify a merchant account; add `PAYFAST_MERCHANT_ID`, `PAYFAST_MERCHANT_KEY`, `PAYFAST_PASSPHRASE` as Supabase Edge Function secrets, then set `config.payment.mode = "live"`.
- [ ] Email: create a free Resend account + verify a sender domain; add `RESEND_API_KEY` secret and set `config.email.from` (until then the report is on the dashboard only).
- [ ] Legal: trading name, registration no., physical address (Terms/Privacy); review refund policy & terms.
- [ ] Domains (paid): register plaindaystudio.com / bizwright.co / abacuslane.com if you approve; run CIPC trademark checks first.
- [ ] Marketplaces: Etsy shop + API app; Gumroad account + access token; Payhip account (CSV upload).
- [ ] Set your dashboard owner key in the Supabase SQL editor (see README → Owner key).
- [ ] Decide whether to move the project to a **private** repo (current branch is in the public `mlinjana/mlinjana`).

## Claude / automation — next
- [x] Deploy staging site and verify all 60 product URLs (2026-10-28).
- [ ] Make pushes deploy to production automatically: merge this branch into `main` (production branch) or change Vercel's production branch.
- [x] Full sandbox purchase test — passed 2026-10-28 (see STATUS.md).
- [ ] Delete test analytics events (Supabase asks you to confirm deletes — approve when prompted). New automated/bot visits are already excluded.
- [x] Research-based prices for all 60 products (research/PRICING.md).
- [x] Daily report now includes pricing signals (rule fires at ≥200 product views per product).
- [ ] After first real sales data: re-score opportunities; expand catalogue only where there is demand.
- [ ] Optional: Paystack adapter (lower card fees than PayFast per published rates).

## Done (2026-10-28)
- [x] Research, brand & domain checks; 60 products generated and validated; images; storefronts; backend; cron; report.
