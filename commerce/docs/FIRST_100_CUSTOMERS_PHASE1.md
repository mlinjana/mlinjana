# First 100 Customers — Phase 1 implementation

Status: review branch only. **No production deployment, payment configuration change or paid spend**.

## Implemented

1. Outcome-led homepage description and SEO title/description.
2. Four accessible, HTML-based links from the homepage to high-intent catalogue categories (inventory, business finance, personal finance, teacher resources).
3. Clearer product-page buying reassurance, explicit digital delivery language and order recovery link.
4. Responsive styling that respects reduced-motion preferences.
5. Client and API code for anonymous basket-add, checkout-handoff and checkout-error events.
6. Staged SQL migration `011_conversion_funnel.sql` (NOT APPLIED) to permit the new event types.
7. Read-only 30-day conversion report that separates live payments from PayFast sandbox transactions and avoids counting basket items twice.
8. Read-only GitHub Actions workflow that builds every storefront, runs internal link checks and regression tests.
9. Owner dashboard funnel panel and corresponding ops-api 30-day aggregate response, with a fallback when the API has not yet been deployed.
10. Five existing products presented on `/start-here` using actual catalogue records and current prices; homepage links to the page; page appears in sitemap. No new products or unverified discounted bundles created.
11. Headless Chromium responsive smoke tests at 375, 768 and 1366px, with screenshots uploaded as short-lived CI artifacts. All external requests blocked to avoid live checkout or production telemetry.
12. Isolated CI preview builder replaces live config only in a disposable CI workspace: staging/noindex, checkout paused, API disabled (`api.invalid`), and a preview notice that explicitly says payments cannot be placed. The resulting static preview is published as a short-lived GitHub Actions artifact, NOT deployed.
13. Migration 011 tested with a minimal `public.events` schema in disposable PostgreSQL: all intended event types accepted and unrecognised types rejected; this is a constraint smoke test, not full Supabase integration testing.

## Acceptance checklist

- [ ] Build the static commerce site using the current repository build instructions.
- [ ] Run the repository link checker (including the four category paths), ensure there are zero broken links.
- [ ] Check the homepage and sample product pages at 375px, 768px and desktop.
- [ ] Run accessibility checks, including keyboard navigation through the new links.
- [x] Source-level checks verified all four category routes resolve through the current taxonomy slug rule and tracking event names agree across site.js, API allowlist and staged SQL.
- [x] GitHub Actions ran Python compilation, the full Jinja storefront build, the repository link checker and first-customer regression suite successfully.
- [ ] Inspect responsive browser screenshots in the GitHub Actions artifact; human visual sign-off required. The browser smoke job checks link navigation and horizontal overflow.
- [x] Generate separate non-indexable, checkout-disabled preview build and verify absence of the basket checkout form.
- [x] Run migration 011 against disposable PostgreSQL in GitHub Actions and verify allowlist/check constraint on fixture data.
- [ ] Run staging integration test against a dedicated non-production Supabase project when provisioned, verify RLS, API logging and event inserts, then apply to production in a reviewed release.
- [ ] Deploy store-api before or with the new site.js; do not deploy the frontend event calls alone and infer missing events are successful.
- [ ] Deploy ops-api funnel count implementation with dashboard static assets; owner-key access remains required.
- [ ] Confirm live dashboard numbers and explain that owner test purchases count toward verified live payments until individually classified.
- [ ] Confirm prices, product IDs, order creation and PayFast integration have not changed through functional checkout testing.
- [ ] Perform a real end-to-end customer order test, including receipt and download, separately from this presentation-only change.
- [ ] Obtain owner's approval before deployment.

## Next priorities

- Baseline unique visitors and referral traffic, filtering out internal testing.
- Measure product view, add-to-basket, checkout start, PayFast handoff, checkout error and verified payment. Successful download remains a separate backend metric. Avoid recording emails or order secrets in web analytics.
- Use existing catalogue items to design five *validated* flagship bundles; do not invent product contents or discount claims.
- Produce short screen-recorded walkthroughs using actual downloads.
- Test five independent full-price purchases, then run measured, low-budget acquisition experiments.

## Deployment safeguards

Preserve the connected Claude development branch; do not merge over another assistant's edits without resolving conflicts. Retain checkout security rules and the owner's live merchant configuration. Production deployment must be a separate reviewed step. Deploy in this order: staging migration 011 and tests; production migration 011; store-api; ops-api; static site; dashboard event reconciliation and browser checks. No changes were made to production Supabase schema or edge functions by this PR.
