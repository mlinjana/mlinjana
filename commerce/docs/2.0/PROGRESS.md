# Mlinjana Studios 2.0 — progress

Owner brief: "Master project prompt: Mlinjana Studios 2.0" (6 Nov 2026). Full discovery report (shared doc):
https://claude.ai/artifact/TQi3EcD51Ynpbq9QGrKa1F

**Current stage:** 2.0 design and navigation are **live** on mlinjanastudios.com (6 Nov 2026, Cloudflare version 53c256f4, DECISIONS.md #41). The site is still in staging mode (noindex, PayFast sandbox) until PayFast confirms the live account. Next: licence tiers, currency display.

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
| 2026-11-06 | Stage 2 preview: logo recoloured (navy/gold); palette tokens; Business / Life / Education divisions + 29 category pages from config/taxonomy.json; new header, mega-menu, footer and search filter; static hero "Make Better Things Happen." | commit 7caf20d; preview Worker version 2c06769f; link check 794 pages, 0 broken, 0 redirecting; preview browser test: Life-filtered search (164 results for "planner"), category chip filter (66 → 3), 2-item basket R118, checkout reached sandbox.payfast.co.za (no payment made). Lighthouse mobile, preview: home perf 97 / a11y 100 / LCP 1.9 s; division 98 / 100 / 2.0 s; category 99 / 100 / 1.6 s; product 100 / 100 / 1.3 s; search 100 / 100 / 1.8 s; CLS 0 on all |
| 2026-11-06 | store-api v9: navy/gold receipt email; PayFast return/cancel URLs without .html | Sandbox: ORD-983B275A536D (single, returned to /chairbook/thanks) and BSK-47B08AB33489 (2 items, fee 136 + 135 cents) paid on verified ITNs; 3/3 ZIPs downloaded. Receipt delivery not tested (Resend 422 for a non-owner address); design checked by local render |
| 2026-11-06 | All 600 downloads rebuilt: navy Start Here.pdf, navy logo on PDF covers; preview images re-rendered | 600/600 validated; listing/price differences vs previous catalogue: 0; 600 files uploaded; DB SHA fingerprint e409e0cc… matches catalogue; 97,646,388 bytes stored, 0 missing; 8 random Start Here.pdf pages: navy present, 0 emerald pixels |
| 2026-11-06 | Old /c/ department pages replaced by 301 redirects to 2.0 categories/divisions | `_redirects` (11 departments × 2 forms); link check 783 pages, 0 broken, 0 redirecting |
| 2026-11-06 | **2.0 live** on mlinjanastudios.com (owner confirmed the deploy) | Live checks: 9 key pages 200 with the navy theme; /c/money/ → 301 /life/personal-finance/; /c/small-business → 301 /business/; old .html → 307 short URL; /pacebook/ → 301 /steadyrep/; search (Business, "invoice") 10 results; category filter 15; basket R69; 0 console errors. Lighthouse mobile (lab): home 99/100/100 LCP 1.6 s; Business division 92/100/100 LCP 2.4 s (TBT 240 ms, the heaviest page: 12 rows of products); category 100/100/100 LCP 1.6 s; product 100/100/100 LCP 1.6 s; search 98/100/100 LCP 2.3 s; CLS 0 on all |

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
- Per-shop policy copies still exist (duplicate titles) but canonicalise to /help/. Single-item checkout returns to /<line>/thanks, so that copy must stay; the other per-shop copies could be removed with 301s to /help/.
- PayFast live payments refused on 30 Oct (account not yet enabled).
- Lighthouse SEO 69 on every page: only the deliberate staging `noindex`.
- Lab data only: real-user Core Web Vitals (including INP) need Cloudflare Web Analytics data over time.
- Supabase advisors: pg_net in public schema; `weekly_costs_usd` search_path; 4 unindexed FKs.

## Next actions
1. Ship the lighter division pages (built, on the preview; waiting for the next live deploy). The earlier Business result (perf 92, LCP 2.4 s) was a noisy single run: two repeat runs on 6 Nov gave perf 99, LCP 1.7–1.9 s. The trimmed page (6 rows of 8 instead of 12 rows of 12) scored 98–99, LCP 1.5–1.7 s, total weight 1,043 KiB vs 1,306 KiB.
2. Licence tiers in product pages, checkout (store-api, sandbox-tested), receipts and Start Here.pdf.
3. Currency display (approximate, labelled) once the PayFast answer is in.

## Rules for every session
- Never claim a test passed unless it ran. Record evidence (commit, order ref, Lighthouse score) here.
- No invented reviews, ratings, sales counts or "best seller" labels.
- Payment code (`store-api`) changes only with sandbox end-to-end tests; never redeploy it from an older copy.
