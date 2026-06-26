"""Search heroes and skins — fast light index + optional full build."""

from __future__ import annotations

import json
import logging
import re
from concurrent.futures import ThreadPoolExecutor, as_completed
from difflib import SequenceMatcher
from typing import Callable, Optional

from .api_client import ApiClient
from .config import INDEX_PATH
from .models import SkinItem

LOG = logging.getLogger(__name__)

ProgressCb = Callable[[str, int, int], None]


def _tokenize(text: str) -> list[str]:
    return [t for t in re.split(r"[\s\-_./]+", text.lower()) if t]


def _score(query: str, item: SkinItem) -> float:
    q = query.lower().strip()
    blob = item.search_blob()
    if not q:
        return 0.0
    if q in blob:
        return 100.0
    ratio = SequenceMatcher(None, q, blob).ratio() * 100
    q_tokens = _tokenize(q)
    b_tokens = set(_tokenize(blob))
    token_hits = sum(1 for t in q_tokens if t in b_tokens or any(t in b for b in b_tokens))
    token_score = (token_hits / max(len(q_tokens), 1)) * 80
    return max(ratio, token_score)


def _dedupe(items: list[SkinItem]) -> list[SkinItem]:
    seen: set[str] = set()
    out: list[SkinItem] = []
    for it in items:
        key = f"{it.download_url}|{it.skin_name}"
        if key in seen or not it.download_url:
            continue
        seen.add(key)
        out.append(it)
    return out


def _save_index(items: list[SkinItem]) -> None:
    INDEX_PATH.parent.mkdir(parents=True, exist_ok=True)
    with open(INDEX_PATH, "w", encoding="utf-8") as f:
        json.dump(
            [
                {
                    "id": x.id,
                    "hero_name": x.hero_name,
                    "skin_name": x.skin_name,
                    "image_url": x.image_url,
                    "download_url": x.download_url,
                    "category": x.category,
                    "mini_patch": x.mini_patch,
                    "source": x.source,
                }
                for x in items
            ],
            f,
            ensure_ascii=False,
        )


class SearchIndex:
    def __init__(self, api: ApiClient, cfg: dict) -> None:
        self.api = api
        self.cfg = cfg
        self.threshold = float(cfg.get("search", {}).get("fuzzy_threshold", 55))
        self.max_results = int(cfg.get("search", {}).get("max_results", 25))
        self._items: list[SkinItem] = []
        self._loaded = False

    def _from_raw(self, raw: list) -> list[SkinItem]:
        return [
            SkinItem(
                id=str(x.get("id", "")),
                hero_name=str(x.get("hero_name", "")),
                skin_name=str(x.get("skin_name", "")),
                image_url=str(x.get("image_url", "")),
                download_url=str(x.get("download_url", "")),
                category=str(x.get("category", "")),
                mini_patch=bool(x.get("mini_patch", False)),
                source=str(x.get("source", "")),
            )
            for x in raw
        ]

    def _load_from_disk(self) -> bool:
        if not INDEX_PATH.exists():
            return False
        try:
            with open(INDEX_PATH, encoding="utf-8") as f:
                raw = json.load(f)
            self._items = self._from_raw(raw)
            self._loaded = True
            return True
        except (json.JSONDecodeError, OSError, TypeError):
            return False

    def build_light(self, refresh: bool = False) -> int:
        """Cepat: heroes + custom saja (~5 detik)."""
        items: list[SkinItem] = []
        try:
            items.extend(self.api.get_heroes_flat(refresh=refresh))
        except Exception as e:
            LOG.warning("heroes: %s", e)
        try:
            items.extend(self.api.get_custom_skins(refresh=refresh))
        except Exception as e:
            LOG.warning("custom: %s", e)
        unique = _dedupe(items)
        self._items = unique
        self._loaded = True
        _save_index(unique)
        LOG.info("Light index: %d skins", len(unique))
        return len(unique)

    def build_full(
        self,
        refresh: bool = False,
        on_progress: Optional[ProgressCb] = None,
    ) -> int:
        """Lengkap: termasuk semua upgrade skin (lama, pakai progress)."""
        items: list[SkinItem] = []
        try:
            if on_progress:
                on_progress("Mengambil daftar hero...", 0, 100)
            items.extend(self.api.get_heroes_flat(refresh=refresh))
        except Exception as e:
            LOG.warning("heroes: %s", e)

        heroes: list[dict] = []
        try:
            heroes = self.api.get_upgrade_menu(refresh=refresh)
        except Exception as e:
            LOG.warning("upgrade menu: %s", e)

        total_h = max(len(heroes), 1)
        done = 0

        def _fetch_one(entry: dict) -> list[SkinItem]:
            return self.api.get_upgrade_skins_for_entry(entry, refresh=refresh)

        workers = min(8, max(2, total_h // 10))
        with ThreadPoolExecutor(max_workers=workers) as pool:
            futures = {pool.submit(_fetch_one, h): h for h in heroes}
            for fut in as_completed(futures):
                entry = futures[fut]
                label = str(entry.get("heroName", "?"))[:30]
                done += 1
                if on_progress:
                    pct = int(done * 70 / total_h)
                    on_progress(f"Upgrade: {label}", pct, 100)
                try:
                    items.extend(fut.result())
                except Exception as e:
                    LOG.debug("upgrade %s: %s", label, e)

        if on_progress:
            on_progress("Custom bundles...", 85, 100)
        try:
            for bundle in self.api.get_custom_bundles(refresh=refresh):
                bid = str(bundle.get("id", ""))
                bname = str(bundle.get("name", ""))
                try:
                    items.extend(
                        self.api.get_custom_bundle_skins(bid, bname, refresh=refresh)
                    )
                except Exception as e:
                    LOG.debug("bundle %s: %s", bname, e)
        except Exception as e:
            LOG.warning("custom bundles: %s", e)

        unique = _dedupe(items)
        self._items = unique
        self._loaded = True
        _save_index(unique)
        if on_progress:
            on_progress("Selesai", 100, 100)
        LOG.info("Full index: %d skins", len(unique))
        return len(unique)

    def build(self, refresh: bool = False, full: bool = False, on_progress: Optional[ProgressCb] = None) -> int:
        if full:
            return self.build_full(refresh=refresh, on_progress=on_progress)
        return self.build_light(refresh=refresh)

    def load(self, allow_build: bool = True) -> None:
        """Muat index dari disk; build ringan hanya jika belum ada."""
        if self._loaded and self._items:
            return
        if self._load_from_disk():
            return
        if allow_build:
            self.build_light()
        else:
            self._items = []

    def ensure_for_search(self) -> None:
        if self._loaded and self._items:
            return
        if self._load_from_disk() and self._items:
            return
        self.build_light()

    @property
    def items(self) -> list[SkinItem]:
        if not self._items:
            self.load()
        return self._items

    @property
    def count(self) -> int:
        return len(self._items)

    def search(self, query: str) -> list[SkinItem]:
        self.ensure_for_search()
        scored = [(_score(query, it), it) for it in self._items]
        scored = [(s, it) for s, it in scored if s >= self.threshold]
        scored.sort(key=lambda x: x[0], reverse=True)
        return [it for _, it in scored[: self.max_results]]

    def by_hero(self, hero_name: str) -> list[SkinItem]:
        q = hero_name.lower()
        return [
            it
            for it in self.items
            if q in it.hero_name.lower() or q in it.category.lower()
        ]

    def heroes_unique(self) -> list[str]:
        names = {it.hero_name for it in self.items if it.hero_name}
        return sorted(names, key=str.lower)
