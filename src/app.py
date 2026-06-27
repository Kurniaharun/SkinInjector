"""Application orchestrator."""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import Callable, Optional

from .catalog_store import catalog_ready, catalog_summary
from .catalog_sync import CatalogSync
from .local_catalog import LocalCatalog
from .backends import StorageBackend, pick_backend
from .backup_manager import BackupManager
from .config import load_config
from .downloader import Downloader
from .errors import InjectorError, NoMLBBInstalledError, NoStorageAccessError
from .fs_utils import free_bytes, has_root, has_shizuku, is_android, setup_logging
from .injector import Injector
from .models import PreflightResult, SkinItem
from .progress import NullReporter, ProgressReporter
from .package_detect import detect_package, get_assets_path
from .search import SearchIndex
from .config import LOG_DIR, ROOT_DIR

LOG = logging.getLogger(__name__)


@dataclass
class BatchInjectResult:
    ok: list[tuple[str, str]] = field(default_factory=list)
    failed: list[tuple[str, str]] = field(default_factory=list)

    @property
    def success_count(self) -> int:
        return len(self.ok)

    @property
    def fail_count(self) -> int:
        return len(self.failed)


class App:
    def __init__(self, mode: str | None = None) -> None:
        self.cfg = load_config()
        self.mode_override = mode
        self.backend: Optional[StorageBackend] = None
        self.api = LocalCatalog(self.cfg)
        self.search = SearchIndex(self.api, self.cfg)
        self.injector: Optional[Injector] = None
        self.package: Optional[str] = None
        self.assets_path: Optional[str] = None
        self.preflight: Optional[PreflightResult] = None
        self._logging_ready = False

    def init(self, force: bool = False) -> PreflightResult:
        if self.preflight and not force:
            return self.preflight

        if not self._logging_ready:
            setup_logging(LOG_DIR, quiet_console=True)
            self._logging_ready = True
        messages: list[str] = []
        ok = True

        if has_root():
            messages.append("[OK] Root (su) terdeteksi")
        else:
            messages.append("[--] Root tidak terdeteksi")

        if has_shizuku():
            messages.append("[OK] Shizuku terdeteksi")
        else:
            messages.append("[--] Shizuku tidak terdeteksi")

        try:
            self.backend = pick_backend(self.cfg, self.mode_override)
            messages.append(f"[OK] Backend aktif: {self.backend.name.upper()}")
        except NoStorageAccessError as e:
            ok = False
            messages.append(f"[!!] {e}")

        try:
            self.package = detect_package(self.cfg)
            self.assets_path = get_assets_path(self.cfg, self.package)
            messages.append(f"[OK] MLBB: {self.package}")
            messages.append(f"     Assets: {self.assets_path}")
        except NoMLBBInstalledError as e:
            if is_android():
                ok = False
                messages.append(f"[!!] {e}")
            else:
                messages.append("[i] MLBB skip (bukan device Android)")
                self.package = self.cfg["packages"][0]
                self.assets_path = get_assets_path(self.cfg, self.package)

        if self.backend and self.assets_path:
            if self.backend.can_write(self.assets_path):
                messages.append("[OK] Path assets writable")
            else:
                messages.append("[!!] Path assets tidak bisa ditulis")
                ok = False

        free = free_bytes(str(ROOT_DIR))
        if free:
            messages.append(f"[OK] Free space: {free // (1024 * 1024)} MB")

        if catalog_ready():
            try:
                self.api.load_endpoints()
                self.api.warmup()
                messages.append(f"[OK] Katalog lokal — {catalog_summary()}")
            except Exception as e:
                messages.append(f"[!!] Katalog: {e}")
                ok = False
        else:
            messages.append("[!!] Katalog belum ada — jalankan: python main.py update")
            ok = False

        dl = Downloader(self.cfg)
        if dl._want_aria():
            messages.append(f"[OK] Download aria2 x{dl.aria_splits}")
        else:
            messages.append("[i] Download HTTP — pkg install aria2 untuk turbo")

        if self.backend:
            self.injector = Injector(self.cfg, self.backend, dl)

        self.preflight = PreflightResult(
            ok=ok,
            mode=self.mode_override or self.cfg.get("access", {}).get("mode", "auto"),
            backend_name=self.backend.name if self.backend else "none",
            package=self.package,
            assets_path=self.assets_path,
            messages=messages,
        )
        return self.preflight

    def inject_skin(
        self,
        skin: SkinItem,
        dry_run: bool = False,
        reporter: ProgressReporter | None = None,
    ) -> str:
        if not self.injector or not self.package or not self.assets_path:
            raise InjectorError("App belum di-init dengan benar")
        result = self.injector.inject(
            skin,
            self.assets_path,
            self.package,
            dry_run=dry_run,
            reporter=reporter or NullReporter(),
        )
        return result.message

    def inject_batch(
        self,
        skins: list[tuple[str, SkinItem]],
        *,
        on_hero_start: Callable[[int, int, str, SkinItem], None] | None = None,
        on_hero_done: Callable[[int, int, str, bool, str], None] | None = None,
    ) -> BatchInjectResult:
        if not self.injector or not self.package or not self.assets_path:
            raise InjectorError("App belum di-init dengan benar")

        total = len(skins)
        result = BatchInjectResult()
        for i, (hero, skin) in enumerate(skins, 1):
            if on_hero_start:
                on_hero_start(i, total, hero, skin)
            try:
                msg = self.inject_skin(skin, reporter=NullReporter())
                result.ok.append((hero, msg))
                if on_hero_done:
                    on_hero_done(i, total, hero, True, msg)
            except Exception as e:
                err = str(e)
                result.failed.append((hero, err))
                if on_hero_done:
                    on_hero_done(i, total, hero, False, err)
        return result

    def restore_default(
        self,
        hero_id: str,
        reporter: ProgressReporter | None = None,
    ) -> str:
        if not self.injector or not self.package or not self.assets_path:
            raise InjectorError("App belum di-init")
        return self.injector.restore_default(
            self.package,
            hero_id,
            self.assets_path,
            reporter=reporter or NullReporter(),
        )

    def list_backups(self):
        if not self.backend:
            return []
        return BackupManager(self.backend).list_backups(self.package)

    def update_catalog(
        self,
        on_progress=None,
    ) -> str:
        """Scrape API → JSON lokal (butuh internet)."""
        sync = CatalogSync(self.cfg)
        meta = sync.sync_full(on_progress=on_progress)
        self.api.invalidate_cache()
        self.api.warmup()
        counts = meta.get("counts", {})
        return (
            f"Katalog di-update — {counts.get('heroes', '?')} hero, "
            f"{counts.get('upgrade_skins', '?')} upgrade, "
            f"{counts.get('effects', '?')} effect"
        )

    def refresh_all(self, full: bool = True) -> str:
        """Rebuild search index dari katalog lokal."""
        if not catalog_ready():
            return "Katalog belum ada — jalankan: python main.py update"
        if hasattr(self.api, "invalidate_cache"):
            self.api.invalidate_cache()
        self.api.warmup()
        if full:
            n = self.search.build_full(refresh=True)
        else:
            n = self.search.build_light(refresh=True)
        return f"Index di-refresh ({n} skin)"
