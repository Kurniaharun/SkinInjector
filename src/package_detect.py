"""Detect installed MLBB package."""

from __future__ import annotations

from typing import Optional

from .config import mlbb_assets_path
from .errors import NoMLBBInstalledError
from .fs_utils import pkg_installed


def detect_package(cfg: dict) -> str:
    for pkg in cfg.get("packages", []):
        if pkg_installed(pkg):
            return pkg
    raise NoMLBBInstalledError(
        "MLBB tidak terdeteksi. Pastikan salah satu terinstall:\n"
        + "\n".join(f"  - {p}" for p in cfg.get("packages", []))
    )


def get_assets_path(cfg: dict, package: Optional[str] = None) -> str:
    pkg = package or detect_package(cfg)
    return mlbb_assets_path(cfg, pkg)
