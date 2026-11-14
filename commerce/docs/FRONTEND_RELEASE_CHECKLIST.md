# Frontend-only release: review and rollback checklist

Scope: PR #2, marketing UI only. Base: `claude/autonomous-ecommerce-network-a0q82x`.
Never deploy PR #1's tracking code or migration 011 as part of this release.

## Pre-merge
1. Confirm frontend-only GitHub Actions workflow succeeds on the latest commit, including scope guard, complete Jinja build, link checker and Chromium screenshots.
2. Review screenshots for desktop, tablet and mobile. Check readability of hero copy, four task cards, five-offer `/start-here`, nav crowding and the sample product purchase panel.
3. Confirm all five featured products still exist and match the published catalogue; verify claims and prices.
4. Confirm PR #2 diff **does not touch** `commerce/supabase/**`, `commerce/engine/static/site.js`, `commerce/config/stores.json`, `commerce/catalogue/**`, or PayFast handling.
5. Confirm no concurrent Claude changes need reconciliation before merge.

## Merge/release
1. Approve the reviewed PR and merge it into the current commerce development branch; do not merge PR #1 yet.
2. Record the currently live Cloudflare Worker deployment ID and ensure a known-good rollback target is available before deployment.
3. Rebuild the storefront from the approved branch. Confirm the existing live-mode configuration is unchanged.
4. Follow the existing restricted Cloudflare deployment process only after owner visual/release approval. The `deploy_cloudflare.sh` script can update both the primary and www Workers; this is a production action, not a read-only test.
5. Inspect the live homepage, product pages, `/start-here`, mobile layout, assets and navigation.
6. Carry out a customer-style full-price order and confirm verified PayFast payment, receipt email, signed download and correct order status. Refund test purchase if appropriate.
7. Record any analytics anomalies; the new funnel tracking must NOT be expected before PR #1's backend release.

## Rollback plan
- If customers cannot browse products, add to basket, pay or download, stop the rollout and restore the previous known-good Cloudflare Workers deployment(s).
- Recheck both apex and www routing, then retest purchasing and receipts.
- Record incident symptoms, timestamps and the deployed Git commit before retrying.

## Sign-off
- [ ] CI green at exact reviewed commit
- [ ] Screenshot/visual sign-off
- [ ] Owner approves production deployment
- [ ] Recorded rollback deployment IDs
- [ ] Production deployed and verified
- [ ] End-to-end paid order verified
- [ ] First-customer campaign activated

**Current status:** pre-merge review only. No deployment or customer acquisition campaign has been initiated by this document.
