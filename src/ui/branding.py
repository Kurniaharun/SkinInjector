"""Branding — simple & clean."""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from rich.console import Console

VERSION = "1.8.0"

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
    ("10", "Refresh Index"),
    ("11", "Settings"),
    ("12", "Backup Official"),
    ("13", "Advanced — Batch Apply"),
    ("0", "Keluar"),
]


def _figlet(text: str) -> str | None:
    try:
        import pyfiglet

        return pyfiglet.figlet_format(text, font="small").rstrip("\n")
    except Exception:
        return None


def print_banner(console: Console) -> None:
    art = _figlet("SKIN INJ")
    if art:
        console.print(art, style="bold cyan")
    else:
        console.print("[bold cyan]SKIN INJECTOR[/]")
    console.print(f"[dim]v{VERSION}[/]\n")


def print_status(console: Console, backend: str, package: str, download: str = "") -> None:
    pkg = package or "?"
    if len(pkg) > 32:
        pkg = "..." + pkg[-29:]
    extra = f"  [dim]| {download}[/]" if download else ""
    console.print(f"[dim]{backend.upper()}[/]  [white]{pkg}[/]{extra}\n")


def render_menu(console: Console) -> None:
    console.print("[bold]Menu[/]")
    for key, label in _MENU:
        if key == "0":
            console.print()
        color = "red" if key == "0" else "cyan"
        console.print(f"  [{color}]{key:>2}[/]  {label}")


def print_goodbye(console: Console) -> None:
    console.print("\n[dim]Bye.[/]\n")
