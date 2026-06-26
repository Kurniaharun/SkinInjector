"""Paginated list picker with search — Termux friendly."""

from __future__ import annotations

from typing import Optional

from rich.console import Console
from rich.text import Text

PAGE_SIZE = 20


def pick_from_list(
    console: Console,
    options: list[str],
    title: str,
    *,
    page_size: int = PAGE_SIZE,
) -> Optional[int]:
    """Return global index in *options*, or None."""
    if not options:
        console.print("[red]Tidak ada data.[/]")
        return None

    filter_q = ""
    page = 0

    while True:
        if filter_q:
            fq = filter_q.lower()
            filtered = [o for o in options if fq in o.lower()]
        else:
            filtered = options

        if not filtered:
            console.print(f"[yellow]Tidak ada hasil untuk '{filter_q}'[/]")
            filter_q = ""
            page = 0
            continue

        total_pages = max(1, (len(filtered) + page_size - 1) // page_size)
        if page >= total_pages:
            page = total_pages - 1

        start = page * page_size
        page_items = filtered[start : start + page_size]

        console.print()
        console.print(f"[bold]{title}[/]")
        console.print(
            f"[dim]Halaman {page + 1}/{total_pages} | "
            f"{len(filtered)} item"
            + (f" | filter: [cyan]{filter_q}[/]" if filter_q else "")
            + "[/]"
        )
        console.print("[dim]Nomor = pilih | [S] cari | [N] next | [P] prev | [0] kembali[/]\n")

        for i, label in enumerate(page_items, start + 1):
            line = Text(f"  {i:>2}. ", style="cyan") + Text(label)
            console.print(line, soft_wrap=True, overflow="fold")

        try:
            raw = input("\n>>> ").strip()
        except (EOFError, KeyboardInterrupt):
            return None

        low = raw.lower()
        if low in ("0", ""):
            return None
        if low == "n":
            if page < total_pages - 1:
                page += 1
            else:
                console.print("[dim]Sudah halaman terakhir.[/]")
            continue
        if low == "p":
            if page > 0:
                page -= 1
            else:
                console.print("[dim]Sudah halaman pertama.[/]")
            continue
        if low == "s":
            try:
                filter_q = input("Cari nama: ").strip()
            except (EOFError, KeyboardInterrupt):
                return None
            page = 0
            continue

        try:
            num = int(raw)
        except ValueError:
            console.print("[red]Input tidak valid.[/]")
            continue

        if 1 <= num <= len(page_items):
            chosen = page_items[num - 1]
            return options.index(chosen)

        console.print(f"[red]Pilih 1-{len(page_items)}[/]")


def pick_skin_labels(
    console: Console,
    labels: list[str],
    title: str,
) -> Optional[int]:
    return pick_from_list(console, labels, title, page_size=15)
