"""Data models."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Optional


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

    @classmethod
    def from_hero_entry(cls, data: dict[str, Any]) -> SkinItem:
        return cls(
            id=str(data.get("id", "")),
            hero_name=str(data.get("heroname", data.get("heroName", ""))),
            skin_name=str(data.get("heroname", data.get("heroName", data.get("name", "")))),
            image_url=str(data.get("img", "")),
            download_url=str(data.get("downloadLink", data.get("url", ""))),
            category=str(data.get("category", "")),
            mini_patch=bool(int(data.get("mini_patch", 0) or 0)),
            source="heroes",
        )

    @classmethod
    def from_upgrade_entry(cls, data: dict[str, Any], hero: str = "") -> SkinItem:
        name = str(data.get("name", data.get("skinName", data.get("heroname", ""))))
        return cls(
            id=str(data.get("id", "")),
            hero_name=hero or str(data.get("heroName", data.get("category", ""))),
            skin_name=name,
            image_url=str(data.get("img", data.get("image", ""))),
            download_url=str(data.get("url", data.get("downloadLink", ""))),
            category=str(data.get("category", hero)),
            mini_patch=bool(int(data.get("mini_patch", 0) or 0)),
            source="upgrade",
        )

    @classmethod
    def from_custom_entry(cls, data: dict[str, Any]) -> SkinItem:
        return cls(
            id=str(data.get("id", "")),
            hero_name=str(data.get("heroName", data.get("name", ""))),
            skin_name=str(data.get("skinName", data.get("name", ""))),
            image_url=str(data.get("img", "")),
            download_url=str(data.get("url", data.get("downloadLink", ""))),
            category=str(data.get("category", "")),
            source="custom",
        )

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
