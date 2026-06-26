"""Branding, figlet banner, and styled UI helpers."""

from __future__ import annotations

from typing import TYPE_CHECKING

from .theme import DIVIDER_CHAR

if TYPE_CHECKING:
    from rich.console import Console

VERSION = "1.5"
APP_NAME = "SkinInjector"
TAGLINE = "MLBB Skin Injector for Termux"
REPO_URL = "https://github.com/Kurniaharun/SkinInjector"

_FALLBACK_BANNER = r"""
 ____  _             _   ___       _           _
/ ___|(_)_ __  _   _| | |_ _|_ __ | |_ ___  __| |___
\___ \| | '_ \| | | | |  | || '_ \| __/ _ \/ _` / __|
 ___) | | | | | |_| | |  | || | | | ||  __/ (_| \__ \
|____/|_|_| |_|\__,_|_| |___|_| |_|\__\___|\__,_|___/
"""

_MENU_ROWS: list[tuple[str, str, str]] = [
    ("1", "Browse Hero", "~130 hero | paginated | [S] cari"),
    ("2", "Search Skin", "cari hero, skin, recall, effect"),
    ("3", "Upgrade Skins", "324 skin upgrade"),
    ("4", "Custom Skins", "skin custom dari API"),
    ("5", "Restore Default", "kembalikan dari backup lokal"),
    ("6", "Status & Backup", "info sistem + daftar backup"),
    ("7", "Refresh Index", "opsional | index offline"),
    ("8", "Settings", "root / shizuku / auto"),
    ("9", "Effects & Recall", "recall | emote | trail | respawn"),
    ("10", "Backup Official", "inject BACKUP.zip dari server"),
    ("0", "Keluar", "sampai jumpa"),
]


def _figlet_text(text: str, font: str = "slant") -> str | None:
    try:
        import pyfiglet

        return pyfiglet.figlet_format(text, font=font).rstrip("\n")
    except Exception:
        return None


def get_banner(compact: bool = False) -> str:
    if compact:
        art = _figlet_text("SKIN", "small") or _figlet_text("SKIN", "standard")
        if art:
            return art
        return "  ╔═ SKIN INJECTOR ═╗"

    for font in ("slant", "ansi_shadow", "standard", "small"):
        art = _figlet_text("SKIN", font)
        if art and len(art.splitlines()) <= 8:
            sub = _figlet_text("INJECTOR", "small")
            if sub and len(sub.splitlines()) <= 4:
                return f"{art}\n{sub}"
            return art

    return _FALLBACK_BANNER.strip("\n")


def _colorize_banner(console: Console, text: str) -> None:
    lines = text.splitlines()
    palette = ["bright_cyan", "cyan", "bright_blue", "blue", "bright_magenta"]
    for i, line in enumerate(lines):
        color = palette[min(i, len(palette) - 1)]
        console.print(line, style=f"bold {color}")


def print_banner(console: Console, *, compact: bool = False) -> None:
    _colorize_banner(console, get_banner(compact=compact))


def print_tagline(console: Console) -> None:
    div = DIVIDER_CHAR * 2
    console.print(
        f"[dim]{div}[/] [bold white]{TAGLINE}[/] "
        f"[dim]v[/][bold cyan]{VERSION}[/] [dim]{div}[/]"
    )
    console.print(f"[dim]{REPO_URL}[/]\n")


def print_divider(console: Console, char: str | None = None, width: int = 52) -> None:
    c = char or DIVIDER_CHAR
    console.print(f"[dim]{c * width}[/]")


def print_splash(console: Console) -> None:
    print_banner(console, compact=False)
    print_tagline(console)


def render_menu_table(console: Console) -> None:
    from rich.table import Table

    table = Table(
        title="[bold white]MAIN MENU[/]",
        title_style="bold cyan",
        border_style="bright_black",
        header_style="bold magenta",
        show_lines=False,
        pad_edge=True,
        expand=False,
    )
    table.add_column("", style="bold cyan", width=4, justify="center")
    table.add_column("Menu", style="bold white", min_width=18)
    table.add_column("Info", style="dim", min_width=28)

    for key, label, info in _MENU_ROWS:
        if key == "0":
            table.add_row("", "", "")
        style_key = "bold red" if key == "0" else "bold cyan"
        table.add_row(f"[{style_key}]{key}[/]", label, info)

    console.print(table)
    console.print("[dim]Tips:[/] [cyan]S[/] cari [dim]|[/] [cyan]N[/]/[cyan]P[/] halaman [dim]|[/] tutup MLBB sebelum inject")


def render_status_bar(
    console: Console,
    *,
    backend: str,
    package: str,
    n_heroes: str | int,
    index_n: str | int,
) -> None:
    from rich.panel import Panel

    grid = (
        f"[bold cyan]Backend[/]  [green]{backend.upper()}[/]\n"
        f"[bold cyan]MLBB[/]      [yellow]{package}[/]\n"
        f"[bold cyan]Hero[/]      [white]{n_heroes}[/]  "
        f"[dim]|[/]  [bold cyan]Index[/] [dim]{index_n}[/]"
    )
    console.print(
        Panel(
            grid,
            title="[bold]STATUS[/]",
            border_style="cyan",
            padding=(0, 1),
        )
    )


def print_goodbye(console: Console) -> None:
    print_divider(console)
    art = _figlet_text("BYE", "small")
    if art:
        console.print(art, style="bold dim cyan")
    console.print("[dim]Terima kasih · tutup MLBB sudah di-restore?[/] :)\n")
