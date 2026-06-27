"""Expand truncated skin names from API (server returns 'King Of Mua..')."""

from __future__ import annotations

import re
from typing import Any
from urllib.parse import unquote, urlparse

BB_TAG = re.compile(r"\[/?b\]", re.I)
TRUNC_MARK = re.compile(r"\.{2,}$")
PAREN = re.compile(r"\(([^)]+)\)")
SPLIT_CHARS = re.compile(r"[^\w\s.\-'/]+")
EMOJI = re.compile(r"[\U0001F300-\U0001FAFF\u2600-\u27BF]+")
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
        "skin",
        "basic",
        "img",
        "image",
        "gambar",
        "hero",
        "portrait",
    }
)

# API memotong kata di tengah — lengkapi sufiks umum MLBB
WORD_COMPLETIONS: dict[str, str] = {
    "mua": "Muai Thai",
    "muai": "Muai Thai",
    "muay": "Muay Thai",
    "tig": "Tiger",
    "tige": "Tiger",
    "tiger": "Tiger",
    "shir": "Shiryu",
    "shiry": "Shiryu",
    "scave": "Scavenger",
    "scaven": "Scavenger",
    "furio": "Furious Tiger",
    "furiou": "Furious Tiger",
    "red": "Red Breach",
    "lob": "Lone Defender",
    "lo": "Lone Defender",
    "lone": "Lone Defender",
    "fi": "Fission Soul",
    "fis": "Fission Soul",
    "fiss": "Fission Soul",
    "em": "Empyrean",
    "emp": "Empyrean",
    "empi": "Empyrean",
    "basi": "Basic",
    "basic": "Basic",
    "hip": "Hip Hop Boy",
    "kin": "King Of Muai Thai",
    "bal": "Balistic",
    "go": "Go Ballistic",
    "libra": "Libra Shiryu",
    "champ": "Champion",
    "dawn": "Dawning",
    "star": "Starlight",
    "starl": "Starlight",
    "seiya": "Saint Seiya",
    "kof": "K.O.F",
    "epic": "Epic",
    "elite": "Elite",
    "special": "Special",
    "ru": "Ruins Scavenger",
    "ruin": "Ruins Scavenger",
    "ve": "Venom Cobra",
    "ven": "Venom Cobra",
    "or": "Orochi Chris",
    "oro": "Orochi Chris",
    "dec": "Demon Hunter",
    "yas": "Yasutsuna",
    "sna": "Snake Lord",
    "jav": "Javelin Master",
    "ligh": "Lightborn",
    "light": "Lightborn",
    "blue": "Blue Spectre",
    "male": "Classic Malefic",
    "arde": "Ardent Spirit",
    "p": "Phantom",
    "w": "West",
    "q": "Queen",
    "gra": "Grand",
    "pu": "Puppet",
    "li": "Light",
    "ca": "Carapace",
    "i": "Imperial",
    "s": "Special",
    "t": "Tiger",
    "b": "Basic",
    "d": "Dawning",
    "k": "King Of Muai Thai",
}

