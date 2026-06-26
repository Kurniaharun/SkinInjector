"""Paginated list picker — simple."""

from __future__ import annotations

from typing import Optional

from rich.console import Console

from .theme import PROMPT, PROMPT_SYMBOL

PAGE_SIZE = 20


def pick_from_list(
    console: Console,
    options: list[str],
    title: str,
    *,
    page_size: int = PAGE_SIZE,
) -> Optional[int]:
    if not options:
        console.print("[red]Kosong.[/]")
        return None

    filter_q = ""
    page = 0

    while True:
        if filter_q:
            filtered = [o for o in options if filter_q.lower() in o.lower()]
        else:
            filtered = options

        if not filtered:
            console.print(f"[yellow]Tidak ada '{filter_q}'[/]")
            filter_q = ""
            page = 0
            continue

        total_pages = max(1, (len(filtered) + page_size - 1) // page_size)
        if page >= total_pages:
            page = total_pages - 1

        start = page * page_size
        page_items = filtered[start : start + page_size]

        console.print()
        console.print(f"[bold]{title}[/]  [dim]({page + 1}/{total_pages})[/]")
        if filter_q:
            console.print(f"[dim]filter: {filter_q}[/]")
        console.print("[dim]nomor | S cari | N/P halaman | 0 kembali[/]\n")

        for i, label in enumerate(page_items, start + 1):
            console.print(f"  [cyan]{i:>2}.[/] {label}")

        try:
            raw = console.input(f"\n[{PROMPT}]{PROMPT_SYMBOL}[/] ").strip()
        except (EOFError, KeyboardInterrupt):
            return None

        low = raw.lower()
        if low in ("0", ""):
            return None
        if low == "n" and page < total_pages - 1:
            page += 1
            continue
        if low == "p" and page > 0:
            page -= 1
            continue
        if low == "s":
            try:
                filter_q = console.input("cari: ").strip()
            except (EOFError, KeyboardInterrupt):
                return None
            page = 0
            continue

        try:
            num = int(raw)
        except ValueError:
            console.print("[red]?[/]")
            continue

        if 1 <= num <= len(page_items):
            return options.index(page_items[num - 1])

        console.print(f"[red]1-{len(page_items)}[/]")


def pick_skin_labels(console: Console, labels: list[str], title: str) -> Optional[int]:
    return pick_from_list(console, labels, title, page_size=15)
