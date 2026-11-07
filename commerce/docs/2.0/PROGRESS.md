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
| 2026-11-06 | Licence tiers: Standard, Team (2.5×, whole rand), Commercial by quote; migration 005; store-api v10; picker, basket, thanks page, /help/licence, Start Here.pdf | commit 784d834. API checks: no licence → R39; team → R98; mixed basket → R612; invalid IDs ignored; unknown licence → Standard. Sandbox through the preview: ORD-873362D6C88B (Team) paid R98; BSK-F78F8722C9D2 paid R305 (Team R98 + Team R148 + Standard R59), licence and amount stored per item, delivered. Front end on the preview, waiting for a live deploy |
| 2026-11-06 | **Licence tiers and lighter division pages live** (owner confirmed the deploy; Cloudflare version 2dcd22ab) | Live checks: key pages 200, redirects, search, category filter, basket, 0 console errors. Live sandbox purchase ORD-A07CB4B9E2FA: Team licence R98 at PayFast, thanks page shows "Team licence (up to 10 people)". All 600 downloads carry the Team wording in Start Here.pdf (600/600 valid, DB fingerprint 067e6e64… matches). Lighthouse mobile (lab): product 100/100/100 LCP 1.3 s; Business 100/100/100 LCP 1.5 s; /help/licence 100/100/100 LCP 1.2 s |

## Product upgrade programme (owner, 7 Nov 2026: "upgrade them all; even the prices must match the products")
Standard: docs/2.0/QUALITY-STANDARD.md. Evidence: engine/value_audit.py -> docs/2.0/value-audit.csv (534 of 600 priced above their content on 7 Nov).
Method: upgrade content in the private factory (backed up to the Supabase 'backups' bucket after every batch), then
value_audit.py -> reprice.py -> factory rebuild -> sync -> site build -> deploy (owner confirms the deploy). Real payments
don't start until every product's price matches its content.

| Group | Builder | Products | Upgraded | Notes |
|---|---|---|---|---|
| Bespoke flagships | specs_b / specs_c + content_f_*.py | 40 | 38 (done 7 Nov) | SOP kit v2 earlier. 37 more: richer Start Here, a Guide sheet explaining each tool's method (KPI definitions, reorder point and safety stock, ABC, amortisation, snowball vs avalanche, markup vs margin…), and companion Worked Example documents for the Word templates (complete business plan, lean canvas, hiring kit, brand guide, onboarding plan, minutes). Not changed: CEO weekly planner (54-page PDF, already substantial) and the business admin bundle (rated fair) |
| Word documents | gen.build_d + content_docs_*.py | 82 | 82 (done 7 Nov) | b1–b8: every generic Word product has a guide, improved template, worked example and listing text that matches the file. Two false claims fixed (comment bank, landlord letters) |
| Spreadsheet trackers | gen.build_x + content_x_*.py | 198 | 198 (done 7 Nov) | b1–b9: every tracker has a hand-written, coherent worked example (a named scenario with consistent figures), a 'What it's for' and 'Good practice' Start Here, and correct key numbers. `check_x_claims.py` requires every number in each example description to be derivable from the example rows; 0 to review. Spot-checked by recalculating in LibreOffice. 18 listings promised features the file didn't have; each now has them (see below) |
| Calculators | gen.build_c + content_c_*.py | 45 | 45 (done 7 Nov) | Every calculator has a Start Here (what it's for, worked example built on its default figures, tips), plus 'Reading the results' and plain-language help for every input on the Calculator sheet. `check_c_claims.py` evaluates each calculator's own formulas and checks every number in the example text (45 checked, 0 open). Fixed: fundraising and break-even results now round up (they rounded down, understating donors and customers needed); the family care calculator gained its missing scenario table |
| Printables | pdfkit + content_p_*.py | 235 | 235 (done 7 Nov) | Each has a guide page (purpose, steps, good practice), a worked-example page (the main page filled in, in the store's second ink colour with a 'Worked example' badge) where the page type allows, and reference pages where real guidance matters (food safety, revision, budgeting, toolbox talks, copywork passages…). Listings name the new pages. Fixed: grid column labels no longer overlap; Toolbox Talk cards now include talking points; Copywork pages now include passages |
| Bundles | - | 20 | - | Priced from their items (<= 65%) |

Tracker fixes, 7 Nov (listing promised something the file didn't do, or a key number was meaningless). Each now does what it says:
- Recipe Costing Calculator: new Recipes sheet with portions, selling price, cost per portion and food-cost % (it only costed ingredient lines).
- Supplier Price Comparison: "Cheapest?" column per item and a count of wins per supplier (it summed unit prices across different items).
- Salary & Job Offer Comparison: weighted score out of 10 (promised, missing). Staff Leave Tracker: leave balances per employee (promised, missing).
- Egg Production: feed per dozen (listing said "feed cost per dozen" with no calculation). Petty Cash Book: cash balance (said "running balance").
- Salon and Food Business trackers: profit (said "monthly profit", none). Beauty Marketing: listing no longer claims promotion costs.
- Strength log and Race calendar: personal-best markers. Body measurements: change from start. Calorie tracker: daily totals. Swimming: weekly totals.
- Income/expense ledgers (rental, smallholding, nonprofit, event, annual budget): key numbers and summaries now show income, costs and net
  instead of adding income and expenses together. Subscription box: monthly recurring revenue from active subscribers only.
- Freelance time tracker: billable value counts billable time only. Party catering counter: only "Yes" replies count for catering.
Builder additions (gen.build_x): coherent example rows per sheet with type and drop-down validation; Start Here sections; key numbers
sumif / net / diff / ratio; summary_view, net_by, countif summaries; cross-sheet formulas ([[Sheet|Column]]), added sheets and columns.
Start Here sheets now print at A4 width (they were clipped). Factory backup: factory/factory-2026-11-07-trackers-done.zip (sha 4d3fefb5…).

Repriced 7 Nov (owner chose 'tiered by type'): printables R39–59, trackers & calculators R49–79, Word kits R69–99, flagships R99–249, placed within each tier by content score; bundles ≤65% of their items, R99–249. List value R44,450 → R42,320. Preview: https://mlinjana-preview.mlinjanachuma.workers.dev (version ccd062c2), 600 products, 0 broken links. Synced and deployed live 7 Nov (version e1f9073c). Checkout paused until PayFast live is active (DECISIONS #43).

Fixed 7 Nov: "Learner Report Comment Bank" claimed "over 100 comments" but had 16; it now has 103.

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
1. Lawyer review of the licence wording (/help/licence, Start Here.pdf) before real sales.
2. Currency display (approximate, labelled) once the PayFast answer is in.
3. Receipt plain-text version: "(Team licence (up to 10 people), R148)" has nested brackets; tidy it with the next store-api change.

## Rules for every session
- Never claim a test passed unless it ran. Record evidence (commit, order ref, Lighthouse score) here.
- No invented reviews, ratings, sales counts or "best seller" labels.
- Payment code (`store-api`) changes only with sandbox end-to-end tests; never redeploy it from an older copy.
