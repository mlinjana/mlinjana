#!/usr/bin/env bash
# Deploy commerce/site to the Cloudflare Worker "commerce-network" (static assets only).
# Needs CLOUDFLARE_API_TOKEN (Workers edit scope) in the environment or in commerce/.env — never committed.
set -euo pipefail
cd "$(dirname "$0")/.."
if [ -z "${CLOUDFLARE_API_TOKEN:-}" ] && [ -f .env ]; then
  CLOUDFLARE_API_TOKEN=$(grep '^CLOUDFLARE_API_TOKEN=' .env | cut -d= -f2-)
fi
export CLOUDFLARE_API_TOKEN CLOUDFLARE_ACCOUNT_ID="${CLOUDFLARE_ACCOUNT_ID:-da113ab5ce60706d4edf410a243e9b5f}"
WRANGLER=${WRANGLER:-npx --yes wrangler@4}
$WRANGLER deploy --config wrangler.jsonc
