"""Backup and restore default skin files."""

from __future__ import annotations

import json
import logging
import shutil
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

from .backends import StorageBackend
from .config import BACKUP_DIR
from .errors import BackupNotFoundError
from .models import BackupManifest

LOG = logging.getLogger(__name__)


class BackupManager:
    def __init__(self, backend: StorageBackend) -> None:
        self.backend = backend

    def _hero_dir(self, package: str, hero_id: str) -> Path:
        safe = hero_id.replace("/", "_") or "unknown"
        return BACKUP_DIR / package / safe

    def manifest_path(self, package: str, hero_id: str) -> Path:
        return self._hero_dir(package, hero_id) / "manifest.json"

    def snapshot_dir(self, package: str, hero_id: str) -> Path:
        return self._hero_dir(package, hero_id) / "files"

    def list_backups(self, package: Optional[str] = None) -> list[BackupManifest]:
        results: list[BackupManifest] = []
        root = BACKUP_DIR
        if not root.exists():
            return results
        for pkg_dir in root.iterdir():
            if not pkg_dir.is_dir():
                continue
            if package and pkg_dir.name != package:
                continue
            for hero_dir in pkg_dir.iterdir():
                mf = hero_dir / "manifest.json"
                if mf.exists():
                    try:
                        with open(mf, encoding="utf-8") as f:
                            results.append(BackupManifest.from_dict(json.load(f)))
                    except (json.JSONDecodeError, OSError) as e:
                        LOG.warning("Skip corrupt manifest %s: %s", mf, e)
        return results

    def ensure_backup(
        self,
        package: str,
        hero_id: str,
        hero_name: str,
        zip_members: list[str],
        assets_path: str,
        reporter=None,
    ) -> BackupManifest:
        """Backup existing game files that would be overwritten."""
        snap = self.snapshot_dir(package, hero_id)
        snap.mkdir(parents=True, exist_ok=True)
        backed: list[str] = []

        existing_manifest = self.manifest_path(package, hero_id)
        if existing_manifest.exists():
            try:
                with open(existing_manifest, encoding="utf-8") as f:
                    old = BackupManifest.from_dict(json.load(f))
                if old.files:
                    LOG.info("Backup sudah ada untuk hero %s", hero_id)
                    return old
            except (json.JSONDecodeError, OSError):
                pass

        candidates = []
        for member in zip_members:
            rel = member.lstrip("/").replace("\\", "/")
            if rel:
                candidates.append(rel)

        total = len(candidates)
        for i, rel in enumerate(candidates, 1):
            if reporter:
                reporter.on_backup_file(i, total, rel)
            src_game = f"{assets_path.rstrip('/')}/{rel}"
            dst_local = snap / rel
            if self.backend.exists(src_game):
                dst_local.parent.mkdir(parents=True, exist_ok=True)
                if self.backend.copy_file(src_game, str(dst_local)):
                    backed.append(rel)
                    LOG.debug("Backed up %s", rel)

        manifest = BackupManifest(
            hero_id=hero_id,
            hero_name=hero_name,
            skin_name="(original)",
            package=package,
            injected_at=datetime.now(timezone.utc).isoformat(),
            files=backed,
            source="pre-inject",
        )
        with open(self.manifest_path(package, hero_id), "w", encoding="utf-8") as f:
            json.dump(manifest.to_dict(), f, indent=2, ensure_ascii=False)
        LOG.info("Backup %d file untuk hero %s", len(backed), hero_name)
        return manifest

    def record_inject(
        self,
        package: str,
        hero_id: str,
        hero_name: str,
        skin_name: str,
        files: list[str],
        source: str,
    ) -> None:
        path = self.manifest_path(package, hero_id)
        keep_files = files
        if path.exists():
            try:
                with open(path, encoding="utf-8") as f:
                    old = BackupManifest.from_dict(json.load(f))
                if old.files and old.source == "pre-inject":
                    keep_files = old.files
            except (json.JSONDecodeError, OSError):
                pass
        manifest = BackupManifest(
            hero_id=hero_id,
            hero_name=hero_name,
            skin_name=skin_name,
            package=package,
            injected_at=datetime.now(timezone.utc).isoformat(),
            files=keep_files,
            source=source,
        )
        path.parent.mkdir(parents=True, exist_ok=True)
        with open(path, "w", encoding="utf-8") as f:
            json.dump(manifest.to_dict(), f, indent=2, ensure_ascii=False)

    def restore(self, package: str, hero_id: str, assets_path: str) -> int:
        mf_path = self.manifest_path(package, hero_id)
        if not mf_path.exists():
            raise BackupNotFoundError(f"Tidak ada backup untuk hero id={hero_id}")
        with open(mf_path, encoding="utf-8") as f:
            manifest = BackupManifest.from_dict(json.load(f))
        snap = self.snapshot_dir(package, hero_id)
        restored = 0
        for rel in manifest.files:
            src_local = snap / rel
            dst_game = f"{assets_path.rstrip('/')}/{rel}"
            if src_local.is_file():
                if self.backend.copy_file(str(src_local), dst_game):
                    restored += 1
            else:
                LOG.warning("Backup file hilang: %s", src_local)
        LOG.info("Restored %d/%d files", restored, len(manifest.files))
        return restored

    def restore_by_manifest_files(self, package: str, hero_id: str, assets_path: str) -> int:
        """Restore only — alias."""
        return self.restore(package, hero_id, assets_path)

    def remove_injected_files(self, package: str, hero_id: str, assets_path: str) -> int:
        """Delete mod files listed in manifest (fallback if no backup snapshot)."""
        mf_path = self.manifest_path(package, hero_id)
        if not mf_path.exists():
            raise BackupNotFoundError(f"Tidak ada manifest inject untuk {hero_id}")
        with open(mf_path, encoding="utf-8") as f:
            manifest = BackupManifest.from_dict(json.load(f))
        removed = 0
        for rel in manifest.files:
            target = f"{assets_path.rstrip('/')}/{rel}"
            if self.backend.exists(target):
                if self.backend.delete(target):
                    removed += 1
        return removed

    def delete_backup(self, package: str, hero_id: str) -> None:
        d = self._hero_dir(package, hero_id)
        if d.exists():
            shutil.rmtree(d)
