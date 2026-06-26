"""Search heroes and skins."""

from __future__ import annotations

import json
import logging
import re
from difflib import SequenceMatcher
from typing import Iterable

from .api_client import ApiClient
from .config import INDEX_PATH
from .models import SkinItem

LOG = logging.getLogger(__name__)


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


class SearchIndex:
    def __init__(self, api: ApiClient, cfg: dict) -> None:
        self.api = api
        self.cfg = cfg
        self.threshold = float(cfg.get("search", {}).get("fuzzy_threshold", 55))
        self.max_results = int(cfg.get("search", {}).get("max_results", 25))
        self._items: list[SkinItem] = []

    def build(self, refresh: bool = False) -> int:
        items: list[SkinItem] = []
        try:
            items.extend(self.api.get_heroes_flat(refresh=refresh))
        except Exception as e:
            LOG.warning("heroes: %s", e)
        try:
            for hero in self.api.heroes_by_name_from_upgrade_menu():
                try:
                    items.extend(self.api.get_upgrade_skins(hero, refresh=refresh))
                except Exception as e:
                    LOG.debug("upgrade %s: %s", hero, e)
        except Exception as e:
            LOG.warning("upgrade menu: %s", e)
        try:
            items.extend(self.api.get_custom_skins(refresh=refresh))
        except Exception as e:
            LOG.warning("custom: %s", e)

        seen: set[str] = set()
        unique: list[SkinItem] = []
        for it in items:
            key = f"{it.download_url}|{it.skin_name}"
            if key in seen or not it.download_url:
                continue
            seen.add(key)
            unique.append(it)

        self._items = unique
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
                    for x in unique
                ],
                f,
                ensure_ascii=False,
                indent=2,
            )
        LOG.info("Index built: %d skins", len(unique))
        return len(unique)

    def load(self) -> None:
        if not INDEX_PATH.exists():
            self.build()
            return
        try:
            with open(INDEX_PATH, encoding="utf-8") as f:
                raw = json.load(f)
            self._items = [
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
        except (json.JSONDecodeError, OSError, TypeError):
            self.build()

    @property
    def items(self) -> list[SkinItem]:
        if not self._items:
            self.load()
        return self._items

    def search(self, query: str) -> list[SkinItem]:
        if not self._items:
            self.load()
        scored = [( _score(query, it), it) for it in self._items]
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
