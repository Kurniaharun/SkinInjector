"""API client for imb.expressme.in (same source as iMOBA APK)."""

from __future__ import annotations

import json
import logging
import time
from pathlib import Path
from typing import Any, Optional
from urllib.parse import quote

import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

from .config import CACHE_DIR
from .errors import ApiError
from .models import SkinItem
from .name_resolver import build_name_corpus, resolve_category_label
from .skin_grade import SKIN_GRADES, detect_skin_grade

# Kategori efek dari API (POST getEmotes + category)
EFFECT_CATEGORIES: list[tuple[str, str]] = [
    ("Recall Animations", "recall"),
    ("Emotes", "emote"),
    ("TRAIL ANIMATION", "trail"),
    ("RESPAWN ANIMATION", "respawn"),
    ("PAINTED SKIN", "painted"),
    ("ELIMINATED BATTLE", "eliminated"),
]

HERO_ROLES: list[str] = [
    "Fighter",
    "Mage",
    "Marksman",
    "Tank",
    "Assassin",
    "Support",
]

LOG = logging.getLogger(__name__)


class ApiClient:
    def __init__(self, cfg: dict) -> None:
        self.cfg = cfg
        api = cfg["api"]
        self.base = api["base"].rstrip("/")
        self.timeout = int(api.get("timeout", 30))
        self.ua = api.get("user_agent", "MLBB-Skin-Injector/1.0")
        self.session = requests.Session()
        self.session.headers.update({"User-Agent": self.ua})
        retry = Retry(total=2, backoff_factor=0.3, status_forcelist=(502, 503, 504))
        adapter = HTTPAdapter(pool_connections=6, pool_maxsize=6, max_retries=retry)
        self.session.mount("https://", adapter)
        self.session.mount("http://", adapter)
        self._endpoints: dict[str, str] = {}
        self._name_corpus: set[str] | None = None

    def _cache_path(self, key: str) -> Path:
        safe = key.replace("/", "_").replace("?", "_")
        return CACHE_DIR / f"{safe}.json"

    def _read_cache(self, key: str, ttl_hours: float) -> Optional[Any]:
        path = self._cache_path(key)
        if not path.exists():
            return None
        age_h = (time.time() - path.stat().st_mtime) / 3600
        if age_h > ttl_hours:
            return None
        try:
            with open(path, encoding="utf-8") as f:
                return json.load(f)
        except (json.JSONDecodeError, OSError):
            return None

    def _write_cache(self, key: str, data: Any) -> None:
        path = self._cache_path(key)
        path.parent.mkdir(parents=True, exist_ok=True)
        with open(path, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)

    def _get(self, url: str) -> Any:
        try:
            r = self.session.get(url, timeout=self.timeout)
            r.raise_for_status()
            return r.json()
        except requests.RequestException as e:
            raise ApiError(f"GET gagal {url}: {e}") from e
        except json.JSONDecodeError as e:
            raise ApiError(f"Response bukan JSON: {url}") from e

    def _post(self, url: str, data: dict[str, str]) -> Any:
        try:
            r = self.session.post(url, data=data, timeout=self.timeout)
            r.raise_for_status()
            return r.json()
        except requests.RequestException as e:
            raise ApiError(f"POST gagal {url}: {e}") from e
        except json.JSONDecodeError as e:
            raise ApiError(f"Response bukan JSON: {url}") from e

    def load_endpoints(self, refresh: bool = False) -> dict[str, str]:
        if self._endpoints and not refresh:
            return self._endpoints
        ttl = float(self.cfg.get("cache", {}).get("endpoints_ttl_hours", 24))
        cached = None if refresh else self._read_cache("endpoints", ttl)
        if cached:
            self._endpoints = {item["name"]: item["value"] for item in cached}
            return self._endpoints
        url = f"{self.base}/{self.cfg['api']['config_endpoint']}"
        raw = self._get(url)
        if not isinstance(raw, list):
            raise ApiError("Format getConnection tidak valid")
        self._write_cache("endpoints", raw)
        self._endpoints = {item["name"]: item["value"] for item in raw}
        LOG.info("Loaded %d endpoints", len(self._endpoints))
        return self._endpoints

    def name_corpus(self, refresh: bool = False) -> set[str]:
        if self._name_corpus is not None and not refresh:
            return self._name_corpus
        entries: list[dict] = []
        try:
            for skins in self.get_hero_groups(refresh=refresh).values():
                entries.extend(skins)
        except ApiError as e:
            LOG.warning("corpus heroes: %s", e)
        try:
            entries.extend(self.get_upgrade_menu(refresh=refresh))
        except ApiError as e:
            LOG.warning("corpus upgrade: %s", e)
        self._name_corpus = build_name_corpus(entries)
        return self._name_corpus

    def upgrade_menu_label(self, entry: dict[str, Any]) -> str:
        return resolve_category_label(entry, self.name_corpus())

    def endpoint(self, name: str) -> str:
        eps = self.load_endpoints()
        if name not in eps:
            raise ApiError(f"Endpoint '{name}' tidak ada di config server")
        return eps[name]

    def get_upgrade_menu(self, refresh: bool = False) -> list[dict[str, Any]]:
        ttl = float(self.cfg.get("cache", {}).get("heroes_ttl_hours", 6))
        key = "getlistUpgradeSkins"
        if not refresh:
            c = self._read_cache(key, ttl)
            if c is not None:
                return c
        data = self._get(self.endpoint("getlistUpgradeSkins"))
        self._write_cache(key, data)
        return data

    def get_upgrade_skins(self, hero_name: str, refresh: bool = False) -> list[SkinItem]:
        ttl = float(self.cfg.get("cache", {}).get("skins_ttl_hours", 1))
        key = f"upgrade_{hero_name}"
        corpus = self.name_corpus(refresh=refresh)
        if not refresh:
            c = self._read_cache(key, ttl)
            if c is not None:
                return [SkinItem.from_upgrade_entry(x, hero_name, corpus) for x in c]
        url = self.endpoint("getUpgradeSkins")
        raw = self._post(url, {"category": hero_name})
        if isinstance(raw, dict):
            raw = raw.get("data", raw.get("skins", [raw]))
        if not isinstance(raw, list):
            raise ApiError("Format getUpgradeSkins tidak valid")
        self._write_cache(key, raw)
        return [
            SkinItem.from_upgrade_entry(x, hero_name, corpus)
            for x in raw
            if x.get("url") or x.get("downloadLink")
        ]

    def get_heroes_flat(self, refresh: bool = False) -> list[SkinItem]:
        ttl = float(self.cfg.get("cache", {}).get("heroes_ttl_hours", 6))
        key = "heroes_flat"
        corpus = self.name_corpus(refresh=refresh)
        if not refresh:
            c = self._read_cache(key, ttl)
            if c is not None:
                return [SkinItem.from_hero_entry(x, corpus=corpus) for x in c]
        url = self.endpoint("getHeroes")
        raw = self._get(url)
        flat: list[dict] = []
        if isinstance(raw, dict):
            for _hero_key, entries in raw.items():
                if isinstance(entries, list):
                    flat.extend(entries)
        elif isinstance(raw, list):
            flat = raw
        else:
            raise ApiError("Format getHeroes tidak valid")
        self._write_cache(key, flat)
        return [SkinItem.from_hero_entry(x, corpus=corpus) for x in flat if x.get("downloadLink")]

    def _pick_custom_download(self, options: list, hero_name: str) -> dict | None:
        """Pilih entry download utama (skip Backup/Remove)."""
        hero_low = hero_name.lower()
        valid = [x for x in options if x.get("url") or x.get("downloadLink")]
        if not valid:
            return None
        for x in valid:
            name = str(x.get("name", "")).lower()
            if "backup" in name or "remove" in name:
                continue
            if hero_low in name.lower() or name.lower() in hero_low:
                return x
        for x in valid:
            name = str(x.get("name", "")).lower()
            if "backup" not in name and "remove" not in name:
                return x
        return valid[0]

    def enrich_custom_menu(self, menu: list[dict[str, Any]]) -> list[dict[str, Any]]:
        """Ambil URL download per skin via getSkinMenu.php?category={heroName}."""
        if not menu:
            return []
        skin_menu_url = self.endpoint("getSkinMenu")
        enriched: list[dict[str, Any]] = []
        for entry in menu:
            hero = str(entry.get("heroName", ""))
            if not hero:
                continue
            try:
                raw = self._post(skin_menu_url, {"category": hero})
                if isinstance(raw, dict):
                    raw = raw.get("data", raw.get("items", []))
                if not isinstance(raw, list):
                    continue
                pick = self._pick_custom_download(raw, hero)
                if not pick:
                    continue
                merged = {**entry, **pick}
                if merged.get("url") or merged.get("downloadLink"):
                    enriched.append(merged)
            except ApiError as e:
                LOG.warning("custom enrich %s: %s", hero, e)
        return enriched

    def get_custom_bundles(self, refresh: bool = False) -> list[dict[str, Any]]:
        """Banner koleksi custom (Naruto, Demon Slayer, dll)."""
        ttl = float(self.cfg.get("cache", {}).get("skins_ttl_hours", 1))
        key = "custom_bundles"
        if not refresh:
            c = self._read_cache(key, ttl)
            if c is not None:
                return c
        raw = self._get(self.endpoint("getCustomSkins"))
        if not isinstance(raw, list):
            raise ApiError("Format getCustomSkins tidak valid")
        self._write_cache(key, raw)
        return raw

    def get_custom_bundle_skins(
        self,
        bundle_id: str,
        bundle_name: str = "",
        refresh: bool = False,
    ) -> list[SkinItem]:
        """Skin dalam koleksi — GET getcustomSkinMenu.php?category={nama bundle}."""
        ttl = float(self.cfg.get("cache", {}).get("skins_ttl_hours", 1))
        key = f"custom_bundle_{bundle_id}"
        corpus = self.name_corpus(refresh=refresh)
        if not refresh:
            c = self._read_cache(key, ttl)
            if c is not None:
                return [
                    SkinItem.from_bundle_entry(x, bundle_name, corpus)
                    for x in c
                    if x.get("downloadLink") or x.get("url")
                ]
        if not bundle_name:
            for b in self.get_custom_bundles(refresh=refresh):
                if str(b.get("id", "")) == str(bundle_id):
                    bundle_name = str(b.get("name", ""))
                    break
        category = bundle_name or bundle_id
        base = self.endpoint("getcustomSkinMenu")
        url = f"{base}{quote(str(category), safe='')}"
        raw = self._get(url)
        if not isinstance(raw, list):
            raise ApiError(f"Format custom bundle {bundle_id} tidak valid")
        raw = self.enrich_custom_menu(raw)
        self._write_cache(key, raw)
        return [
            SkinItem.from_bundle_entry(x, bundle_name or category, corpus)
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
                skins = self.get_custom_bundle_skins(
                    str(bundle.get("id", "")),
                    name,
                )
                out.extend(skins[:limit])
            except ApiError as e:
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
                except ApiError:
                    pass
        return out[:limit]

    def get_custom_skins(self, refresh: bool = False) -> list[SkinItem]:
        """Legacy — banner saja, pakai get_custom_bundles + get_custom_bundle_skins."""
        return [
            SkinItem.from_custom_entry(x, self.name_corpus(refresh=refresh))
            for x in self.get_custom_bundles(refresh=refresh)
        ]

    def get_role_categories(self, refresh: bool = False) -> list[dict[str, Any]]:
        ttl = float(self.cfg.get("cache", {}).get("heroes_ttl_hours", 6))
        key = "category1_roles"
        if not refresh:
            c = self._read_cache(key, ttl)
            if c is not None:
                return c
        raw = self._get(self.endpoint("getCategory1"))
        if not isinstance(raw, list):
            raise ApiError("Format getCategory1 tidak valid")
        self._write_cache(key, raw)
        return raw

    def list_heroes_by_role(self, role: str, refresh: bool = False) -> list[str]:
        ttl = float(self.cfg.get("cache", {}).get("heroes_ttl_hours", 6))
        key = f"heroes_role_{role.lower()}"
        if not refresh:
            c = self._read_cache(key, ttl)
            if isinstance(c, list):
                return c
        raw = self._post(self.endpoint("getHeroes"), {"category": role})
        names: list[str] = []
        if isinstance(raw, dict):
            names = sorted(raw.keys(), key=str.lower)
        elif isinstance(raw, list):
            for x in raw:
                if isinstance(x, dict):
                    n = x.get("heroName") or x.get("heroname") or x.get("name")
                    if n:
                        names.append(str(n))
        self._write_cache(key, names)
        return names

    def get_announcements(self, refresh: bool = False) -> list[dict[str, Any]]:
        ttl = float(self.cfg.get("cache", {}).get("endpoints_ttl_hours", 24))
        key = "announcements"
        if not refresh:
            c = self._read_cache(key, ttl)
            if c is not None:
                return c
        raw = self._get(self.endpoint("getAnnouncement"))
        if not isinstance(raw, list):
            raise ApiError("Format getAnnouncement tidak valid")
        self._write_cache(key, raw)
        return raw

    def get_effects(self, category: str, refresh: bool = False) -> list[SkinItem]:
        """Recall, emote, trail, respawn, painted — POST getEmotes."""
        ttl = float(self.cfg.get("cache", {}).get("skins_ttl_hours", 1))
        safe_cat = category.replace("/", "_").replace(" ", "_")
        key = f"effects_{safe_cat}"
        corpus = self.name_corpus(refresh=refresh)
        if not refresh:
            c = self._read_cache(key, ttl)
            if c is not None:
                return [SkinItem.from_effect_entry(x, corpus=corpus) for x in c]
        url = self.endpoint("getEmotes")
        raw = self._post(url, {"category": category})
        if isinstance(raw, dict):
            raw = raw.get("data", raw.get("items", []))
        if not isinstance(raw, list):
            raise ApiError(f"Format getEmotes tidak valid untuk {category}")
        self._write_cache(key, raw)
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
            try:
                for item in self.get_effects(cat_name):
                    if q in item.skin_name.lower() or q in item.category.lower():
                        results.append(item)
                        if len([r for r in results if r.category == cat_name]) >= limit_per_cat:
                            break
            except ApiError as e:
                LOG.warning("search effects %s: %s", cat_name, e)
        return results

    def list_backup_skins(self, hero_name: str | None = None, refresh: bool = False) -> list[SkinItem]:
        """Skin BACKUP official dari API (untuk restore skin default via inject)."""
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
        """Home menu categories from getCategory1 + getCategory2."""
        items: list[dict] = []
        for ep in ("getCategory1", "getCategory2"):
            try:
                data = self._get(self.endpoint(ep))
                if isinstance(data, list):
                    items.extend(data)
            except ApiError as e:
                LOG.warning("%s", e)
        return items

    def get_hero_groups(self, refresh: bool = False) -> dict[str, list[dict[str, Any]]]:
        """getHeroes2 — dict[hero_name, list[skin entries]]."""
        ttl = float(self.cfg.get("cache", {}).get("heroes_ttl_hours", 6))
        key = "heroes_groups"
        if not refresh:
            c = self._read_cache(key, ttl)
            if isinstance(c, dict):
                return c
        url = self.endpoint("getHeroes")
        raw = self._get(url)
        if not isinstance(raw, dict):
            raise ApiError("Format getHeroes tidak valid (harus dict per hero)")
        self._write_cache(key, raw)
        return raw

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
        """POST pakai heroName persis dari item list upgrade."""
        category = str(entry.get("heroName") or entry.get("name") or "")
        if not category:
            return []
        return self.get_upgrade_skins(category, refresh=refresh)

    def grade_counts_for_role(self, role: str, refresh: bool = False) -> dict[str, int]:
        """Jumlah hero per grade skin yang tersedia di role."""
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
        """Satu skin per grade untuk hero (prioritas entry pertama)."""
        found: dict[str, SkinItem | None] = {key: None for _label, key in SKIN_GRADES}
        for skin in self.get_skins_for_hero(hero, refresh=refresh):
            grade = detect_skin_grade(skin)
            if grade and found.get(grade) is None:
                found[grade] = skin
        return found

    def find_skins_for_role_grade(
        self, role: str, grade: str, refresh: bool = False
    ) -> list[tuple[str, SkinItem]]:
        """Daftar (hero, skin) yang punya grade tertentu dalam role."""
        out: list[tuple[str, SkinItem]] = []
        for hero in self.list_heroes_by_role(role, refresh=refresh):
            for skin in self.get_skins_for_hero(hero, refresh=refresh):
                if detect_skin_grade(skin) == grade:
                    out.append((hero, skin))
                    break
        return out
