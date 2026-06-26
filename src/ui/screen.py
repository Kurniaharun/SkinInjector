"""Clear screen and busy spinner helpers."""

from __future__ import annotations

import os
import sys
from contextlib import contextmanager
from typing import Callable, Iterator, TypeVar

from rich.console import Console

T = TypeVar("T")


def clear_screen() -> None:
    """Clear terminal — Termux, Linux, Windows."""
    if sys.platform == "win32":
        os.system("cls")
    else:
        if os.environ.get("TERM"):
            sys.stdout.write("\033c")
            sys.stdout.flush()
        else:
            os.system("clear 2>/dev/null")


@contextmanager
def busy(console: Console, message: str) -> Iterator[None]:
    """Tampilkan spinner saat operasi lambat."""
    with console.status(f"[bold cyan]{message}[/]", spinner="dots"):
        yield


def run_busy(console: Console, message: str, fn: Callable[[], T]) -> T:
    with busy(console, message):
        return fn()
