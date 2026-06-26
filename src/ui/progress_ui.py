"""Rich progress bar UI for inject + download."""

from __future__ import annotations

import time
from typing import Optional

from rich.console import Console
from rich.progress import (
    BarColumn,
    Progress,
    SpinnerColumn,
    TaskProgressColumn,
    TextColumn,
)

from ..models import SkinItem
from ..progress import ProgressReporter


def _fmt_bytes(n: int) -> str:
    if n < 1024:
        return f"{n} B"
    if n < 1024 * 1024:
        return f"{n / 1024:.1f} KB"
    return f"{n / (1024 * 1024):.2f} MB"


class RichInjectReporter:
    """Context manager: spinner + bar 0-100% + download sub-bar."""

    def __init__(self, console: Console, skin: SkinItem) -> None:
        self.console = console
        self.skin = skin
        self._progress: Optional[Progress] = None
        self._main_id: Optional[int] = None
        self._dl_id: Optional[int] = None
        self._dl_base_pct = 5
        self._dl_span = 50
        self._last_dl_log = 0.0
        self.reporter: ProgressReporter = self

    def __enter__(self) -> RichInjectReporter:
        label = self.skin.label()
        if self.skin.source == "restore":
            self.console.print(f"\n[bold yellow]Restore[/] {label}\n")
        else:
            self.console.print(f"\n[bold cyan]Inject[/] {label}\n")
        self._progress = Progress(
            SpinnerColumn("dots", style="cyan"),
            TextColumn("{task.description}"),
            BarColumn(bar_width=32, complete_style="green"),
            TaskProgressColumn(),
            TextColumn("[dim]{task.fields[detail]}"),
            console=self.console,
            transient=False,
        )
        self._progress.start()
        self._main_id = self._progress.add_task(
            "Menyiapkan...",
            total=100,
            detail="",
        )
        self._dl_id = self._progress.add_task(
            "[green]Download ZIP[/]",
            total=100,
            visible=False,
            detail="",
        )
        return self

    def __exit__(self, *args) -> None:
        if self._progress:
            self._progress.stop()

    def on_step(self, step: str, percent: int, detail: str = "") -> None:
        if not self._progress or self._main_id is None:
            return
        pct = min(100, max(0, percent))
        self._progress.update(
            self._main_id,
            completed=pct,
            description=step,
            detail=detail,
        )
        if "download" not in step.lower() and self._dl_id is not None:
            self._progress.update(self._dl_id, visible=False)

    def on_download(self, downloaded: int, total: int, speed_bps: float = 0) -> None:
        if not self._progress or self._main_id is None or self._dl_id is None:
            return
        self._progress.update(self._dl_id, visible=True)
        if total > 0:
            ratio = min(1.0, downloaded / total)
            main_pct = self._dl_base_pct + int(ratio * self._dl_span)
            if downloaded == 0:
                main_pct = max(main_pct, 8)
            self._progress.update(
                self._main_id,
                completed=main_pct,
                description="[cyan]Downloading skin ZIP...[/]",
                detail=f"{_fmt_bytes(downloaded)} / {_fmt_bytes(total)}",
            )
            self._progress.update(
                self._dl_id,
                completed=int(ratio * 100),
                total=100,
                description=f"[green]Download {_fmt_bytes(downloaded)}/{_fmt_bytes(total)}[/]",
                detail=f"{speed_bps / (1024*1024):.1f} MB/s" if speed_bps > 0 else "menghubungkan",
            )
        else:
            now = time.time()
            if now - self._last_dl_log > 0.2:
                self._last_dl_log = now
                pulse = 10 + int(now * 3) % 20
                if downloaded > 0:
                    pulse = min(52, 25 + int(downloaded / 65536) % 25)
                self._progress.update(
                    self._main_id,
                    completed=pulse,
                    description="[cyan]Downloading...[/]",
                    detail=_fmt_bytes(downloaded) if downloaded else "menunggu data",
                )
                self._progress.update(
                    self._dl_id,
                    completed=None,
                    total=None,
                    description=(
                        f"[green]Downloaded {_fmt_bytes(downloaded)}[/]"
                        if downloaded
                        else "[green]Menunggu server...[/]"
                    ),
                )

    def on_backup_file(self, current: int, total: int, filename: str) -> None:
        if not self._progress or self._main_id is None:
            return
        base = 65
        span = 15
        pct = base + (int(current * span / total) if total else 0)
        short = filename
        self._progress.update(
            self._main_id,
            completed=pct,
            description="[yellow]Backup skin default...[/]",
            detail=f"{current}/{total} {short}",
        )

    def finish(self, success: bool, message: str) -> None:
        if not self._progress or self._main_id is None:
            return
        if self._dl_id is not None:
            self._progress.update(self._dl_id, visible=False)
        if success:
            self._progress.update(
                self._main_id,
                completed=100,
                description="[bold green]Selesai![/]",
                detail=message,
            )
            self.console.print(f"\n[green]OK[/] {message}")
        else:
            self._progress.update(
                self._main_id,
                completed=100,
                description="[bold red]Gagal[/]",
                detail=message,
            )
            self.console.print(f"\n[red]Gagal[/] {message}")
