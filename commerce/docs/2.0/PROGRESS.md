# Mlinjana Studios 2.0 — progress

Owner brief: "Master project prompt: Mlinjana Studios 2.0" (6 Nov 2026). Full discovery report (shared doc):
https://claude.ai/artifact/TQi3EcD51Ynpbq9QGrKa1F

**Current stage:** 1 Discovery — complete. Stage 2 (Design) waits on the owner decisions below.

## Completed
| Date | Work | Evidence |
|---|---|---|
| 2026-11-06 | Discovery: site, database, storage, functions, payments, catalogue, orders audited | Report (link above) |
| 2026-11-06 | Catalogue inventory exported: 600 products, IDs, URLs, prices, formats, file SHA-256, proposed division/category | `catalogue-inventory.csv` |
| 2026-11-06 | Draft 2.0 taxonomy: every product mapped (Business 303, Life 230, Education 67) | `taxonomy-proposal.json` |
| 2026-11-06 | Fixed: phone header buttons without accessible names; breadcrumb contrast; closed dialogs taking part in layout | commit 59fbd47; Lighthouse accessibility product 100, category 98, search 98, home 96 |

## Decisions waiting on the owner
1. Brand palette: brief's navy/ivory/champagne gold (recommended) vs emerald/marigold chosen 5 Nov.
2. Technology: keep static site + Supabase (recommended) vs Next.js rebuild.
3. International payments: ask PayFast to enable Multi-Currency Pricing (recommended); approximate prices until then.
4. Tax: accountant on EU/UK VAT before marketing abroad.
5. Analytics: Cloudflare Web Analytics + Search Console (recommended) vs GA4 with cookie consent.
6. Licence tiers and multipliers (recommended: Personal and Business at today's price, Team 2.5x, Commercial/Enterprise by quote).
7. Verify mlinjanastudios.com at Resend (owner DNS step) — blocks customer receipts, accounts and newsletter.

## Open technical issues (from the audit)
- `.html` URLs answer 307 → extensionless; links and canonicals use `.html` (Cloudflare assets html_handling).
- Lighthouse records no LCP on the home page (hero fade-in) and, on the live site, the product page; local Chrome now records it for the product page after commit 59fbd47.
- 126 duplicate titles: per-line copies of the six policy pages.
- Structured data: Product only (add Organization, WebSite, BreadcrumbList).
- Cloudflare Web Analytics beacon injected but blocked by CSP.
- PayFast live payments refused on 30 Oct (account not yet enabled).
- Supabase advisors: pg_net in public schema; `weekly_costs_usd` search_path; 4 unindexed FKs.

## Next actions
1. Owner answers decisions 1–7.
2. Stage 2: design preview on a separate address (not the live site).
3. Stage 3.1 quick fixes (redirects, duplicates, structured data) can start as soon as decision 5 is made.

## Rules for every session
- Never claim a test passed unless it ran. Record evidence (commit, order ref, Lighthouse score) here.
- No invented reviews, ratings, sales counts or "best seller" labels.
- Payment code (`store-api`) changes only with sandbox end-to-end tests; never redeploy it from an older copy.
