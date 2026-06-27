"""Offline catalog — raw JSON di RAM, SkinItem parse lazy + cache."""

from __future__ import annotations

import logging
from typing import Any

from .api_client import EFFECT_CATEGORIES, HERO_ROLES
from .catalog_store import catalog_ready, read_json
from .errors import CatalogNotFoundError
from .models import SkinItem
from .name_resolver import resolve_category_label
from .skin_grade import SKIN_GRADES, detect_skin_grade

LOG = logging.getLogger(__name__)


def _parse_hero_entries(hero: str, entries: list, corpus: set[str]) -> list[SkinItem]:
    out: list[SkinItem] = []
    for x in entries:
        item = SkinItem.from_hero_entry(x, hero=hero, corpus=corpus)
        if item.download_url:
            out.append(item)
    return out


def _parse_upgrade_entries(cat: str, entries: list, corpus: set[str]) -> list[SkinItem]:
    return [
        SkinItem.from_upgrade_entry(x, cat, corpus)
        for x in entries
        if x.get("url") or x.get("downloadLink")
    ]


def _parse_effect_entries(entries: list, corpus: set[str]) -> list[SkinItem]:
    return [
        SkinItem.from_effect_entry(x, corpus=corpus)
        for x in entries
        if x.get("downloadLink") or x.get("url")
    ]


def _parse_bundle_entries(bundle_name: str, entries: list, corpus: set[str]) -> list[SkinItem]:
    return [
        SkinItem.from_bundle_entry(x, bundle_name, corpus)
        for x in entries
        if x.get("downloadLink") or x.get("url")
    ]


def _lc_key(text: str) -> str:
    return (text or "").strip().lower()


