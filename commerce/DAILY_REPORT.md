# DAILY REPORT

The report is generated automatically at **18:00 SAST** by the `ops-api` function (pg_cron) from live database records, stored in the `daily_reports` table, and shown on the owner dashboard (`/dashboard/`, owner key required).

**Delivery:**
- Dashboard: always.
- Email: automatic once `RESEND_API_KEY` + sender are configured (no Claude usage).
- Until then: no automatic email. A test report was delivered through your connected Gmail on 2026-10-28 (verified in your mailbox).
  A Claude routine could forward it daily, but routines created from this session can't carry the Gmail/Supabase connectors —
  create it in the claude.ai routines UI with both connectors attached if you want that (small daily Claude usage).

## Latest (2026-10-28, first run)
| Measure | Value |
|---|---|
| Stores built / live / staging | 3 / 0 / 3 |
| Products generated / validated | 60 / 60 |
| Products published (verified live listing) | 0 |
| Failed listings | 0 |
| Listings awaiting your authorisation | 240 |
| Real orders · revenue | 0 · R0.00 |

Note: page views in the first report came from a pre-deployment local test and are not real traffic.
