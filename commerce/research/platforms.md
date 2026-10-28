# Platform research (checked 2026-10-28)

Status key: **Verified** = from the provider's own page in a search result. **Secondary** = third-party source only. **Unverified** = not confirmed. Re-check fees before going live; they change.

## Payment gateways (South African business)

| Gateway | SA sellers | Fees found | Currency / international | API & webhooks | Status |
|---|---|---|---|---|---|
| **PayFast (Network International)** — *chosen* | Yes (SA gateway) | Card 3.2% + R2.00, Instant EFT 2% (min R2) on an undated PayFast fees page; a 2026 third-party article says ~2.85% + R2 | Accepts ZAR only; foreign cards are converted by the card scheme | Hosted payment page + ITN webhook with MD5 signature and server-side validation; public sandbox | Fees: secondary/undated — **confirm in your PayFast account** |
| Paystack | Yes | 2.9% + R1 local cards, 3.1% + R1 international, 2% EFT (excl. VAT), R3 per payout (Paystack support article) | ZAR settlement T+1 | REST API + HMAC-SHA512 webhooks; test keys after sign-up | Verified (support article); cheaper alternative — adapter not built yet |
| Stripe | Not checked for SA availability in this session | — | — | — | Unverified |

Sources: [PayFast fees](https://payfast.io/fees) · [Kolonell 2026 SA fees](https://kolonell.com/en/blog/payment-processing-fees-south-africa-ozow-payfast-2026) · [Paystack pricing](https://support.paystack.com/hc/en-us/articles/360009881920) · [PayFast sandbox values (dj-payfast docs)](https://dj-payfast.readthedocs.io/en/latest/testing.html)

## Marketplaces

| Platform | SA sellers & payouts | Fees found | API for listings | Status / requirement |
|---|---|---|---|---|
| **Etsy** | South Africa is listed as eligible for Etsy Payments | US$0.20 listing fee, 6.5% transaction fee, country-specific payment processing (SA rate not found), Offsite Ads 12–15% when triggered | Open API v3 `createDraftListing` (OAuth, `listings_w`), digital files must be uploaded | Needs your shop, identity/bank verification and an approved API app. Listing fees = spending → needs your authorisation |
| **Gumroad** | Bank payouts in most countries, PayPal where not; SA appears supported (secondary) | Not verified in this session | v2 API: `POST /v2/products` per third-party mirror; `edit_products` scope (official OAuth page) | Adapter written (`engine/publish.py`, **untested**); needs account + access token |
| **Payhip** | PayPal/Stripe payouts; SA users report PayPal withdrawal friction | Free plan 5% + processor fees (third-party) | No public listing API found | Use `catalogue/exports/marketplace_listings.csv` for manual upload |
| **Shopify** (connected store `b2agme-q1`) | Store country ZA, currency ZAR | Plan cost not checked | Admin API + MCP connector | Store is on **trial** — "you'll need to upgrade before you can start selling" |

Sources: [Etsy Payments countries](https://help.etsy.com/hc/articles/115015710408) · [Etsy fees](https://help.etsy.com/hc/articles/115015628847) · [Etsy listings tutorial](https://developers.etsy.com/documentation/tutorials/listings/) · [Gumroad payouts](https://gumroad.com/help/article/13-getting-paid) · [Gumroad API](https://gumroad.com/api) · [Payhip review](https://dodopayments.com/blogs/payhip-review)

## Hosting & email

| Service | Finding | Source |
|---|---|---|
| Vercel Hobby | Non-commercial personal use only; taking payments counts as commercial. Used here **only for staging** | [Vercel fair use](https://vercel.com/docs/limits/fair-use-guidelines) |
| Cloudflare Pages | No commercial-use ban found (secondary sources); free plan limits 500 builds/month | [Cloudflare limits](https://developers.cloudflare.com/pages/platform/limits) |
| GitHub Pages | Not allowed as a host for e-commerce sites | GitHub Pages terms |
| Supabase | Free plan, 2 active projects per org | Connected account |
| Resend | Free tier ~3,000 emails/month, 100/day, 1 domain (secondary) | [Resend pricing summary](https://automationatlas.io/answers/resend-free-tier-explained-2026/) |

## Brand & domain checks (2026-10-28)

Registry availability checked via the Vercel domain API (read-only; nothing bought):
- **Plainday Studio** — plaindaystudio.com ✓, plainday.co ✓ (plainday.com taken). No same-name brand found in a web search.
- **Bizwright** — bizwright.co ✓, bizwrighttemplates.com ✓ (bizwright.com taken). No same-name brand found.
- **Abacus Lane** — abacuslane.com ✓. Unrelated "Abacus" finance companies exist; no "Abacus Lane" brand found.
- Rejected: *Sumwise* (existing financial-modelling spreadsheet product), *Clerkly* (Clerkly UK / Clerky).
- **Not done:** formal trademark searches (CIPC in South Africa, USPTO/WIPO). Do these before registering.
