"""CLI bridge untuk server.js — status, search, skins, inject."""

from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

_instance = None


def get_app():
    global _instance
    if _instance is None:
        from src.app import App

        _instance = App()
        _instance.init()
    return _instance


def _skin_dict(s) -> dict:
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


def cmd_status() -> dict:
    app = get_app()
    pf = app.preflight or app.init()
    from src.catalog_store import catalog_ready, catalog_summary

    return {
        "ok": pf.ok,
        "backend": pf.backend_name,
        "package": pf.package,
        "assets_path": pf.assets_path,
        "catalog": catalog_summary() if catalog_ready() else "belum ada",
        "heroes": len(app.api.list_hero_names()),
    }


def cmd_search(query: str) -> list[dict]:
    app = get_app()
    app.search.ensure_for_search()
    results = list(app.search.search(query))
    if len(results) < 8:
        app.api.warmup()
        for hero in app.api.search_hero_names(query)[:6]:
            results.extend(app.api.get_skins_for_hero(hero))
        for entry in app.api.search_upgrade_entries(query)[:8]:
            results.extend(app.api.get_upgrade_skins_for_entry(entry))
        results.extend(app.api.search_effects(query))
    seen: set[str] = set()
    out: list[dict] = []
    for s in results:
        if s.download_url and s.download_url not in seen:
            seen.add(s.download_url)
            out.append(_skin_dict(s))
    return out[:40]


def cmd_hero_skins(name: str) -> list[dict]:
    app = get_app()
    app.api.warmup()
    return [_skin_dict(s) for s in app.api.get_skins_for_hero(name)]


def cmd_upgrade_skins(index: int) -> list[dict]:
    app = get_app()
    app.api.warmup()
    menu = app.api.get_upgrade_menu()
    if index < 0 or index >= len(menu):
        return []
    entry = menu[index]
    return [_skin_dict(s) for s in app.api.get_upgrade_skins_for_entry(entry)]


def cmd_effect_skins(category: str) -> list[dict]:
    app = get_app()
    app.api.warmup()
    return [_skin_dict(s) for s in app.api.get_effects(category)]


def cmd_bundle_skins(bundle_id: str) -> list[dict]:
    app = get_app()
    app.api.warmup()
    name = ""
    for b in app.api.get_custom_bundles():
        if str(b.get("id")) == bundle_id:
            name = str(b.get("name", ""))
            break
    return [_skin_dict(s) for s in app.api.get_custom_bundle_skins(bundle_id, name)]


def cmd_inject(payload: dict) -> dict:
    from src.errors import InjectorError
    from src.models import SkinItem
    from src.progress import NullReporter

    app = get_app()
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
        msg = app.inject_skin(skin, reporter=NullReporter())
        return {"ok": True, "message": msg}
    except InjectorError as e:
        return {"ok": False, "message": str(e)}


def main() -> None:
    if len(sys.argv) < 2:
        print(json.dumps({"error": "usage: web_bridge <cmd> [args]"}))
        sys.exit(1)
    cmd = sys.argv[1]
    try:
        if cmd == "status":
            out = cmd_status()
        elif cmd == "search":
            out = cmd_search(sys.argv[2] if len(sys.argv) > 2 else "")
        elif cmd == "hero_skins":
            out = cmd_hero_skins(sys.argv[2])
        elif cmd == "upgrade_skins":
            out = cmd_upgrade_skins(int(sys.argv[2]))
        elif cmd == "effect_skins":
            out = cmd_effect_skins(sys.argv[2])
        elif cmd == "bundle_skins":
            out = cmd_bundle_skins(sys.argv[2])
        elif cmd == "inject":
            out = cmd_inject(json.loads(sys.argv[2]))
        else:
            out = {"error": f"unknown cmd: {cmd}"}
    except Exception as e:
        out = {"error": str(e)}
    print(json.dumps(out, ensure_ascii=False))


if __name__ == "__main__":
    main()
