"""Fast download via aria2c (multi-connection)."""

from __future__ import annotations

import logging
import shutil
import subprocess
import time
from pathlib import Path

from .progress import ProgressReporter

LOG = logging.getLogger(__name__)


def find_aria2(explicit: str | None = None) -> str | None:
    if explicit:
        return explicit if Path(explicit).exists() or shutil.which(explicit) else None
    return shutil.which("aria2c")


def download_with_aria2(
    url: str,
    dest: Path,
    *,
    user_agent: str,
    splits: int = 16,
    aria2_path: str | None = None,
    timeout: int = 600,
    reporter: ProgressReporter,
    total_hint: int = 0,
) -> None:
    binary = find_aria2(aria2_path)
    if not binary:
        raise FileNotFoundError("aria2c tidak ditemukan")

    dest.parent.mkdir(parents=True, exist_ok=True)
    if dest.exists():
        dest.unlink()

    splits = max(1, min(16, splits))
    cmd = [
        binary,
        f"-x{splits}",
        f"-s{splits}",
        "-k1M",
        "--file-allocation=none",
        "--allow-overwrite=true",
        "--auto-file-renaming=false",
        "--console-log-level=error",
        "--summary-interval=0",
        f"--user-agent={user_agent}",
        f"-d{dest.parent}",
        f"-o{dest.name}",
        url,
    ]

    reporter.on_step("Menghubungkan server...", 3, f"x{splits}")
    LOG.info("aria2: %s", " ".join(cmd[:8]))

    proc = subprocess.Popen(
        cmd,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.PIPE,
        text=True,
    )

    t0 = time.time()
    last_t = 0.0
    downloaded = 0

    while proc.poll() is None:
        now = time.time()
        if now - last_t >= 0.2:
            elapsed = now - t0
            if dest.exists():
                downloaded = dest.stat().st_size
                if downloaded > 0:
                    reporter.on_download(
                        downloaded,
                        total_hint,
                        downloaded / max(elapsed, 0.001),
                    )
                else:
                    reporter.on_step(
                        f"Menyiapkan download... {elapsed:.0f}s",
                        min(18, 6 + int(elapsed) % 12),
                        f"x{splits}",
                    )
            else:
                reporter.on_step(
                    f"Menghubungkan... {elapsed:.0f}s",
                    min(18, 6 + int(elapsed) % 12),
                    f"aria2 x{splits}",
                )
            last_t = now
        time.sleep(0.1)

    err = (proc.stderr.read() or "").strip() if proc.stderr else ""
    if proc.returncode != 0:
        dest.unlink(missing_ok=True)
        raise RuntimeError(err or f"aria2 exit {proc.returncode}")

    if not dest.is_file():
        raise RuntimeError("aria2 selesai tapi file tidak ada")

    downloaded = dest.stat().st_size
    elapsed = max(time.time() - t0, 0.001)
    reporter.on_download(downloaded, total_hint or downloaded, downloaded / elapsed)
