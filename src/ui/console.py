"""Terminal-aware Rich console for Termux."""

from __future__ import annotations

import shutil

from rich.console import Console


def make_console() -> Console:
    cols, _rows = shutil.get_terminal_size(fallback=(100, 40))
    # Termux kadang lapor lebar sempit — jangan potong teks paksa
    width = None if cols < 50 else min(cols, 140)
    return Console(
        width=width,
        soft_wrap=True,
        highlight=False,
        emoji=False,
    )
