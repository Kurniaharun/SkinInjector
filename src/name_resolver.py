"""Expand truncated skin names from API (server returns 'King Of Mua..')."""

from __future__ import annotations

import re
from typing import Any
from urllib.parse import unquote, urlparse

BB_TAG = re.compile(r"\[/?b\]", re.I)
TRUNC_MARK = re.compile(r"\.{2,}$")
PAREN = re.compile(r"\(([^)]+)\)")
SPLIT_CHARS = re.compile(r"[^\w\s.\-'/]+")
SKIP = frozenset(
    {
        "backup",
        "raw",
        "main",
        "refs",
        "heads",
        "github",
        "githubusercontent",
        "zip",
        "jpg",
        "jpeg",
        "png",
        "webp",
        "uploads",
        "wp",
        "content",
    }
)

# API memotong kata di tengah — lengkapi sufiks umum MLBB
WORD_COMPLETIONS: dict[str, str] = {
    "mua": "Muai Thai",
    "muai": "Muai Thai",
    "muay": "Muay Thai",
    "tig": "Tiger",
    "tige": "Tiger",
    "shir": "Shiryu",
    "shiry": "Shiryu",
    "scave": "Scavenger",
    "scaven": "Scavenger",
    "furio": "Furious Tiger",
    "furiou": "Furious Tiger",
    "red": "Red Breach",
    "lob": "Lone Defender",
    "lo": "Lone Defender",
    "fi": "Fission Soul",
    "em": "Empyrean",
    "basi": "Basic",
    "hip": "Hip Hop Boy",
    "kin": "King Of Muai Thai",
    "bal": "Balistic",
    "go": "Go Ballistic",
    "libra": "Libra Shiryu",
    "champ": "Champion",
    "dawn": "Dawning",
    "star": "Starlight",
    "seiya": "Saint Seiya",
    "kof": "K.O.F",
    "epic": "Epic",
    "elite": "Elite",
    "special": "Special",
}

SHORT_TOKEN: dict[str, str] = {
    "kin": "King Of Muai Thai",
    "hip": "Hip Hop Boy",
    "go": "Go Ballistic",
    "furio": "Furious Tiger",
    "furiou": "Furious Tiger",
}


def strip_markup(name: str) -> str:
    text = BB_TAG.sub("", name or "").strip()
    return re.sub(r"\s+", " ", text)


def is_truncated(name: str) -> bool:
    text = strip_markup(name)
    return bool(TRUNC_MARK.search(text))


def _filename(url: str) -> str:
    if not url:
        return ""
    return unquote(urlparse(url).path or "").rsplit("/", 1)[-1]


def _stem(filename: str) -> str:
    if not filename:
        return ""
    return unquote(filename.rsplit(".", 1)[0]).strip()


def extract_url_hints(img: str = "", download: str = "") -> list[str]:
    hints: list[str] = []
    for url in (img, download):
        if not url:
            continue
        decoded = unquote(url)
        for match in PAREN.finditer(decoded):
            inner = match.group(1).strip()
            if len(inner) > 2:
                hints.append(inner)
        stem = _stem(_filename(url))
        for chunk in SPLIT_CHARS.split(stem):
            chunk = chunk.strip(" -_")
            if len(chunk) > 2 and chunk.lower() not in SKIP:
                hints.append(chunk)
        parts = re.split(r"\s*-\s*", stem, maxsplit=1)
        if len(parts) > 1 and len(parts[1]) > 3:
            hints.append(parts[1].strip())
    return hints


def _complete_core(core: str) -> str:
    words = core.split()
    if not words:
        return core

    last = words[-1].lower()
    if len(words) == 1 and last in SHORT_TOKEN:
        return SHORT_TOKEN[last]

    for key, full in sorted(WORD_COMPLETIONS.items(), key=lambda x: -len(x[0])):
        if not (last == key or last.startswith(key) or key.startswith(last)):
            continue
        prefix = " ".join(words[:-1])
        if prefix and full.lower().startswith(prefix.lower()):
            return full
        if prefix:
            return f"{prefix} {full}"
        return full
    return core


def resolve_name(
    raw: str,
    *,
    hero: str = "",
    img: str = "",
    download: str = "",
    corpus: set[str] | None = None,
) -> str:
    name = strip_markup(raw)
    if not name:
        return name

    if " - " in name and is_truncated(name):
        hero_part, skin_part = name.split(" - ", 1)
        skin_resolved = resolve_name(
            skin_part,
            hero=hero_part.strip(),
            img=img,
            download=download,
            corpus=corpus,
        )
        return f"{hero_part.strip()} - {skin_resolved}"

    if not is_truncated(name):
        return name

    prefix = TRUNC_MARK.sub("", name).rstrip(". ").strip()
    prefix_low = prefix.lower()
    pool = extract_url_hints(img, download)

    if prefix_low.startswith("backup"):
        for hint in pool:
            if "backup" in hint.lower():
                return strip_markup(hint)

    # Token pendek upgrade menu: Kin.. -> King Of Muai Thai
    token = prefix.split()[-1].lower() if prefix.split() else prefix_low
    if token in SHORT_TOKEN:
        if len(prefix.split()) == 1:
            return SHORT_TOKEN[token]
        head = " ".join(prefix.split()[:-1])
        return f"{head} {SHORT_TOKEN[token]}" if head else SHORT_TOKEN[token]

    pool.extend(corpus or [])
    best = ""
    for candidate in pool:
        text = strip_markup(str(candidate))
        if not text or is_truncated(text):
            continue
        low = text.lower()
        if len(prefix_low) >= 4 and low.startswith(prefix_low) and len(text) > len(best):
            best = text

    if best:
        return best

    for hint in sorted(pool, key=lambda x: len(str(x)), reverse=True):
        text = strip_markup(str(hint))
        if not text or is_truncated(text):
            continue
        if PAREN.search(str(hint)) or "(" in str(hint):
            if len(text) > len(prefix) + 1:
                return text

    completed = _complete_core(prefix)
    return completed if completed else name


def resolve_category_label(entry: dict[str, Any], corpus: set[str] | None = None) -> str:
    return resolve_name(
        str(entry.get("heroName") or entry.get("name") or ""),
        img=str(entry.get("img", "")),
        download=str(entry.get("downloadLink") or entry.get("url") or ""),
        corpus=corpus,
    )


def build_name_corpus(entries: list[dict[str, Any]]) -> set[str]:
    names: set[str] = set()
    for entry in entries:
        for key in ("heroname", "heroName", "name", "skinName"):
            val = entry.get(key)
            if val:
                names.add(strip_markup(str(val)))
        for hint in extract_url_hints(
            str(entry.get("img", "")),
            str(entry.get("downloadLink") or entry.get("url") or ""),
        ):
            names.add(strip_markup(hint))
    return {n for n in names if n and not is_truncated(n)}
