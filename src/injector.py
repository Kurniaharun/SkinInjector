"""Skin injection orchestration with step-by-step progress."""

from __future__ import annotations

import logging
from dataclasses import dataclass
from pathlib import Path
from typing import Optional

from .backup_manager import BackupManager
from .backends import StorageBackend
from .config import DOWNLOAD_DIR
from .downloader import Downloader
from .errors import InjectFailedError, ZipInvalidError
from .fs_utils import validate_skin_zip
from .models import SkinItem
from .progress import NullReporter, ProgressReporter

LOG = logging.getLogger(__name__)


@dataclass
class InjectResult:
    ok: bool
    skin: SkinItem
    zip_path: Path
    target: str
    files_count: int
    message: str


class Injector:
    def __init__(
        self,
        cfg: dict,
        backend: StorageBackend,
        downloader: Downloader | None = None,
    ) -> None:
        self.cfg = cfg
        self.backend = backend
        self.downloader = downloader or Downloader(cfg)
        self.backup = BackupManager(backend)

    def inject(
        self,
        skin: SkinItem,
        assets_path: str,
        package: str,
        dry_run: bool = False,
        reporter: Optional[ProgressReporter] = None,
    ) -> InjectResult:
        rep = reporter or NullReporter()
        if not skin.download_url:
            rep.finish(False, "Skin tidak punya download URL")
            raise InjectFailedError("Skin tidak punya download URL")

        rep.on_step("Memulai inject...", 2, skin.skin_name)
        rep.on_step("Backend: siap", 4, package)

        zip_path = self.downloader.download(
            skin.download_url,
            self.cfg["inject"].get("temp_zip_name", "IMB.zip"),
            reporter=rep,
        )

        rep.on_step("Memvalidasi ZIP...", 58, str(zip_path.name))
        try:
            members = validate_skin_zip(
                zip_path,
                min_bytes=int(self.cfg.get("download", {}).get("min_zip_bytes", 1024)),
            )
        except ZipInvalidError as e:
            rep.finish(False, str(e))
            raise

        rep.on_step(
            f"ZIP valid — {len(members)} file",
            65,
            f"{zip_path.stat().st_size // 1024} KB",
        )

        if dry_run:
            msg = f"[DRY-RUN] Siap inject {len(members)} file ke {assets_path}"
            rep.finish(True, msg)
            return InjectResult(
                ok=True,
                skin=skin,
                zip_path=zip_path,
                target=assets_path,
                files_count=len(members),
                message=msg,
            )

        hero_id = skin.id or skin.hero_name.replace(" ", "_")

        rep.on_step(
            "Apply ke folder MLBB...",
            72,
            assets_path[-50:],
        )
        ok = self.backend.unzip_replace(str(zip_path), assets_path)
        if not ok:
            rep.on_step("Inject gagal...", 88, "")
            if self.cfg.get("inject", {}).get("auto_rollback_on_fail", True):
                if self.cfg.get("inject", {}).get("backup_before_inject", False):
                    try:
                        self.backup.restore(package, hero_id, assets_path)
                        rep.on_step("Rollback selesai", 92, "")
                    except Exception as e:
                        LOG.error("Rollback gagal: %s", e)
            msg = "Inject gagal (unzip)."
            rep.finish(False, msg)
            raise InjectFailedError(msg)

        rep.on_step("Menyimpan log inject...", 90, "")
        self.backup.record_inject(
            package=package,
            hero_id=hero_id,
            hero_name=skin.hero_name,
            skin_name=skin.skin_name,
            files=members,
            source=skin.source,
        )

        rep.on_step("Membersihkan file temp...", 97, "")
        try:
            zip_path.unlink(missing_ok=True)
        except OSError:
            pass

        msg = f"Inject sukses: {skin.skin_name} ({len(members)} file)"
        rep.finish(True, msg)
        return InjectResult(
            ok=True,
            skin=skin,
            zip_path=zip_path,
            target=assets_path,
            files_count=len(members),
            message=msg,
        )

    def restore_default(
        self,
        package: str,
        hero_id: str,
        assets_path: str,
        reporter: Optional[ProgressReporter] = None,
    ) -> str:
        rep = reporter or NullReporter()
        rep.on_step("Restore default skin...", 10, hero_id)
        restored = self.backup.restore(package, hero_id, assets_path)
        if restored > 0:
            msg = f"Restore default sukses ({restored} file)"
            rep.finish(True, msg)
            return msg
        msg = "Restore gagal — backup kosong"
        rep.finish(False, msg)
        raise InjectFailedError(msg + ". Coba hapus file mod manual.")

    def cleanup_temp(self) -> None:
        for p in DOWNLOAD_DIR.glob("*.zip"):
            try:
                p.unlink()
            except OSError:
                pass
