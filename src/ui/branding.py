"""Branding — simple & clean."""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from rich.console import Console

VERSION = "1.5.1"

_MENU: list[tuple[str, str]] = [
    ("1", "Browse Hero"),
    ("2", "Search Skin"),
    ("3", "Upgrade Skins"),
    ("4", "Custom Skins"),
    ("5", "Restore Default"),
    ("6", "Status"),
    ("7", "Refresh Index"),
    ("8", "Settings"),
    ("9", "Effects & Recall"),
    ("10", "Backup Official"),
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


def print_status(console: Console, backend: str, package: str) -> None:
    pkg = package or "?"
    if len(pkg) > 36:
        pkg = "..." + pkg[-33:]
    console.print(f"[dim]{backend.upper()}[/]  [white]{pkg}[/]\n")


def render_menu(console: Console) -> None:
    console.print("[bold]Menu[/]")
    for key, label in _MENU:
        if key == "0":
            console.print()
        color = "red" if key == "0" else "cyan"
        console.print(f"  [{color}]{key:>2}[/]  {label}")


def print_goodbye(console: Console) -> None:
    console.print("\n[dim]Bye.[/]\n")
