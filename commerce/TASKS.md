# TASKS

## Owner (you) — needed to go live
- [x] Approve Vercel team access.
- [x] Install the Vercel GitHub app on `mlinjana/mlinjana` (https://github.com/apps/vercel/installations/new) → lets Vercel deploy on every push.
- [ ] Choose live hosting: **Cloudflare Pages** (free; share an API token) or **Vercel Pro** (~US$20/month — paid, needs your OK).
- [ ] PayFast: open/verify a merchant account; add `PAYFAST_MERCHANT_ID`, `PAYFAST_MERCHANT_KEY`, `PAYFAST_PASSPHRASE` as Supabase Edge Function secrets, then set `config.payment.mode = "live"`.
- [ ] Email: create a free Resend account + verify a sender domain; add `RESEND_API_KEY` secret and set `config.email.from` (until then the report is on the dashboard only).
- [ ] Legal: trading name, registration no., physical address (Terms/Privacy); review refund policy & terms.
- [ ] Domains (paid): register plaindaystudio.com / bizwright.co / abacuslane.com and any of the 17 new brands' domains you want (see `config/stores.json → domain_plan`; checked available 2026-10-28, not purchased). Run CIPC trademark checks first.
- [ ] Review the 17 new store names/niches and tell me which to keep, rename or drop.
- [ ] Marketplaces: Etsy shop + API app; Gumroad account + access token; Payhip account (CSV upload).
- [ ] Set your dashboard owner key in the Supabase SQL editor (see README → Owner key).
- [ ] Decide whether to move the project to a **private** repo (current branch is in the public `mlinjana/mlinjana`).

## Claude / automation — next
- [x] Deploy staging site and verify all 60 product URLs (2026-10-28).
- [ ] Make pushes deploy to production automatically: merge this branch into `main` (production branch) or change Vercel's production branch.
- [x] Full sandbox purchase test — passed 2026-10-28 (see STATUS.md).
- [ ] Delete test analytics events — run `delete from public.events where ts < now();` in the Supabase SQL editor (my delete requests time out waiting for your approval). New automated/bot visits are already excluded.
- [x] Research-based prices for all 60 products (research/PRICING.md).
- [x] Daily report now includes pricing signals (rule fires at ≥200 product views per product).
- [ ] After first real sales data: re-score opportunities per store; prune or expand stores based on demand.
- [ ] Individually benchmark prices for the best-viewed new products (548 are category-band estimates).
- [ ] Optional: Paystack adapter (lower card fees than PayFast per published rates).

## Done (2026-10-28)
- [x] Expanded to 20 stores × 30 unique products (600), validated, priced, deployed, URL- and price-verified; sandbox purchase verified on a new store.
- [x] Research, brand & domain checks; 60 products generated and validated; images; storefronts; backend; cron; report.
