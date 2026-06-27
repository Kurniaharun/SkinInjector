"""Branding — SkinJECT by KurrXd."""

from __future__ import annotations

from typing import TYPE_CHECKING

from .theme import DIVIDER_CHAR

if TYPE_CHECKING:
    from rich.console import Console

APP_NAME = "SkinJECT"
AUTHOR = "KurrXd"
VERSION = "2.0.0"
TAGLINE = "MLBB Skin Injector | Termux | Offline"

_MENU: list[tuple[str, str]] = [
    ("1", "Browse Hero"),
    ("2", "Browse by Role"),
    ("3", "Search Skin"),
    ("4", "Upgrade Skins"),
    ("5", "Custom Bundle"),
    ("6", "Effects & Recall"),
    ("7", "Restore Default"),
    ("8", "News / Update"),
    ("9", "Status"),
    ("10", "Update Katalog"),
    ("11", "Refresh Index"),
    ("12", "Settings"),
    ("13", "Backup Official"),
    ("14", "Advanced - Batch Apply"),
    ("0", "Keluar"),
]

_FIGLET_FONTS = ("slant", "standard", "small", "banner3-D", "doom")


def _figlet(text: str) -> str | None:
    try:
        import pyfiglet

        for font in _FIGLET_FONTS:
            try:
                art = pyfiglet.figlet_format(text, font=font).rstrip("\n")
                if art and max(len(line) for line in art.splitlines()) <= 72:
                    return art
            except Exception:
                continue
    except Exception:
        pass
    return None


def _rule(console: Console, *, style: str = "cyan") -> None:
    from rich.rule import Rule

    console.print(Rule(style=style, characters=DIVIDER_CHAR))


def print_banner(console: Console) -> None:
    art = _figlet(APP_NAME)
    console.print()
    if art:
        console.print(art, style="bold bright_cyan")
    else:
        console.print(
            "[bold bright_cyan]Skin[/][bold bright_magenta]JECT[/]",
        )
    console.print()
    console.print(f"        [bold bright_magenta]by {AUTHOR}[/]")
    console.print(f"        [dim]{TAGLINE}  v{VERSION}[/]")
    console.print()
    _rule(console, style="bright_cyan")


def print_status(console: Console, backend: str, package: str, download: str = "") -> None:
    pkg = package or "?"
    if len(pkg) > 36:
        pkg = "..." + pkg[-33:]
    parts = [f"[bright_cyan]{backend.upper()}[/]", f"[white]{pkg}[/]"]
    if download:
        parts.append(f"[dim]{download}[/]")
    console.print("  ".join(parts))
    _rule(console, style="dim")


def render_menu(console: Console) -> None:
    from rich.table import Table

    table = Table(
        show_header=True,
        header_style="bold bright_cyan",
        box=None,
        padding=(0, 1),
        collapse_padding=True,
    )
    table.add_column("#", style="cyan", justify="right", width=3)
    table.add_column("Menu", style="white")

    for key, label in _MENU:
        style = "bold red" if key == "0" else "cyan"
        table.add_row(f"[{style}]{key}[/]", label)

    console.print()
    console.print(table)


def print_goodbye(console: Console) -> None:
    console.print()
    _rule(console, style="dim")
    console.print(
        f"[bright_cyan]{APP_NAME}[/] [bold bright_magenta]by {AUTHOR}[/]"
        f"  [dim]- sampai jumpa.[/]\n"
    )
