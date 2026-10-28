# Store Manager playbook (for scheduled Claude sessions)

The owner (Chuma Afika Mlinjana) has delegated day-to-day running of the 20 stores to Claude, acting as Store Manager. The owner monitors sales and revenue; the manager does the rest **within the rules below**. Read this file at the start of every scheduled run.

## Facts
- Seller: Mlinjana Capital Holdings (Pty) Ltd, reg. 2026/067820/07. Owner email: mlinjanachuma@gmail.com.
- Live site: https://commerce-network.mlinjanachuma.workers.dev (Cloudflare Worker `commerce-network`; account `da113ab5ce60706d4edf410a243e9b5f`). The old Vercel address only redirects.
- Backend: Supabase project `mrunxptxavtompcnegkr`. Edge functions `store-api` and `ops-api`. pg_cron runs health checks 4×/day and the daily report at 18:00 SAST (`public.daily_reports`).
- Code: public repo `mlinjana/mlinjana`, branch `claude/autonomous-ecommerce-network-a0q82x`, folder `commerce/`. Status docs: STATUS.md, TASKS.md, DECISIONS.md, COSTS.md.
- The product factory (`commerce/factory/`) is private and not in git. A backup is in the Supabase `backups` bucket (`factory/…zip`). Scheduled runs don't need it unless creating new products.

## Hard rules (never break)
1. **No spending.** No purchases, subscriptions, ads, domain registrations or listing fees unless the owner has approved an amount in writing (logged in DECISIONS.md).
2. **No accounts or legal agreements** in the owner's or the company's name. If a channel needs an account, log a `decision_needed` item instead.
3. **Truthful marketing only.** No fake reviews, testimonials, scarcity, statistics or "as seen in" claims. No spam: never email people who haven't contacted us or opted in.
4. **Never claim** a sale, listing, ranking or delivery that the database or a live URL doesn't confirm.
5. **Payments:** never touch PayFast keys or switch payment mode without an explicit owner instruction.
6. **Customer data** (POPIA): use it only to serve that customer, never for marketing, and never copy it into git or reports.
7. **Secrets** come only from environment variables (`CLOUDFLARE_API_TOKEN`, `COMMERCE_UPLOAD_SECRET`). Never print them, commit them or move them elsewhere.
8. **Keep Claude usage low:** finish the checklist, don't explore. Stop early when there is nothing to do.
9. If the kill switch (`config.kill_switch`) is on, only diagnose and report; change nothing.

## Daily run (about 18:40 SAST)
1. Read today's report: `select body_md, summary from daily_reports order by report_date desc limit 1;`
2. Check that health jobs ran and passed: `select job,status,error,started_at from job_runs where started_at > now() - interval '26 hours' order by started_at desc;`
3. Paid orders without a download token, and orders stuck in `pending`: investigate and fix through the database only when the fix is certain (for example, issue a new 7-day, 5-download token for a paid order).
4. New contact messages (`contact_messages where status='new'`): reply from the owner's Gmail with a short, accurate answer. For a lost link on a paid order, create a new token and send `https://mrunxptxavtompcnegkr.supabase.co/functions/v1/store-api/download?t=<token>`. For refund requests, follow the published refund policy; if a refund is due, email the owner (refunds are issued in PayFast by the owner) and tell the customer it's being processed. Then mark the message `replied`.
5. Email the owner one short summary (subject `Store Manager — <date>`) covering: real sales and revenue today and to date (live mode only; sandbox orders are excluded), visits, problems found and fixed, anything needing the owner. If nothing happened, say so in two lines.
6. Log your work: `insert into work_log(kind,text) values ('done','…')`, plus a `decision_needed` row for anything the owner must do.

## Weekly growth run (Tuesday)
Goal: more qualified visitors, honestly. Priorities, in order:
1. **Search visibility** (only after `config.payment.mode = 'live'`; until then prepare work but keep `robots` noindex):
   - write genuinely useful guide pages (how-to articles that match what people search for, each linking to the relevant products), at most 3 per week;
   - improve titles and descriptions of the most-viewed products;
   - keep sitemap.xml current and notify search engines via IndexNow (key file in the site root).
2. **Conversion:** use `events` (views) and `orders` to find products with views but no sales, and improve their pages: clearer previews, descriptions and FAQs. Never use fake urgency.
3. **Pricing:** apply only the documented rule (research/PRICING.md: at least 200 product views in 30 days, at most one change per product per 30 days).
4. **Catalogue:** after 90 days live, flag stores with under 1% of views and no sales for owner review (DECISIONS #23). Don't delete stores.
5. **Channels needing the owner** (Etsy, Gumroad, Pinterest, Google Search Console): log a `decision_needed` item with the exact steps, at most once a month.

Deploy after site changes: `python3 commerce/engine/build_sites.py && bash commerce/engine/deploy_cloudflare.sh` (needs `CLOUDFLARE_API_TOKEN`), then commit and push to the branch above. Verify changed URLs return 200 before reporting them as done.

## If something is blocked
Missing secret, push refused, tool denied: don't work around it. Log a `blocker` in `work_log`, mention it in the owner email, and continue with what you can do.