class LocalCatalog:
    """Katalog offline — warmup() muat JSON mentah (~50ms), parse per-menu."""

    def __init__(self, cfg: dict) -> None:
        self.cfg = cfg
        self._raw_loaded = False
        self._corpus: set[str] = set()
        self._heroes_raw: dict[str, list] = {}
        self._upgrade_menu: list[dict] = []
        self._upgrade_labels: list[str] = []
        self._upgrade_raw: dict[str, list] = {}
        self._bundles: list[dict] = []
        self._bundle_raw: dict[str, list] = {}
        self._effects_raw: dict[str, list] = {}
        self._announcements: list[dict] = []
        self._role_categories: list[dict] = []
        self._heroes_by_role: dict[str, list[str]] = {}
        self._hero_names: list[str] = []
        self._skins_hero: dict[str, list[SkinItem]] = {}
        self._skins_hero_lc: dict[str, list[SkinItem]] = {}
        self._skins_upgrade: dict[str, list[SkinItem]] = {}
        self._skins_upgrade_lc: dict[str, list[SkinItem]] = {}
        self._skins_effects: dict[str, list[SkinItem]] = {}
        self._skins_bundle: dict[str, list[SkinItem]] = {}
        self._heroes_flat: list[SkinItem] | None = None
        self._all_skins: list[SkinItem] | None = None

    def _require(self) -> None:
        if not catalog_ready():
            raise CatalogNotFoundError(
                "Katalog belum di-scrape.\n"
                "Jalankan: python main.py update"
            )

    def warmup(self) -> None:
        """Muat semua JSON mentah ke RAM — tanpa parse SkinItem."""
        if self._raw_loaded:
            return
        self._require()
        LOG.info("Warmup katalog (raw)...")

        self._heroes_raw = read_json("heroes")
        self._upgrade_menu = read_json("upgrade_menu")
        self._upgrade_raw = read_json("upgrade_skins", default={})
        self._bundles = read_json("custom_bundles")
        self._bundle_raw = read_json("custom_bundle_skins", default={})
        self._effects_raw = read_json("effects", default={})
        self._announcements = read_json("announcements", default=[])
        self._role_categories = read_json(
            "role_categories", default=[{"name": r} for r in HERO_ROLES]
        )
        self._heroes_by_role = read_json("heroes_by_role", default={})

        try:
            self._corpus = set(read_json("name_corpus", default=[]))
        except CatalogNotFoundError:
            self._corpus = set()

        try:
            saved_labels = read_json("upgrade_labels", default=None)
        except CatalogNotFoundError:
            saved_labels = None

        if saved_labels and len(saved_labels) == len(self._upgrade_menu):
            self._upgrade_labels = list(saved_labels)
        else:
            self._upgrade_labels = [
                resolve_category_label(x, self._corpus) for x in self._upgrade_menu
            ]

        self._hero_names = sorted(self._heroes_raw.keys(), key=str.lower)
        self._raw_loaded = True
        LOG.info("Katalog raw: %d hero, %d upgrade menu", len(self._hero_names), len(self._upgrade_menu))

    def is_warm(self) -> bool:
        return self._raw_loaded

    def load_endpoints(self, refresh: bool = False) -> dict[str, str]:
        self._require()
        return {}

    def name_corpus(self, refresh: bool = False) -> set[str]:
        if refresh:
            self.invalidate_cache()
        self.warmup()
        return self._corpus

    def upgrade_menu_label(self, entry: dict[str, Any]) -> str:
        self.warmup()
        try:
            idx = self._upgrade_menu.index(entry)
            return self._upgrade_labels[idx]
        except ValueError:
            return resolve_category_label(entry, self._corpus)

    def get_upgrade_menu(self, refresh: bool = False) -> list[dict[str, Any]]:
        self.warmup()
        return self._upgrade_menu

    def get_upgrade_menu_labels(self) -> list[str]:
        self.warmup()
        return self._upgrade_labels

    def _upgrade_key(self, hero_name: str) -> str | None:
        if hero_name in self._upgrade_raw:
            return hero_name
        lk = _lc_key(hero_name)
        for key in self._upgrade_raw:
            if _lc_key(key) == lk:
                return key
        return None

    def get_upgrade_skins(self, hero_name: str, refresh: bool = False) -> list[SkinItem]:
        self.warmup()
        if hero_name in self._skins_upgrade:
            return self._skins_upgrade[hero_name]
        lk = _lc_key(hero_name)
        if lk in self._skins_upgrade_lc:
            return self._skins_upgrade_lc[lk]

        key = self._upgrade_key(hero_name)
        if not key:
            return []
        skins = _parse_upgrade_entries(key, self._upgrade_raw[key], self._corpus)
        self._skins_upgrade[key] = skins
        self._skins_upgrade_lc[lk] = skins
        return skins

    def get_heroes_flat(self, refresh: bool = False) -> list[SkinItem]:
        self.warmup()
        if self._heroes_flat is not None:
            return self._heroes_flat
        flat: list[SkinItem] = []
        for hero in self._hero_names:
            flat.extend(self.get_skins_for_hero(hero))
        self._heroes_flat = flat
        return flat

    def get_custom_bundles(self, refresh: bool = False) -> list[dict[str, Any]]:
        self.warmup()
        return self._bundles

    def get_custom_bundle_skins(
        self,
        bundle_id: str,
        bundle_name: str = "",
        refresh: bool = False,
    ) -> list[SkinItem]:
        self.warmup()
        if bundle_id in self._skins_bundle:
            return self._skins_bundle[bundle_id]
        entries = self._bundle_raw.get(bundle_id, [])
        if not bundle_name:
            bundle_name = next(
                (str(b.get("name", "")) for b in self._bundles if str(b.get("id")) == bundle_id),
                "",
            )
        skins = _parse_bundle_entries(bundle_name, entries, self._corpus)
        self._skins_bundle[bundle_id] = skins
        return skins

    def search_custom_bundles(self, query: str, limit: int = 20) -> list[SkinItem]:
        self.warmup()
        q = query.lower().strip()
        if not q:
            return []
        out: list[SkinItem] = []
        for bundle in self._bundles:
            name = str(bundle.get("name", ""))
            bid = str(bundle.get("id", ""))
            if q not in name.lower():
                continue
            out.extend(self.get_custom_bundle_skins(bid, name)[:limit])
            if len(out) >= limit:
                return out[:limit]
        if len(out) < limit:
            for bid in self._bundle_raw:
                for skin in self.get_custom_bundle_skins(bid):
                    if q in skin.label().lower():
                        out.append(skin)
                        if len(out) >= limit:
                            return out[:limit]
        return out[:limit]

    def get_custom_skins(self, refresh: bool = False) -> list[SkinItem]:
        self.warmup()
        return [SkinItem.from_custom_entry(x, self._corpus) for x in self._bundles]

    def get_role_categories(self, refresh: bool = False) -> list[dict[str, Any]]:
        self.warmup()
        return self._role_categories

    def list_heroes_by_role(self, role: str, refresh: bool = False) -> list[str]:
        self.warmup()
        if role in self._heroes_by_role:
            return self._heroes_by_role[role]
        for key, val in self._heroes_by_role.items():
            if key.lower() == role.lower():
                return val
        return []

    def get_announcements(self, refresh: bool = False) -> list[dict[str, Any]]:
        self.warmup()
        return self._announcements

    def get_effects(self, category: str, refresh: bool = False) -> list[SkinItem]:
        self.warmup()
        if category in self._skins_effects:
            return self._skins_effects[category]
        entries = self._effects_raw.get(category, [])
        skins = _parse_effect_entries(entries, self._corpus)
        self._skins_effects[category] = skins
        return skins

    def list_effect_categories(self) -> list[tuple[str, str]]:
        return list(EFFECT_CATEGORIES)

    def search_effects(self, query: str, limit_per_cat: int = 12) -> list[SkinItem]:
        self.warmup()
        q = query.lower().strip()
        if not q:
            return []
        results: list[SkinItem] = []
        for cat_name, _src in EFFECT_CATEGORIES:
            cat_count = 0
            for item in self.get_effects(cat_name):
                if q in item.skin_name.lower() or q in item.category.lower():
                    results.append(item)
                    cat_count += 1
                    if cat_count >= limit_per_cat:
                        break
        return results

    def list_backup_skins(self, hero_name: str | None = None, refresh: bool = False) -> list[SkinItem]:
        self.warmup()
        out: list[SkinItem] = []
        heroes = [hero_name] if hero_name else self._hero_names
        for hero in heroes:
            entries = self._heroes_raw.get(hero, [])
            if not entries and hero_name:
                for key, val in self._heroes_raw.items():
                    if key.lower() == hero_name.lower():
                        entries = val
                        hero = key
                        break
            for x in entries:
                raw = str(x.get("heroname", x.get("name", ""))).lower()
                dl = str(x.get("downloadLink", "")).lower()
                if "backup" in raw or "backup" in dl:
                    item = SkinItem.from_hero_entry(x, hero=hero, corpus=self._corpus)
                    item.source = "backup"
                    if item.download_url:
                        out.append(item)
        return out

    def get_categories(self) -> list[dict[str, Any]]:
        return self.get_role_categories()

    def get_hero_groups(self, refresh: bool = False) -> dict[str, list[dict[str, Any]]]:
        self.warmup()
        return self._heroes_raw

    def list_hero_names(self, refresh: bool = False) -> list[str]:
        self.warmup()
        return self._hero_names

    def get_skins_for_hero(self, hero_name: str, refresh: bool = False) -> list[SkinItem]:
        self.warmup()
        if hero_name in self._skins_hero:
            return self._skins_hero[hero_name]
        lk = _lc_key(hero_name)
        if lk in self._skins_hero_lc:
            return self._skins_hero_lc[lk]

        entries = self._heroes_raw.get(hero_name, [])
        hero_key = hero_name
        if not entries:
            for key, val in self._heroes_raw.items():
                if key.lower() == lk:
                    entries = val
                    hero_key = key
                    break
        skins = _parse_hero_entries(hero_key, entries, self._corpus)
        self._skins_hero[hero_key] = skins
        self._skins_hero_lc[lk] = skins
        return skins

    def search_hero_names(self, query: str) -> list[str]:
        self.warmup()
        q = query.lower().strip()
        if not q:
            return self._hero_names
        return [n for n in self._hero_names if q in n.lower()]

    def search_upgrade_entries(self, query: str) -> list[dict[str, Any]]:
        self.warmup()
        q = query.lower().strip()
        if not q:
            return self._upgrade_menu
        out: list[dict[str, Any]] = []
        for entry, label in zip(self._upgrade_menu, self._upgrade_labels):
            raw = str(entry.get("heroName", entry.get("name", "")))
            if q in raw.lower() or q in label.lower():
                out.append(entry)
        return out

    def get_upgrade_skins_for_entry(self, entry: dict[str, Any], refresh: bool = False) -> list[SkinItem]:
        category = str(entry.get("heroName") or entry.get("name") or "")
        if not category:
            return []
        return self.get_upgrade_skins(category, refresh=refresh)

    def all_skins_for_index(self) -> list[SkinItem]:
        """Untuk build search index — parse semua (hanya saat refresh index)."""
        self.warmup()
        if self._all_skins is not None:
            return self._all_skins
        items: list[SkinItem] = []
        items.extend(self.get_heroes_flat())
        for key in self._upgrade_raw:
            items.extend(self.get_upgrade_skins(key))
        for bid in self._bundle_raw:
            items.extend(self.get_custom_bundle_skins(bid))
        for cat in self._effects_raw:
            items.extend(self.get_effects(cat))
        self._all_skins = items
        return items

    def grade_counts_for_role(self, role: str, refresh: bool = False) -> dict[str, int]:
        self.warmup()
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
        self.warmup()
        out: list[tuple[str, SkinItem]] = []
        for hero in self.list_heroes_by_role(role, refresh=refresh):
            for skin in self.get_skins_for_hero(hero, refresh=refresh):
                if detect_skin_grade(skin) == grade:
                    out.append((hero, skin))
                    break
        return out

    def invalidate_cache(self) -> None:
        self._raw_loaded = False
        self._corpus = set()
        self._heroes_raw = {}
        self._upgrade_menu = []
        self._upgrade_labels = []
        self._upgrade_raw = {}
        self._bundles = []
        self._bundle_raw = {}
        self._effects_raw = {}
        self._announcements = []
        self._role_categories = []
        self._heroes_by_role = {}
        self._hero_names = []
        self._skins_hero = {}
        self._skins_hero_lc = {}
        self._skins_upgrade = {}
        self._skins_upgrade_lc = {}
        self._skins_effects = {}
        self._skins_bundle = {}
        self._heroes_flat = None
        self._all_skins = None
