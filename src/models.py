"""Data models."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Optional

from .name_resolver import resolve_name, strip_markup

@dataclass
class SkinItem:
    id: str
    hero_name: str
    skin_name: str
    image_url: str
    download_url: str
    category: str = ""
    mini_patch: bool = False
    source: str = "heroes"
    api_category: str = ""  # key POST API (bisa terpotong, jangan diubah)

    @classmethod
    def from_hero_entry(
        cls,
        data: dict[str, Any],
        hero: str = "",
        corpus: set[str] | None = None,
    ) -> SkinItem:
        img = str(data.get("img", ""))
        dl = str(data.get("downloadLink", data.get("url", "")))
        raw_skin = str(data.get("heroname", data.get("heroName", data.get("name", ""))))
        hero_name = hero or str(data.get("heroName", ""))
        skin_name = resolve_name(
            raw_skin,
            hero=hero_name,
            img=img,
            download=dl,
            corpus=corpus,
        )
        return cls(
            id=str(data.get("id", "")),
            hero_name=hero_name,
            skin_name=skin_name,
            image_url=img,
            download_url=dl,
            category=str(data.get("category", "")),
            mini_patch=bool(int(data.get("mini_patch", 0) or 0)),
            source="heroes",
            api_category=raw_skin,
        )

    @classmethod
    def from_upgrade_entry(
        cls,
        data: dict[str, Any],
        hero: str = "",
        corpus: set[str] | None = None,
    ) -> SkinItem:
        img = str(data.get("img", data.get("image", "")))
        dl = str(data.get("url", data.get("downloadLink", "")))
        raw_name = str(data.get("name", data.get("skinName", data.get("heroname", ""))))
        api_cat = hero or str(data.get("heroName", data.get("category", "")))
        skin_name = resolve_name(
            raw_name,
            hero=api_cat.split(" - ")[0] if " - " in api_cat else api_cat,
            img=img,
            download=dl,
            corpus=corpus,
        )
        display_hero = resolve_name(api_cat, img=img, download=dl, corpus=corpus) if api_cat else api_cat
        return cls(
            id=str(data.get("id", "")),
            hero_name=display_hero,
            skin_name=skin_name,
            image_url=img,
            download_url=dl,
            category=str(data.get("category", api_cat)),
            mini_patch=bool(int(data.get("mini_patch", 0) or 0)),
            source="upgrade",
            api_category=api_cat,
        )

    @classmethod
    def from_custom_entry(cls, data: dict[str, Any], corpus: set[str] | None = None) -> SkinItem:
        img = str(data.get("img", ""))
        dl = str(data.get("url", data.get("downloadLink", "")))
        raw_skin = str(data.get("skinName", data.get("name", "")))
        raw_hero = str(data.get("heroName", data.get("name", "")))
        return cls(
            id=str(data.get("id", "")),
            hero_name=resolve_name(raw_hero, img=img, download=dl, corpus=corpus),
            skin_name=resolve_name(raw_skin, hero=raw_hero, img=img, download=dl, corpus=corpus),
            image_url=img,
            download_url=dl,
            category=str(data.get("category", "")),
            source="custom",
            api_category=raw_skin,
        )

    def label(self) -> str:
        """Teks tampilan penuh untuk menu."""
        hero = strip_markup(self.hero_name)
        skin = strip_markup(self.skin_name)
        if hero and skin and skin.lower() not in hero.lower():
            return f"{hero} - {skin}"
        return skin or hero

    def search_blob(self) -> str:
        return " ".join(
            [
                self.id,
                self.hero_name,
                self.skin_name,
                self.category,
                self.source,
            ]
        ).lower()


@dataclass
class BackupManifest:
    hero_id: str
    hero_name: str
    skin_name: str
    package: str
    injected_at: str
    files: list[str] = field(default_factory=list)
    source: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "hero_id": self.hero_id,
            "hero_name": self.hero_name,
            "skin_name": self.skin_name,
            "package": self.package,
            "injected_at": self.injected_at,
            "files": self.files,
            "source": self.source,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> BackupManifest:
        return cls(
            hero_id=str(data.get("hero_id", "")),
            hero_name=str(data.get("hero_name", "")),
            skin_name=str(data.get("skin_name", "")),
            package=str(data.get("package", "")),
            injected_at=str(data.get("injected_at", "")),
            files=list(data.get("files", [])),
            source=str(data.get("source", "")),
        )


@dataclass
class PreflightResult:
    ok: bool
    mode: str
    backend_name: str
    package: Optional[str]
    assets_path: Optional[str]
    messages: list[str] = field(default_factory=list)
