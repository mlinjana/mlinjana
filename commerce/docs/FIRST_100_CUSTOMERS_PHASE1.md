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

## Acceptance checklist

- [ ] Build the static commerce site using the current repository build instructions.
- [ ] Run the repository link checker (including the four category paths), ensure there are zero broken links.
- [ ] Check the homepage and sample product pages at 375px, 768px and desktop.
- [ ] Run accessibility checks, including keyboard navigation through the new links.
- [x] Source-level checks verified all four category routes resolve through the current taxonomy slug rule and tracking event names agree across site.js, API allowlist and staged SQL.
- [x] GitHub Actions ran Python compilation, the full Jinja storefront build, the repository link checker and first-customer regression suite successfully.
- [ ] Manually inspect phone, tablet and desktop visuals; CI does not currently take browser screenshots.
- [ ] Run migration 011 on a non-production database, verify event inserts, then apply with a reviewed release to production.
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
