"""Local JSON catalog storage — offline skin database."""

from __future__ import annotations

import json
import logging
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from .config import DATA_DIR
from .errors import CatalogNotFoundError

LOG = logging.getLogger(__name__)

CATALOG_DIR = DATA_DIR / "catalog"

FILES = {
    "meta": "meta.json",
    "heroes": "heroes_groups.json",
    "upgrade_menu": "upgrade_menu.json",
    "upgrade_skins": "upgrade_skins.json",
    "custom_bundles": "custom_bundles.json",
    "custom_bundle_skins": "custom_bundle_skins.json",
    "effects": "effects.json",
    "announcements": "announcements.json",
    "role_categories": "role_categories.json",
    "heroes_by_role": "heroes_by_role.json",
    "name_corpus": "name_corpus.json",
    "upgrade_labels": "upgrade_labels.json",
}


def catalog_ready() -> bool:
    """True jika scrape minimal sudah ada."""
    required = ("meta", "heroes", "upgrade_menu")
    return all((CATALOG_DIR / FILES[k]).is_file() for k in required)


def catalog_path(key: str) -> Path:
    if key not in FILES:
        raise KeyError(f"Unknown catalog key: {key}")
    return CATALOG_DIR / FILES[key]


def read_json(key: str, default: Any = None) -> Any:
    path = catalog_path(key)
    if not path.is_file():
        if default is not None:
            return default
        raise CatalogNotFoundError(
            f"Katalog '{key}' belum ada. Jalankan: python main.py update"
        )
    try:
        with open(path, encoding="utf-8") as f:
            return json.load(f)
    except (json.JSONDecodeError, OSError) as e:
        raise CatalogNotFoundError(f"Katalog corrupt ({key}): {e}") from e


def write_json(key: str, data: Any) -> None:
    CATALOG_DIR.mkdir(parents=True, exist_ok=True)
    path = catalog_path(key)
    tmp = path.with_suffix(".tmp")
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, separators=(",", ":"))
    tmp.replace(path)


def read_meta() -> dict[str, Any]:
    return read_json("meta", default={})


def write_meta(extra: dict[str, Any] | None = None) -> dict[str, Any]:
    meta = {
        "updated_at": datetime.now(timezone.utc).isoformat(),
        "version": 1,
    }
    if extra:
        meta.update(extra)
    write_json("meta", meta)
    return meta


def catalog_summary() -> str:
    if not catalog_ready():
        return "belum di-scrape"
    meta = read_meta()
    ts = meta.get("updated_at", "?")[:19].replace("T", " ")
    counts = meta.get("counts", {})
    parts = [f"update {ts}"]
    if counts:
        parts.append(
            f"{counts.get('heroes', '?')} hero · "
            f"{counts.get('upgrade_skins', '?')} upgrade · "
            f"{counts.get('effects', '?')} effect"
        )
    return " · ".join(parts)
