# Digital commerce network

Twenty independently branded digital-product stores (30 products each, 600 total) on one shared, low-cost engine.

| Store | Sells | Products |
|---|---|---|
| **Plainday Studio** (`/plainday/`) | Printable planners & journals (PDF, A4 + US Letter) | 20 |
| **Bizwright** (`/bizwright/`) | Business templates (Excel, Word, PDF) | 20 |
| **Abacus Lane** (`/abacus/`) | Finance & operations spreadsheet tools (Excel / Google Sheets) | 20 |

## Architecture
```
factory/ (private, gitignored) ──► build/ (private) ──► Supabase Storage (private bucket)
   specs + templates → PDF/XLSX/DOCX → validate (LibreOffice recalc, regression tests) → covers/previews
catalogue/products.json ──► engine/build_sites.py ──► site/ (static: 20 stores + dashboard) ──► Vercel/Cloudflare
engine/publish.py ──► catalogue/listings.json + exports/marketplace_listings.csv
engine/sync.py ──► ops-api /admin/upload + /admin/sync ──► Postgres (products, listings, stores)
Browser ──► store-api /checkout ──► PayFast ──► store-api /payfast-itn (verified) ──► download token ──► signed URL
pg_cron ──► ops-api /cron/health (4×/day) and /cron/daily-report (18:00 SAST) ──► daily_reports ──► dashboard / email
```
Backend: Supabase project `commerce-network` (`mrunxptxavtompcnegkr`), functions `store-api` and `ops-api`.

## Routine operations (no Claude needed)
```bash
python3 factory/run.py                 # build/validate products (skips unchanged ones); --only slug,... --force
python3 engine/publish.py --verify-own # listing records; marks own-store listings live only if the URL returns 200
python3 engine/build_sites.py          # regenerate storefronts + dashboard
python3 engine/sync.py --files         # upload changed ZIPs (checksum-verified) and sync catalogue/listings
python3 engine/sync.py --work done "Added 5 products"   # log progress for the daily report
```
`commerce/.env` (never committed) holds `COMMERCE_UPLOAD_SECRET`. The factory source is backed up in the private `backups` bucket.

## Owner key (dashboard login)
Choose a long passphrase (24+ characters) and run this once in the Supabase SQL editor for project `commerce-network`:
```sql
update public.config set value = to_jsonb(encode(extensions.digest('YOUR-LONG-PASSPHRASE','sha256'),'hex')), updated_at = now()
where key = 'admin_key_sha256';
```
Then open `/dashboard/`, enter the passphrase and press **Load live data**. Only the hash is stored.

## Going live (in order)
1. Hosting that allows commercial use (Cloudflare Pages free, or Vercel Pro). Update `config/stores.json → site_base`, rebuild, sync.
2. PayFast live account → add secrets `PAYFAST_MERCHANT_ID`, `PAYFAST_MERCHANT_KEY`, `PAYFAST_PASSPHRASE` → `update config set value = jsonb_set(value,'{mode}','"live"') where key='payment';`
3. Resend: secret `RESEND_API_KEY`, then `update config set value = '{"provider":"resend","from":"Store <orders@yourdomain>","reply_to":null}' where key='email';`
4. Fill the legal disclosures in `config/stores.json → legal`, set `"mode": "live"`, rebuild (removes test banner, enables sitemap/indexing).

## Safety controls
- Orders become `paid` only after a verified PayFast ITN (signature, server validation, merchant, amount). No card data ever touches this system.
- Downloads: 7-day, 5-use tokens → 2-minute signed URLs from a private bucket.
- Kill switch (`config.kill_switch`): set automatically after 5 consecutive job errors or a weekly budget breach; pauses automation and checkout.
- Job frequency caps, idempotent rebuilds/uploads/syncs, unique product IDs (`PLD-/BZW-/ABL-###`), unique (product, channel) listings.

See STATUS.md, TASKS.md, DECISIONS.md, COSTS.md, DAILY_REPORT.md and research/.
