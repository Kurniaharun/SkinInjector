"""Shared Rich styles."""

import sys

ACCENT = "cyan"
ACCENT_BRIGHT = "bright_cyan"
SUCCESS = "bright_green"
WARNING = "yellow"
ERROR = "bright_red"
MUTED = "dim"
TITLE = "bold white"
HIGHLIGHT = "bold magenta"

PROMPT = "bold bright_magenta"
PROMPT_SYMBOL = ">" if sys.platform == "win32" else "❯"
DIVIDER_CHAR = "-" if sys.platform == "win32" else "─"