SHORT_TOKEN: dict[str, str] = {
    **{k: v for k, v in WORD_COMPLETIONS.items() if len(k) <= 4},
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
    return unquote(urlparse(url or "").path or "").rsplit("/", 1)[-1]


def _stem(filename: str) -> str:
    if not filename:
        return ""
    return unquote(filename.rsplit(".", 1)[0]).strip()


def _hero_base(hero: str) -> str:
    """Ambil nama hero utama dari 'Alucard-Lo' / 'X Borg'."""
    text = strip_markup(hero).split("-")[0].strip()
    if not text:
        return hero.strip()
    return text


def _beautify_skin(text: str) -> str:
    text = EMOJI.sub("", strip_markup(text)).replace("+", " ").strip(" -_")
    text = re.sub(r"\s+", " ", text)
    if not text:
        return text
    if re.fullmatch(r"S\d+", text, re.I):
        return text.upper()
    if text.upper() in ("S1", "S2", "S3", "S7", "S9", "S11", "S15", "S18", "S19", "S23"):
        return text.upper()
    if text.isupper() and len(text) <= 6:
        return text.title()
    return text


def _format_label(label: str) -> str:
    if " - " not in label:
        t = strip_markup(label)
        return t.title() if t.isupper() else t
    hero, skin = label.split(" - ", 1)
    skin = skin.strip()
    if not skin:
        return hero.title()
    if re.fullmatch(r"S\d+", skin, re.I):
        skin = skin.upper()
    elif skin.isupper() and len(skin) > 3:
        skin = skin.title()
    else:
        skin = skin.title()
    hero_fmt = hero.title() if hero.isupper() else hero
    return f"{hero_fmt} - {skin}"


def _split_upgrade_category(raw: str) -> tuple[str, str]:
    """Pisah Hero + skin abbrev dari berbagai format API."""
    text = strip_markup(raw)
    text = TRUNC_MARK.sub("", text).rstrip(". ").strip()
    if not text:
        return "", ""

    if " - " in text:
        hero, skin = text.split(" - ", 1)
        return hero.strip(), skin.strip()

    if "-" in text:
        hero, skin = text.split("-", 1)
        return hero.strip(), skin.strip()

    parts = text.rsplit(" ", 1)
    if len(parts) == 2 and len(parts[1]) <= 14:
        return parts[0].strip(), parts[1].strip()

    return text, ""


def extract_url_hints(img: str = "", download: str = "") -> list[str]:
    hints: list[str] = []
    for url in (img, download):
        if not url:
            continue
        decoded = unquote(url).replace("+", " ")
        for match in PAREN.finditer(decoded):
            inner = match.group(1).strip()
            if len(inner) > 2 and not inner.isdigit():
                hints.append(inner)
        stem = _beautify_skin(_stem(_filename(url)))
        if not stem:
            continue
        hints.append(stem)
        for chunk in SPLIT_CHARS.split(stem):
            chunk = chunk.strip(" -_")
            if len(chunk) > 2 and chunk.lower() not in SKIP:
                hints.append(chunk)
        parts = re.split(r"\s*-\s*", stem, maxsplit=1)
        if len(parts) > 1 and len(parts[1]) > 2:
            hints.append(parts[1].strip())
        # "basic skin hero" / "basic alpha"
        m = re.search(r"basic\s+(?:skin\s+)?(.+)", stem, re.I)
        if m:
            hints.append("Basic")
    return hints


def _label_from_img(hero: str, img: str = "", download: str = "") -> str | None:
    """Label upgrade dari nama file gambar menu (paling akurat)."""
    hero_base = _hero_base(hero)
    hlow = hero_base.lower()

    for url in (img, download):
        if not url:
            continue
        stem = _beautify_skin(_stem(_filename(url)))
        if not stem or re.match(r"^[a-f0-9]{8,}$", stem, re.I):
            continue
        if re.match(r"^\d", stem) or re.search(r"\(\d+\)\s*$", stem):
            continue
        slow = stem.lower()

        if re.search(r"\bbasic\b", slow):
            return f"{hero_base} - Basic"

        if slow.startswith(hlow):
            rest = _beautify_skin(stem[len(hero_base) :])
            if rest and rest.lower() not in SKIP:
                if re.fullmatch(r"S\d+", rest, re.I):
                    return f"{hero_base} - {rest.upper()}"
                expanded = _expand_token(rest)
                return f"{hero_base} - {expanded}"

        # Stem tanpa hero: "Elite.jpg", "Starlight.jpg", "Granger Valentine"
        if (
            hlow not in slow
            and len(slow) >= 3
            and not re.match(r"^\d", slow)
            and slow.lower() not in SKIP
            and not re.match(r"^s\d+$", slow)
        ):
            words = stem.split()
            skin_words = [
                w
                for w in words
                if w.lower()[:4] != hlow[:4]
                and not w.lower().startswith(hlow[:4])
                and hlow[:4] not in w.lower()[:4]
            ]
            if skin_words:
                return f"{hero_base} - {_expand_token(' '.join(skin_words))}"
            return f"{hero_base} - {_expand_token(stem)}"

        # Hero singkatan di img: "Lance zodiac" untuk Lancelot
        if hlow[:4] in slow or slow.startswith(hlow[:4]):
            for token in stem.split():
                if token.lower() not in SKIP and hlow[:4] not in token.lower()[:4]:
                    if len(token) >= 3:
                        return f"{hero_base} - {_expand_token(token)}"

        if hlow in slow:
            idx = slow.find(hlow)
            rest = _beautify_skin(stem[idx + len(hero_base) :])
            if rest and rest.lower() not in SKIP and not re.match(r"^\d", rest):
                expanded = _expand_token(rest)
                return f"{hero_base} - {expanded}"

        # "basic alpha" / hero di akhir
        m = re.match(r"basic\s+(.+)", slow, re.I)
        if m and hlow in m.group(1).lower():
            return f"{hero_base} - Basic"

    return None


def _expand_token(token: str) -> str:
    text = strip_markup(token)
    if not text:
        return text
    low = text.lower()
    if low in SHORT_TOKEN:
        return SHORT_TOKEN[low]
    completed = _complete_core(text)
    if completed != text:
        return completed
    if corpus_match := _corpus_expand(text, None, min_len=2):
        return corpus_match
    return text


def _corpus_expand(prefix: str, corpus: set[str] | None, *, min_len: int = 3) -> str:
    if not corpus:
        return ""
    plow = prefix.lower()
    if len(plow) < min_len:
        return ""
    best = ""
    for candidate in corpus:
        text = strip_markup(str(candidate))
        if is_truncated(text):
            continue
        low = text.lower()
        if low.startswith(plow) and len(text) > len(best):
            best = text
    return best


def _complete_core(core: str) -> str:
    words = core.split()
    if not words:
        return core

    last = words[-1].lower()
    if len(words) == 1 and last in SHORT_TOKEN:
        return SHORT_TOKEN[last]

    for key, full in sorted(WORD_COMPLETIONS.items(), key=lambda x: -len(x[0])):
        if len(key) == 1 and (len(last) > 1 or any(c.isdigit() for c in last)):
            continue
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

    if "-" in name and is_truncated(name) and " - " not in name:
        hero_part, skin_part = name.split("-", 1)
        skin_resolved = resolve_name(
            TRUNC_MARK.sub("", skin_part).rstrip(". "),
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
        low = text.lower()
        if PAREN.search(str(hint)) or "(" in str(hint):
            if len(prefix_low) >= 2 and (low.startswith(prefix_low) or prefix_low in low):
                if len(text) > len(prefix) + 1:
                    return text

    completed = _complete_core(prefix)
    return completed if completed else name


def resolve_upgrade_menu_label(entry: dict[str, Any], corpus: set[str] | None = None) -> str:
    """Label menu upgrade — img URL + expand token + corpus."""
    raw = strip_markup(str(entry.get("heroName") or entry.get("name") or ""))
    img = str(entry.get("img", ""))
    download = str(entry.get("downloadLink") or entry.get("url") or "")

    if not raw:
        return raw

    hero_part, skin_part = _split_upgrade_category(raw)
    if not hero_part:
        return raw

    if not is_truncated(raw) and skin_part:
        return _format_label(f"{hero_part} - {skin_part}" if skin_part else hero_part)
    if not is_truncated(raw):
        return _format_label(hero_part)

    # 1) Nama file gambar (paling akurat)
    img_label = _label_from_img(hero_part, img, download)
    if img_label:
        if skin_part:
            rest = img_label.split(" - ", 1)[-1]
            if re.fullmatch(r"S\d+", rest, re.I):
                exp = _expand_token(skin_part)
                if exp.lower() != skin_part.lower():
                    return _format_label(f"{hero_part} - {exp}")
        return _format_label(img_label)

    # 2) Token skin dari key API (Lo, Fi, Red, Basi, ...)
    if skin_part:
        sp_low = skin_part.lower()
        if sp_low in SHORT_TOKEN:
            return _format_label(f"{hero_part} - {SHORT_TOKEN[sp_low]}")

        expanded = _expand_token(skin_part)
        if expanded and expanded.lower() != sp_low:
            return _format_label(f"{hero_part} - {expanded}")

        hints = extract_url_hints(img, download)
        for hint in hints:
            hl = strip_markup(hint)
            if re.match(r"^\d", hl):
                continue
            hlow = hl.lower()
            hb = _hero_base(hero_part).lower()
            if hlow.startswith(hb):
                rest = _beautify_skin(hl[len(_hero_base(hero_part)) :])
                if rest:
                    return _format_label(f"{hero_part} - {_expand_token(rest)}")
            if sp_low and len(sp_low) >= 2 and sp_low in hlow:
                return _format_label(f"{hero_part} - {_expand_token(hl)}")
            if hb in hlow:
                tokens = [
                    t
                    for t in hl.split()
                    if t.lower() != hb and t.lower() not in SKIP
                ]
                if tokens and tokens[0].lower()[:4] == hb[:4]:
                    tokens = tokens[1:]
                if tokens:
                    return _format_label(f"{hero_part} - {_expand_token(' '.join(tokens))}")

        if corpus:
            best = _corpus_expand(skin_part, corpus, min_len=1)
            if best and len(best) > len(skin_part):
                return _format_label(f"{hero_part} - {best}")

        if skin_part:
            return _format_label(f"{hero_part} - {_beautify_skin(skin_part)}")

    # 3) Hero saja terpotong (Guinevere .., Minsitthar..)
    img_label = _label_from_img(hero_part, img, download)
    if img_label:
        return _format_label(img_label)

    hints = extract_url_hints(img, download)
    for hint in hints:
        if hint.lower() == "basic" or "basic" in hint.lower():
            return _format_label(f"{_hero_base(hero_part)} - Basic")

    # Fallback: hero tanpa skin → Basic (umum untuk entry upgrade)
    if not skin_part and _hero_base(hero_part):
        return _format_label(f"{_hero_base(hero_part)} - Basic")

    resolved = resolve_name(raw, img=img, download=download, corpus=corpus)
    return _format_label(resolved)


def resolve_category_label(entry: dict[str, Any], corpus: set[str] | None = None) -> str:
    return resolve_upgrade_menu_label(entry, corpus)


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
