# TASKS

## Owner (you) — the only steps I can't do for you (legal identity, accounts, money)
- [x] Approve Vercel team access · install Vercel GitHub app · delete test events (done 2026-10-28).
- [x] Store names delegated to Claude → decided (DECISIONS #23).
- [ ] **1. Legal details (needed before any real sale; PayFast also checks them):** your full legal or trading name, physical address, and registration number (or "sole proprietor, not registered"). Send them in chat and I'll fill in the Terms and Privacy pages.
- [ ] **2. PayFast live account:** register at payfast.io and complete the identity and bank checks (FICA). Then, in Supabase → Edge Functions → Secrets, add `PAYFAST_MERCHANT_ID`, `PAYFAST_MERCHANT_KEY` and `PAYFAST_PASSPHRASE`, and tell me. I'll switch to live mode and run a R39 live test purchase for you to approve and refund.
- [x] **3. Cloudflare** — done 2026-10-28. Claude deploys with `engine/deploy_cloudflare.sh` using your API token (stored only in the git-ignored `commerce/.env`). Optional: delete the leftover "mlinjana" Hello-world Worker in the dashboard (it's harmless). Roll the API token if you ever want to cut my access; I'll need a new one for future deploys.
- [ ] **4. Resend (daily report email):** create a free account and either connect the Resend connector in claude.ai, or add a `RESEND_API_KEY` secret in Supabase. I'll set the sender and test it.
- [ ] **5. Spending (optional, needs an amount from you):** one network domain (approx. US$10–15/year; price not checked). Etsy listing fees are US$0.20 per listing, and I'd only list the top sellers.
- [ ] **6. Marketplaces (when you're ready):** Gumroad first (no listing fees): create an account and an access token. Etsy only after there is sales data.

## Claude / automation — next
- [x] Deploy staging site and verify all 60 product URLs (2026-10-28).
- [ ] Auto-deploys: Cloudflare Pages (owner step 3) deploys this branch on every push; staging on Vercel is deployed manually through the Vercel connector.
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
