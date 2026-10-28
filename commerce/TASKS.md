# TASKS

## Owner (you) — needed to go live
- [ ] Approve Vercel team access for the connector (link in chat) → lets me deploy the staging stores.
- [ ] Choose live hosting: **Cloudflare Pages** (free; share an API token) or **Vercel Pro** (~US$20/month — paid, needs your OK).
- [ ] PayFast: open/verify a merchant account; add `PAYFAST_MERCHANT_ID`, `PAYFAST_MERCHANT_KEY`, `PAYFAST_PASSPHRASE` as Supabase Edge Function secrets, then set `config.payment.mode = "live"`.
- [ ] Email: create a free Resend account + verify a sender domain; add `RESEND_API_KEY` secret and set `config.email.from` (until then the report is on the dashboard only).
- [ ] Legal: trading name, registration no., physical address (Terms/Privacy); review refund policy & terms.
- [ ] Domains (paid): register plaindaystudio.com / bizwright.co / abacuslane.com if you approve; run CIPC trademark checks first.
- [ ] Marketplaces: Etsy shop + API app; Gumroad account + access token; Payhip account (CSV upload).
- [ ] Set your dashboard owner key in the Supabase SQL editor (see README → Owner key).
- [ ] Decide whether to move the project to a **private** repo (current branch is in the public `mlinjana/mlinjana`).

## Claude / automation — next
- [ ] Deploy staging site, set `site_base`, rebuild, verify all 60 product URLs → own-store listings `live`.
- [ ] Full sandbox purchase test (checkout → PayFast sandbox → ITN → download) and record result.
- [ ] Delete pre-deployment test page-view events (needs your confirmation in Supabase).
- [ ] After first real sales data: re-score opportunities; expand catalogue only where there is demand.
- [ ] Optional: Paystack adapter (lower card fees than PayFast per published rates).

## Done (2026-10-28)
- [x] Research, brand & domain checks; 60 products generated and validated; images; storefronts; backend; cron; report.
