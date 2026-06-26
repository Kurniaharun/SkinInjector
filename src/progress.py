"""Progress reporting for inject pipeline."""

from __future__ import annotations

from typing import Optional, Protocol


class ProgressReporter(Protocol):
    def on_step(self, step: str, percent: int, detail: str = "") -> None: ...
    def on_download(self, downloaded: int, total: int, speed_bps: float = 0) -> None: ...
    def on_backup_file(self, current: int, total: int, filename: str) -> None: ...
    def finish(self, success: bool, message: str) -> None: ...


class NullReporter:
    """No-op reporter for CLI non-interactive mode."""

    def on_step(self, step: str, percent: int, detail: str = "") -> None:
        pass

    def on_download(self, downloaded: int, total: int, speed_bps: float = 0) -> None:
        pass

    def on_backup_file(self, current: int, total: int, filename: str) -> None:
        pass

    def finish(self, success: bool, message: str) -> None:
        pass


class ConsoleReporter:
    """Simple text progress for non-rich environments."""

    def __init__(self) -> None:
        self._last_pct = -1

    def on_step(self, step: str, percent: int, detail: str = "") -> None:
        if percent != self._last_pct:
            self._last_pct = percent
            line = f"[{percent:3d}%] {step}"
            if detail:
                line += f" — {detail}"
            print(line, flush=True)

    def on_download(self, downloaded: int, total: int, speed_bps: float = 0) -> None:
        if total > 0:
            pct = int(downloaded * 50 / total) + 5
            mb = downloaded / (1024 * 1024)
            tmb = total / (1024 * 1024)
            print(f"[{pct:3d}%] Download {mb:.1f}/{tmb:.1f} MB", flush=True)

    def on_backup_file(self, current: int, total: int, filename: str) -> None:
        print(f"[backup] {current}/{total} {filename}", flush=True)

    def finish(self, success: bool, message: str) -> None:
        tag = "OK" if success else "FAIL"
        print(f"[{tag}] {message}", flush=True)
