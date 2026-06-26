"""Configuration loader."""

from __future__ import annotations

import os
from pathlib import Path
from typing import Any

import yaml

from .errors import ConfigError

ROOT_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = ROOT_DIR / "data"
CACHE_DIR = DATA_DIR / "cache"
DOWNLOAD_DIR = DATA_DIR / "downloads"
BACKUP_DIR = DATA_DIR / "backups"
LOG_DIR = ROOT_DIR / "logs"
INDEX_PATH = DATA_DIR / "heroes_index.json"


def _ensure_dirs() -> None:
    for d in (DATA_DIR, CACHE_DIR, DOWNLOAD_DIR, BACKUP_DIR, LOG_DIR):
        d.mkdir(parents=True, exist_ok=True)


def load_config(path: Path | None = None) -> dict[str, Any]:
    _ensure_dirs()
    cfg_path = path or (ROOT_DIR / "config" / "default.yaml")
    if not cfg_path.exists():
        raise ConfigError(f"Config tidak ditemukan: {cfg_path}")
    with open(cfg_path, encoding="utf-8") as f:
        cfg = yaml.safe_load(f) or {}
    env_mode = os.environ.get("MLBB_ACCESS_MODE")
    if env_mode:
        cfg.setdefault("access", {})["mode"] = env_mode
    return cfg


def mlbb_assets_path(cfg: dict[str, Any], package: str) -> str:
    root = cfg["paths"]["storage_root"].rstrip("/")
    sub = cfg["paths"]["mlbb_assets_subpath"].strip("/")
    return f"{root}/Android/data/{package}/{sub}"
