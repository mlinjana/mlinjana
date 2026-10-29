# STATUS — 2026-10-28

**Overall:** 20 stores with 30 products each (600 products) are built, validated and **deployed on Cloudflare** at **https://mlinjanastudios.com** (own domain since 29 Oct). The old Vercel address redirects there. Payments run in the PayFast **sandbox**, so no real sales are possible yet.

| Phase | State | Verified evidence |
|---|---|---|
| 1 Foundation | ✅ Done | Supabase project `commerce-network` (free tier): RLS on all tables; private buckets `products` (600 files, 54 MB, 0 missing) and `backups` |
| 2 Stores | ✅ Deployed on Cloudflare (still sandbox payments), redesigned 29 Oct with a personality per store, 3D/animation, new artwork | https://commerce-network.mlinjanachuma.workers.dev — 20 storefronts, same security headers. Old /pacebook/ links redirect 301 and Vercel redirects 308, 742 pages, dashboard. Pages checked in a headless browser at 390 px and 1280 px: no overflow, no broken images, no script errors. Button colours computed for WCAG AA contrast |
| 3 Product factory | ✅ 600/600 validated | 5,350 PDF pages (A4 + Letter); 109,935 formulas with 0 error cells after LibreOffice recalculation; original regression tests pass; 13 calculator outputs cross-checked against independent calculations (this caught 1 sign error, now fixed) |
| 4 Publishing | ✅ Own store 600/600 URL-verified · ⏳ marketplaces awaiting your accounts | 600 own-store listings `live` (HTTP 200, test mode); 2,400 marketplace listings `awaiting_authorisation` |
| 5 Transactions | ✅ Sandbox end-to-end verified on Cloudflare (Steady Rep PCB-001, ZIP checksum identical) and earlier on Vercel | Public site, Kindkeep KDK-013: checkout → PayFast sandbox → payment → verified ITN → order `paid` (R39.00 gross, R0.90 fee) → download; ZIP SHA-256 identical to the built file |
| 6 Operations | ✅ Scheduled & verified at 600-product scale | Health job: 20/20 stores HTTP 200, 600/600 listings OK, 6.5 s. Daily report counts all 3,000 listings (paginated reads) |
| 7 Verification | ⏳ Partial | Report generation verified; email via Gmail verified earlier; live prices on all 600 pages match the catalogue and the database (R44,450 total across the 600 products) |

**Prices:** 52 products are priced from individual market benchmarks. The other 548 use researched category bands and are marked as estimates (`research/pricing.csv`). Single products cost R39–R279.

**Not yet proven:** real demand. No product has had real traffic or sales.

**Blocked on owner:**
- PayFast live account
- Resend key (email)
- Legal disclosures
- Hosting choice for live sales

See TASKS.md.
