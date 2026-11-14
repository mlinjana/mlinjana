"""Prepare a strictly non-transactional storefront preview build.

Only run inside an ephemeral CI workspace, never on a production checkout host.
The preview uses noindex, disables checkout UI and points browser API calls at
an intentionally non-routable test hostname.
"""
import json
from pathlib import Path

root = Path(__file__).resolve().parents[1]
path = root / "config/stores.json"
cfg = json.loads(path.read_text(encoding="utf-8"))
if cfg.get("mode") != "live":
    raise SystemExit("Expected the checked-in production config before preview conversion")
cfg["mode"] = "staging"
cfg["checkout"] = "paused"
cfg["site_base"] = "https://preview.invalid"
cfg["api_base"] = "https://api.invalid/functions/v1"
path.write_text(json.dumps(cfg, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
print("Ephemeral preview config prepared: checkout paused, API isolated, noindex.")
