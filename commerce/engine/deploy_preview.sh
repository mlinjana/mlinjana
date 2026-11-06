#!/usr/bin/env bash
# Deploy commerce/site to the preview Worker "mlinjana-preview" (workers.dev only), never to mlinjanastudios.com.
# Refuses a live-mode build: previews must stay noindex and use the PayFast sandbox.
set -euo pipefail
cd "$(dirname "$0")/.."
grep -q '"mode": "staging"' config/stores.json || { echo "config/stores.json is not in staging mode: refusing to deploy a preview" >&2; exit 1; }
if [ -z "${CLOUDFLARE_API_TOKEN:-}" ] && [ -f .env ]; then
  CLOUDFLARE_API_TOKEN=$(grep '^CLOUDFLARE_API_TOKEN=' .env | cut -d= -f2-)
fi
export CLOUDFLARE_API_TOKEN CLOUDFLARE_ACCOUNT_ID="${CLOUDFLARE_ACCOUNT_ID:-da113ab5ce60706d4edf410a243e9b5f}"
WRANGLER=${WRANGLER:-npx --yes wrangler@4}
$WRANGLER deploy --config wrangler.preview.jsonc
