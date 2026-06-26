"""Deteksi tipe/grade skin MLBB dari data API."""

from __future__ import annotations

import re
from urllib.parse import unquote

from .models import SkinItem

# Urutan penting — yang lebih spesifik dulu
_GRADE_RULES: list[tuple[str, re.Pattern[str]]] = [
    ("collector", re.compile(r"\bcollector\b", re.I)),
    ("starlight", re.compile(r"\bstar\s*light\b|\bstarlight\b", re.I)),
    ("legend", re.compile(r"\blegend\b", re.I)),
    ("epic", re.compile(r"\bepic\b", re.I)),
    ("elite", re.compile(r"\belite\b", re.I)),
    ("prime", re.compile(r"\bprime\b", re.I)),
    ("special", re.compile(r"\bspecial\b", re.I)),
    ("limited", re.compile(r"\blimited\b", re.I)),
    ("annual", re.compile(r"\bannual\b", re.I)),
    ("basic", re.compile(r"\bbasic\b|\bbasic\s+skin\b|\bdefault\s+skin\b|\bnormal\s+skin\b", re.I)),
]

SKIN_GRADES: list[tuple[str, str]] = [
    ("Basic", "basic"),
    ("Elite", "elite"),
    ("Epic", "epic"),
    ("Legend", "legend"),
    ("Collector", "collector"),
    ("Starlight", "starlight"),
    ("Special", "special"),
    ("Limited", "limited"),
    ("Prime", "prime"),
]

_BACKUP = re.compile(r"\bbackup\b", re.I)


def _normalize_blob(text: str) -> str:
    decoded = unquote(text or "")
    spaced = re.sub(r"[%_\-./]+", " ", decoded)
    return re.sub(r"\s+", " ", spaced).strip().lower()


def _blob(item: SkinItem) -> str:
    return _normalize_blob(
        " ".join(
            [
                item.skin_name,
                item.hero_name,
                item.api_category,
                item.download_url,
                item.image_url,
                item.category,
            ]
        )
    )


def detect_skin_grade(item: SkinItem) -> str | None:
    """Return grade key (basic/epic/...) atau None jika backup/tidak dikenali."""
    if item.source not in ("heroes", ""):
        return None
    text = _blob(item)
    if _BACKUP.search(text):
        return None

    raw = _normalize_blob(item.api_category or item.skin_name or "")
    for _label, key in SKIN_GRADES:
        if raw == key:
            return key

    for key, pattern in _GRADE_RULES:
        if pattern.search(text):
            return key
    return None


def grade_label(key: str) -> str:
    for label, k in SKIN_GRADES:
        if k == key:
            return label
    return key.title()
