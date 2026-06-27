"""Offline catalog — baca JSON lokal, tanpa koneksi API."""

from __future__ import annotations

import logging
from typing import Any, Optional

from .api_client import EFFECT_CATEGORIES, HERO_ROLES
from .catalog_store import catalog_ready, read_json
from .errors import CatalogNotFoundError
from .models import SkinItem
from .name_resolver import resolve_category_label
from .skin_grade import SKIN_GRADES, detect_skin_grade

LOG = logging.getLogger(__name__)


class LocalCatalog:
    """Drop-in pengganti ApiClient — semua data dari data/catalog/."""

    def __init__(self, cfg: dict) -> None:
        self.cfg = cfg
        self._name_corpus: set[str] | None = None
        self._heroes: dict[str, list] | None = None

    def _require(self) -> None:
        if not catalog_ready():
            raise CatalogNotFoundError(
                "Katalog belum di-scrape.\n"
                "Jalankan: python main.py update"
            )

    def load_endpoints(self, refresh: bool = False) -> dict[str, str]:
        """No-op — mode offline tidak butuh endpoint."""
        self._require()
        return {}

    def name_corpus(self, refresh: bool = False) -> set[str]:
        if self._name_corpus is not None and not refresh:
            return self._name_corpus
        self._require()
        try:
            raw = read_json("name_corpus", default=[])
            self._name_corpus = set(raw) if raw else set()
        except CatalogNotFoundError:
            self._name_corpus = set()
        if not self._name_corpus:
            self._name_corpus = self._build_corpus_fallback()
        return self._name_corpus

    def _build_corpus_fallback(self) -> set[str]:
        from .name_resolver import build_name_corpus

        entries: list[dict] = []
        try:
            for skins in self.get_hero_groups().values():
                if isinstance(skins, list):
                    entries.extend(skins)
        except Exception:
            pass
        try:
            entries.extend(self.get_upgrade_menu())
        except Exception:
            pass
        return build_name_corpus(entries)

    def upgrade_menu_label(self, entry: dict[str, Any]) -> str:
        return resolve_category_label(entry, self.name_corpus())

    def get_upgrade_menu(self, refresh: bool = False) -> list[dict[str, Any]]:
        self._require()
        return read_json("upgrade_menu")

    def get_upgrade_skins(self, hero_name: str, refresh: bool = False) -> list[SkinItem]:
        self._require()
        all_up = read_json("upgrade_skins", default={})
        raw = all_up.get(hero_name, [])
        if not raw:
            for key, val in all_up.items():
                if key.lower() == hero_name.lower():
                    raw = val
                    break
        corpus = self.name_corpus()
        return [
            SkinItem.from_upgrade_entry(x, hero_name, corpus)
            for x in raw
            if x.get("url") or x.get("downloadLink")
        ]

    def get_heroes_flat(self, refresh: bool = False) -> list[SkinItem]:
        groups = self.get_hero_groups(refresh=refresh)
        corpus = self.name_corpus(refresh=refresh)
        flat: list[SkinItem] = []
        for hero_key, entries in groups.items():
            if not isinstance(entries, list):
                continue
            for x in entries:
                item = SkinItem.from_hero_entry(x, hero=hero_key, corpus=corpus)
                if item.download_url:
                    flat.append(item)
        return flat

    def get_custom_bundles(self, refresh: bool = False) -> list[dict[str, Any]]:
        self._require()
        return read_json("custom_bundles")

    def get_custom_bundle_skins(
        self,
        bundle_id: str,
        bundle_name: str = "",
        refresh: bool = False,
    ) -> list[SkinItem]:
        self._require()
        all_b = read_json("custom_bundle_skins", default={})
        raw = all_b.get(bundle_id, [])
        corpus = self.name_corpus()
        return [
            SkinItem.from_bundle_entry(x, bundle_name, corpus)
            for x in raw
            if x.get("downloadLink") or x.get("url")
        ]

    def search_custom_bundles(self, query: str, limit: int = 20) -> list[SkinItem]:
        q = query.lower().strip()
        if not q:
            return []
        out: list[SkinItem] = []
        for bundle in self.get_custom_bundles():
            name = str(bundle.get("name", ""))
            if q not in name.lower():
                continue
            try:
                skins = self.get_custom_bundle_skins(str(bundle.get("id", "")), name)
                out.extend(skins[:limit])
            except Exception as e:
                LOG.warning("custom bundle %s: %s", name, e)
        if len(out) < limit:
            for bundle in self.get_custom_bundles():
                bid = str(bundle.get("id", ""))
                bname = str(bundle.get("name", ""))
                try:
                    for skin in self.get_custom_bundle_skins(bid, bname):
                        if q in skin.label().lower():
                            out.append(skin)
                            if len(out) >= limit:
                                return out
                except Exception:
                    pass
        return out[:limit]

    def get_custom_skins(self, refresh: bool = False) -> list[SkinItem]:
        return [
            SkinItem.from_custom_entry(x, self.name_corpus(refresh=refresh))
            for x in self.get_custom_bundles(refresh=refresh)
        ]

    def get_role_categories(self, refresh: bool = False) -> list[dict[str, Any]]:
        self._require()
        return read_json("role_categories", default=[{"name": r} for r in HERO_ROLES])

    def list_heroes_by_role(self, role: str, refresh: bool = False) -> list[str]:
        self._require()
        by_role = read_json("heroes_by_role", default={})
        names = by_role.get(role, [])
        if not names:
            for key, val in by_role.items():
                if key.lower() == role.lower():
                    return val
        return names

    def get_announcements(self, refresh: bool = False) -> list[dict[str, Any]]:
        self._require()
        return read_json("announcements", default=[])

    def get_effects(self, category: str, refresh: bool = False) -> list[SkinItem]:
        self._require()
        all_fx = read_json("effects", default={})
        raw = all_fx.get(category, [])
        corpus = self.name_corpus()
        return [
            SkinItem.from_effect_entry(x, corpus=corpus)
            for x in raw
            if x.get("downloadLink") or x.get("url")
        ]

    def list_effect_categories(self) -> list[tuple[str, str]]:
        return list(EFFECT_CATEGORIES)

    def search_effects(self, query: str, limit_per_cat: int = 12) -> list[SkinItem]:
        q = query.lower().strip()
        if not q:
            return []
        results: list[SkinItem] = []
        for cat_name, _src in EFFECT_CATEGORIES:
            for item in self.get_effects(cat_name):
                if q in item.skin_name.lower() or q in item.category.lower():
                    results.append(item)
                    if len([r for r in results if r.category == cat_name]) >= limit_per_cat:
                        break
        return results

    def list_backup_skins(self, hero_name: str | None = None, refresh: bool = False) -> list[SkinItem]:
        corpus = self.name_corpus(refresh=refresh)
        groups = self.get_hero_groups(refresh=refresh)
        out: list[SkinItem] = []
        heroes = [hero_name] if hero_name else sorted(groups.keys(), key=str.lower)
        for hero in heroes:
            entries = groups.get(hero, [])
            if not entries and hero_name:
                for key, val in groups.items():
                    if key.lower() == hero_name.lower():
                        entries = val
                        hero = key
                        break
            for x in entries:
                raw = str(x.get("heroname", x.get("name", ""))).lower()
                dl = str(x.get("downloadLink", "")).lower()
                if "backup" in raw or "backup" in dl:
                    item = SkinItem.from_hero_entry(x, hero=hero, corpus=corpus)
                    item.source = "backup"
                    if item.download_url:
                        out.append(item)
        return out

    def get_categories(self) -> list[dict[str, Any]]:
        return self.get_role_categories()

    def get_hero_groups(self, refresh: bool = False) -> dict[str, list[dict[str, Any]]]:
        if self._heroes is not None and not refresh:
            return self._heroes
        self._require()
        self._heroes = read_json("heroes")
        return self._heroes

    def list_hero_names(self, refresh: bool = False) -> list[str]:
        groups = self.get_hero_groups(refresh=refresh)
        return sorted(groups.keys(), key=str.lower)

    def get_skins_for_hero(self, hero_name: str, refresh: bool = False) -> list[SkinItem]:
        groups = self.get_hero_groups(refresh=refresh)
        entries = groups.get(hero_name, [])
        if not entries:
            for key, val in groups.items():
                if key.lower() == hero_name.lower():
                    entries = val
                    break
        skins: list[SkinItem] = []
        corpus = self.name_corpus(refresh=refresh)
        for x in entries:
            item = SkinItem.from_hero_entry(x, hero=hero_name, corpus=corpus)
            if item.download_url:
                skins.append(item)
        return skins

    def search_hero_names(self, query: str) -> list[str]:
        q = query.lower().strip()
        if not q:
            return self.list_hero_names()
        return [n for n in self.list_hero_names() if q in n.lower()]

    def search_upgrade_entries(self, query: str) -> list[dict[str, Any]]:
        q = query.lower().strip()
        menu = self.get_upgrade_menu()
        if not q:
            return menu
        out: list[dict[str, Any]] = []
        for x in menu:
            raw = str(x.get("heroName", x.get("name", "")))
            label = self.upgrade_menu_label(x)
            if q in raw.lower() or q in label.lower():
                out.append(x)
        return out

    def get_upgrade_skins_for_entry(self, entry: dict[str, Any], refresh: bool = False) -> list[SkinItem]:
        category = str(entry.get("heroName") or entry.get("name") or "")
        if not category:
            return []
        return self.get_upgrade_skins(category, refresh=refresh)

    def grade_counts_for_role(self, role: str, refresh: bool = False) -> dict[str, int]:
        counts: dict[str, int] = {key: 0 for _label, key in SKIN_GRADES}
        for hero in self.list_heroes_by_role(role, refresh=refresh):
            grade = self._hero_grade_match(hero, refresh=refresh)
            for g, skin in grade.items():
                if skin and g in counts:
                    counts[g] += 1
        return counts

    def _hero_grade_match(
        self, hero: str, refresh: bool = False
    ) -> dict[str, SkinItem | None]:
        found: dict[str, SkinItem | None] = {key: None for _label, key in SKIN_GRADES}
        for skin in self.get_skins_for_hero(hero, refresh=refresh):
            grade = detect_skin_grade(skin)
            if grade and found.get(grade) is None:
                found[grade] = skin
        return found

    def find_skins_for_role_grade(
        self, role: str, grade: str, refresh: bool = False
    ) -> list[tuple[str, SkinItem]]:
        out: list[tuple[str, SkinItem]] = []
        for hero in self.list_heroes_by_role(role, refresh=refresh):
            for skin in self.get_skins_for_hero(hero, refresh=refresh):
                if detect_skin_grade(skin) == grade:
                    out.append((hero, skin))
                    break
        return out

    def invalidate_cache(self) -> None:
        """Panggil setelah catalog di-update."""
        self._name_corpus = None
        self._heroes = None
