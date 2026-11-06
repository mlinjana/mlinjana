# Mlinjana Studios 2.0 — progress

Owner brief: "Master project prompt: Mlinjana Studios 2.0" (6 Nov 2026). Full discovery report (shared doc):
https://claude.ai/artifact/TQi3EcD51Ynpbq9QGrKa1F

**Current stage:** 3.1 quick technical fixes — done and live (6 Nov). Next: Stage 2 design preview (navy/ivory/gold), on a separate address.

## Completed
| Date | Work | Evidence |
|---|---|---|
| 2026-11-06 | Discovery: site, database, storage, functions, payments, catalogue, orders audited | Report (link above) |
| 2026-11-06 | Catalogue inventory exported: 600 products, IDs, URLs, prices, formats, file SHA-256, proposed division/category | `catalogue-inventory.csv` |
| 2026-11-06 | Draft 2.0 taxonomy: every product mapped (Business 303, Life 230, Education 67) | `taxonomy-proposal.json` |
| 2026-11-06 | Fixed: phone header buttons without accessible names; breadcrumb contrast; closed dialogs taking part in layout | commit 59fbd47; Lighthouse accessibility product 100, category 98, search 98, home 96 |
| 2026-11-06 | Owner decisions recorded (palette, keep and extend, analytics, licence tiers) | DECISIONS.md #39 |
| 2026-11-06 | Extensionless links and canonicals everywhere; per-shop policy copies canonical to /help/; broken thanks canonical fixed; sitemap adds help pages, drops shop pages that canonicalise to their department | commit 46efa26; `engine/check_links.py`: 762 pages, 95,911 links, 0 broken, 0 redirecting (live-mode build: 638 sitemap URLs, 0 broken); live `curl`: product URL 200 with no redirect, old .html 307 keeps the query string |
| 2026-11-06 | Structured data: Organization + WebSite (SearchAction) on home; BreadcrumbList on department, shop and product pages; Product gains image, category and seller | JSON parsed and checked for home, department, shop and product pages. Not yet run through Google's Rich Results Test (needs the site indexable) |
| 2026-11-06 | Cloudflare Web Analytics allowed in CSP; privacy notice names it | Live browser test: beacon script 200, report POST /cdn-cgi/rum 204, no console errors |
| 2026-11-06 | Missing LCP fixed: carousels combined scroll snapping with CSS smooth scrolling, which ended LCP measurement | commit 34ce523; before: 3/8 product loads and 0/8 home loads recorded LCP; after: 8/8 on home, product, shop, search, category. Live Lighthouse mobile (lab): home perf 99 LCP 1.9 s, product 100 LCP 1.6 s, shop 100 LCP 1.6 s, search 100 LCP 1.3 s; CLS 0 on all |

## Owner decisions (6 Nov 2026, DECISIONS.md #39)
- Palette: Midnight Navy, Warm Ivory, Champagne Gold, Charcoal, White.
- Technology: keep and extend the static site + Supabase.
- Analytics: Cloudflare Web Analytics + Google Search Console.
- Licences: Personal and Business at today's price; Team (up to 10) 2.5×; Commercial/Enterprise by quote.

## Still waiting on the owner
1. PayFast: confirm the live account can take payments, and ask whether Multi-Currency Pricing can be enabled.
2. Tax: accountant on EU/UK VAT before marketing abroad.
3. Verify mlinjanastudios.com at Resend (DNS step): blocks customer receipts, accounts and newsletter.
4. Search Console: add the property once the site leaves staging (it is `noindex` now, by design, until PayFast is live).

## Open technical issues
- Per-shop policy copies still exist (duplicate titles) but now canonicalise to /help/. Removing them waits until store-api no longer links to them.
- store-api return/cancel URLs still use `.html`; they work via Cloudflare's 307, and the query string is kept. Change only with a sandbox end-to-end test.
- PayFast live payments refused on 30 Oct (account not yet enabled).
- Lighthouse SEO 69 on every page: only the deliberate staging `noindex`.
- Lab data only: real-user Core Web Vitals (including INP) need Cloudflare Web Analytics data over time.
- Supabase advisors: pg_net in public schema; `weekly_costs_usd` search_path; 4 unindexed FKs.

## Next actions
1. Stage 2: recolour the logo to navy/ivory/gold; apply the palette; build the Business / Life / Education navigation from `taxonomy-proposal.json`; new static hero "Make Better Things Happen."; deploy to a separate preview Worker for owner approval.
2. Licence tiers in product pages, checkout (store-api, sandbox-tested), receipts and Start Here.pdf.
3. Currency display (approximate, labelled) once the PayFast answer is in.

## Rules for every session
- Never claim a test passed unless it ran. Record evidence (commit, order ref, Lighthouse score) here.
- No invented reviews, ratings, sales counts or "best seller" labels.
- Payment code (`store-api`) changes only with sandbox end-to-end tests; never redeploy it from an older copy.
