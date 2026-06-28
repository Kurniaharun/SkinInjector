"""SkinJECT web API — status, browse, search, inject."""

from __future__ import annotations

from typing import Any

from ..catalog_store import catalog_ready, catalog_summary, read_json
from ..errors import InjectorError
from ..models import SkinItem
from ..progress import NullReporter
from ..ui.branding import APP_NAME, AUTHOR, VERSION

EFFECT_CATS = [
    {"id": "Recall Animations", "label": "Recall"},
    {"id": "Emotes", "label": "Emotes"},
    {"id": "TRAIL ANIMATION", "label": "Trail"},
    {"id": "RESPAWN ANIMATION", "label": "Respawn"},
    {"id": "PAINTED SKIN", "label": "Painted"},
    {"id": "ELIMINATED BATTLE", "label": "Eliminated"},
]

_instance: "WebApi | None" = None


def get_web_api() -> "WebApi":
    global _instance
    if _instance is None:
        _instance = WebApi()
    return _instance


def skin_dict(s: SkinItem) -> dict[str, Any]:
    return {
        "id": s.id,
        "hero_name": s.hero_name,
        "skin_name": s.skin_name,
        "image_url": s.image_url,
        "download_url": s.download_url,
        "source": s.source,
        "category": s.category,
        "label": s.label(),
    }


class WebApi:
    def __init__(self) -> None:
        self._app = None

    @property
    def app(self):
        if self._app is None:
            from ..app import App

            self._app = App()
            self._app.init()
        return self._app

    def status(self) -> dict[str, Any]:
        pf = self.app.preflight or self.app.init()
        return {
            "ok": pf.ok,
            "backend": pf.backend_name,
            "package": pf.package,
            "assets_path": pf.assets_path,
            "catalog": catalog_summary() if catalog_ready() else "belum ada",
            "heroes": len(self.app.api.list_hero_names()),
        }

    def meta(self) -> dict[str, Any]:
        return {
            "app": APP_NAME,
            "author": AUTHOR,
            "version": VERSION,
            "meta": read_json("meta", {}),
        }

    def heroes(self) -> dict[str, Any]:
        icons = self.app.api.hero_icon_map()
        names = sorted(icons.keys(), key=str.lower)
        return {
            "heroes": [
                {"name": name, "label": name, "image_url": icons.get(name, "")}
                for name in names
            ]
        }

    def roles(self) -> dict[str, Any]:
        cats = read_json("role_categories", [])
        roles = [r.get("name") or r for r in cats if r]
        return {"roles": [r for r in roles if r]}

    def role_heroes(self, role: str) -> dict[str, Any]:
        by_role = read_json("heroes_by_role", {})
        icons = self.app.api.hero_icon_map()
        heroes = by_role.get(role, [])
        return {
            "heroes": [
                {"name": name, "label": name, "image_url": icons.get(name, "")}
                for name in heroes
            ]
        }

    def upgrade_menu(self) -> dict[str, Any]:
        menu = read_json("upgrade_menu", [])
        labels = read_json("upgrade_labels", [])
        items = []
        for i, entry in enumerate(menu):
            items.append(
                {
                    "index": i,
                    "id": entry.get("id", ""),
                    "key": entry.get("heroName", ""),
                    "label": labels[i] if i < len(labels) else entry.get("heroName", ""),
                    "image_url": entry.get("img", ""),
                }
            )
        return {"items": items}

    def custom_bundles(self) -> dict[str, Any]:
        bundles = read_json("custom_bundles", [])
        return {
            "bundles": [
                {
                    "id": str(b.get("id", "")),
                    "name": b.get("name") or f"Bundle {b.get('id', '')}",
                    "image_url": b.get("img", ""),
                }
                for b in bundles
            ]
        }

    def effect_categories(self) -> dict[str, Any]:
        return {"categories": EFFECT_CATS}

    def hero_skins(self, name: str) -> dict[str, Any]:
        self.app.api.warmup()
        skins = [skin_dict(s) for s in self.app.api.get_skins_for_hero(name)]
        return {"skins": skins}

    def upgrade_skins(self, index: int) -> dict[str, Any]:
        self.app.api.warmup()
        menu = self.app.api.get_upgrade_menu()
        if index < 0 or index >= len(menu):
            return {"skins": []}
        skins = [skin_dict(s) for s in self.app.api.get_upgrade_skins_for_entry(menu[index])]
        return {"skins": skins}

    def effect_skins(self, category: str) -> dict[str, Any]:
        self.app.api.warmup()
        skins = [skin_dict(s) for s in self.app.api.get_effects(category)]
        return {"skins": skins}

    def bundle_skins(self, bundle_id: str) -> dict[str, Any]:
        self.app.api.warmup()
        name = ""
        for b in self.app.api.get_custom_bundles():
            if str(b.get("id")) == bundle_id:
                name = str(b.get("name", ""))
                break
        skins = [skin_dict(s) for s in self.app.api.get_custom_bundle_skins(bundle_id, name)]
        return {"skins": skins}

    def search(self, query: str) -> dict[str, Any]:
        self.app.search.ensure_for_search()
        results = list(self.app.search.search(query))
        if len(results) < 8:
            self.app.api.warmup()
            for hero in self.app.api.search_hero_names(query)[:6]:
                results.extend(self.app.api.get_skins_for_hero(hero))
            for entry in self.app.api.search_upgrade_entries(query)[:8]:
                results.extend(self.app.api.get_upgrade_skins_for_entry(entry))
            results.extend(self.app.api.search_effects(query))
        seen: set[str] = set()
        out: list[dict[str, Any]] = []
        for s in results:
            if s.download_url and s.download_url not in seen:
                seen.add(s.download_url)
                out.append(skin_dict(s))
        return {"skins": out[:40]}

    def inject(self, payload: dict[str, Any]) -> dict[str, Any]:
        skin = SkinItem(
            id=str(payload.get("id", "")),
            hero_name=str(payload.get("hero_name", "")),
            skin_name=str(payload.get("skin_name", "")),
            image_url=str(payload.get("image_url", "")),
            download_url=str(payload.get("download_url", "")),
            source=str(payload.get("source", "web")),
        )
        if not skin.download_url:
            return {"ok": False, "message": "URL download kosong"}
        try:
            msg = self.app.inject_skin(skin, reporter=NullReporter())
            return {"ok": True, "message": msg}
        except InjectorError as e:
            return {"ok": False, "message": str(e)}
