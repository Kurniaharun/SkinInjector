#!/usr/bin/env python3
"""Re-sync custom bundle skins ke data/catalog/."""

from __future__ import annotations

import sys
from pathlib import Path
from urllib.parse import quote

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from src.api_client import ApiClient
from src.catalog_store import write_json
from src.config import load_config


def main() -> int:
    cfg = load_config()
    api = ApiClient(cfg)
    api.load_endpoints()
    bundles = api.get_custom_bundles(refresh=True)
    write_json("custom_bundles", bundles)
    base = api.endpoint("getcustomSkinMenu")
    bundle_skins: dict[str, list] = {}
    total = 0
    for b in bundles:
        bid = str(b.get("id", ""))
        bname = str(b.get("name", ""))
        if not bid:
            continue
        menu = api._get(f"{base}{quote(bname, safe='')}")
        if not isinstance(menu, list):
            menu = []
        raw = api.enrich_custom_menu(menu)
        bundle_skins[bid] = raw
        total += len(raw)
        print(f"  {bid} {bname[:40]:40} -> {len(raw)} skin")
    write_json("custom_bundle_skins", bundle_skins)
    print(f"\nSelesai — {len(bundles)} bundle, {total} skin")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
