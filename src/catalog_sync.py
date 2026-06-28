"""Full scrape API → local JSON catalog + incremental updater."""

from __future__ import annotations

import logging
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Any, Callable, Optional
from urllib.parse import quote

from .api_client import EFFECT_CATEGORIES, HERO_ROLES, ApiClient
from .catalog_store import CATALOG_DIR, write_json, write_meta
from .errors import ApiError
from .name_resolver import build_name_corpus, resolve_upgrade_menu_label

LOG = logging.getLogger(__name__)

ProgressCb = Callable[[str, int, int], None]


class CatalogSync:
    """Ambil semua data dari API dan simpan ke data/catalog/*.json."""

    def __init__(self, cfg: dict) -> None:
        self.cfg = cfg
        self.remote = ApiClient(cfg)

    def sync_full(
        self,
        on_progress: Optional[ProgressCb] = None,
    ) -> dict[str, Any]:
        def prog(msg: str, cur: int, total: int = 100) -> None:
            if on_progress:
                on_progress(msg, cur, total)

        CATALOG_DIR.mkdir(parents=True, exist_ok=True)
        prog("Memuat endpoint API...", 2, 100)

        self.remote.load_endpoints(refresh=True)

        prog("Mengambil daftar hero...", 5, 100)
        heroes_url = self.remote.endpoint("getHeroes")
        heroes = self.remote._get(heroes_url)
        if not isinstance(heroes, dict):
            raise ApiError("Format getHeroes tidak valid")
        write_json("heroes", heroes)

        prog("Mengambil menu upgrade...", 12, 100)
        upgrade_menu = self.remote._get(self.remote.endpoint("getlistUpgradeSkins"))
        write_json("upgrade_menu", upgrade_menu)

        upgrade_skins: dict[str, list] = {}
        total_u = max(len(upgrade_menu), 1)
        done_u = 0

        def _fetch_upgrade(entry: dict) -> tuple[str, list]:
            cat = str(entry.get("heroName") or entry.get("name") or "")
            if not cat:
                return "", []
            try:
                url = self.remote.endpoint("getUpgradeSkins")
                raw = self.remote._post(url, {"category": cat})
                if isinstance(raw, dict):
                    raw = raw.get("data", raw.get("skins", [raw]))
                if not isinstance(raw, list):
                    raw = []
                return cat, raw
            except ApiError as e:
                LOG.warning("upgrade %s: %s", cat, e)
                return cat, []

        workers = min(8, max(2, total_u // 8))
        with ThreadPoolExecutor(max_workers=workers) as pool:
            futures = {pool.submit(_fetch_upgrade, e): e for e in upgrade_menu}
            for fut in as_completed(futures):
                done_u += 1
                cat, raw_list = fut.result()
                if cat and raw_list:
                    upgrade_skins[cat] = raw_list
                if done_u % 3 == 0 or done_u == total_u:
                    pct = 12 + int(done_u * 28 / total_u)
                    prog(f"Upgrade skin ({done_u}/{total_u})", pct, 100)

        write_json("upgrade_skins", upgrade_skins)

        prog("Mengambil custom bundle...", 42, 100)
        bundles = self.remote._get(self.remote.endpoint("getCustomSkins"))
        if not isinstance(bundles, list):
            bundles = []
        write_json("custom_bundles", bundles)

        bundle_skins: dict[str, list] = {}
        total_b = max(len(bundles), 1)
        for i, bundle in enumerate(bundles, 1):
            bid = str(bundle.get("id", ""))
            bname = str(bundle.get("name", ""))
            if not bid:
                continue
            try:
                base = self.remote.endpoint("getcustomSkinMenu")
                raw = self.remote._get(f"{base}{quote(bname, safe='')}")
                if not isinstance(raw, list):
                    raw = []
                raw = self.remote.enrich_custom_menu(raw)
                bundle_skins[bid] = raw
            except ApiError as e:
                LOG.warning("bundle %s: %s", bname, e)
            pct = 42 + int(i * 10 / total_b)
            prog(f"Custom: {bname[:28]}", pct, 100)

        write_json("custom_bundle_skins", bundle_skins)

        prog("Mengambil effects...", 55, 100)
        effects: dict[str, list] = {}
        effect_total = len(EFFECT_CATEGORIES)
        for i, (cat_name, _src) in enumerate(EFFECT_CATEGORIES, 1):
            try:
                url = self.remote.endpoint("getEmotes")
                raw = self.remote._post(url, {"category": cat_name})
                if isinstance(raw, dict):
                    raw = raw.get("data", raw.get("items", []))
                if not isinstance(raw, list):
                    raw = []
                effects[cat_name] = raw
            except ApiError as e:
                LOG.warning("effect %s: %s", cat_name, e)
                effects[cat_name] = []
            pct = 55 + int(i * 15 / effect_total)
            prog(f"Effect: {cat_name[:24]}", pct, 100)

        write_json("effects", effects)

        prog("Mengambil pengumuman...", 72, 100)
        announcements = self.remote._get(self.remote.endpoint("getAnnouncement"))
        if not isinstance(announcements, list):
            announcements = []
        write_json("announcements", announcements)

        prog("Mengambil kategori role...", 75, 100)
        try:
            roles = self.remote._get(self.remote.endpoint("getCategory1"))
            if not isinstance(roles, list):
                roles = [{"name": r} for r in HERO_ROLES]
        except ApiError:
            roles = [{"name": r} for r in HERO_ROLES]
        write_json("role_categories", roles)

        role_names = [str(x.get("name", "")) for x in roles if x.get("name")] or list(HERO_ROLES)
        heroes_by_role: dict[str, list[str]] = {}
        total_r = max(len(role_names), 1)

        for i, role in enumerate(role_names, 1):
            try:
                heroes_by_role[role] = self.remote.list_heroes_by_role(role, refresh=True)
            except ApiError as e:
                LOG.warning("role %s: %s", role, e)
                heroes_by_role[role] = []
            pct = 75 + int(i * 12 / total_r)
            prog(f"Role: {role}", pct, 100)

        write_json("heroes_by_role", heroes_by_role)

        prog("Membangun name corpus...", 90, 100)
        entries: list[dict] = []
        for skins in heroes.values():
            if isinstance(skins, list):
                entries.extend(skins)
        entries.extend(upgrade_menu)
        corpus = sorted(build_name_corpus(entries))
        write_json("name_corpus", corpus)

        upgrade_labels = [
            resolve_upgrade_menu_label(x, set(corpus)) for x in upgrade_menu
        ]
        write_json("upgrade_labels", upgrade_labels)

        effect_count = sum(len(v) for v in effects.values())
        upgrade_count = sum(len(v) for v in upgrade_skins.values())
        bundle_count = sum(len(v) for v in bundle_skins.values())

        meta = write_meta(
            {
                "counts": {
                    "heroes": len(heroes),
                    "upgrade_entries": len(upgrade_menu),
                    "upgrade_skins": upgrade_count,
                    "custom_bundles": len(bundles),
                    "custom_skins": bundle_count,
                    "effects": effect_count,
                    "announcements": len(announcements),
                    "roles": len(role_names),
                },
            }
        )

        prog("Selesai", 100, 100)
        LOG.info("Catalog sync selesai: %s", meta.get("counts"))
        return meta
