"""Download skin ZIP with retry and progress."""

from __future__ import annotations

import logging
import time
from pathlib import Path
from typing import TYPE_CHECKING, Optional
from urllib.parse import urlparse

import requests
from tenacity import retry, stop_after_attempt, wait_exponential

from .config import DOWNLOAD_DIR
from .errors import DownloadError
from .progress import NullReporter, ProgressReporter

if TYPE_CHECKING:
    pass

LOG = logging.getLogger(__name__)


class Downloader:
    def __init__(self, cfg: dict) -> None:
        self.cfg = cfg
        dl = cfg.get("download", {})
        self.chunk = int(dl.get("chunk_size", 8192))
        self.min_bytes = int(dl.get("min_zip_bytes", 1024))
        self.session = requests.Session()
        self.session.headers.update(
            {"User-Agent": cfg["api"].get("user_agent", "MLBB-Skin-Injector/1.0")}
        )

    def _filename_from_url(self, url: str) -> str:
        name = Path(urlparse(url).path).name
        return name or self.cfg["inject"].get("temp_zip_name", "IMB.zip")

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=30),
        reraise=True,
    )
    def _fetch(
        self,
        url: str,
        dest: Path,
        reporter: ProgressReporter,
    ) -> None:
        LOG.info("Downloading %s", url)
        reporter.on_step("Menghubungkan server...", 6, url[:50])
        with self.session.get(url, stream=True, timeout=120) as r:
            r.raise_for_status()
            total = int(r.headers.get("content-length", 0))
            downloaded = 0
            dest.parent.mkdir(parents=True, exist_ok=True)
            t0 = time.time()
            last_t = t0
            with open(dest, "wb") as f:
                for chunk in r.iter_content(chunk_size=self.chunk):
                    if not chunk:
                        continue
                    f.write(chunk)
                    downloaded += len(chunk)
                    now = time.time()
                    if now - last_t >= 0.05 or downloaded == total:
                        elapsed = max(now - t0, 0.001)
                        speed = downloaded / elapsed
                        reporter.on_download(downloaded, total, speed)
                        last_t = now
            if total and downloaded < total:
                raise DownloadError(f"Download tidak lengkap: {downloaded}/{total}")
        reporter.on_download(downloaded, downloaded or total or 1, 0)

    def download(
        self,
        url: str,
        filename: str | None = None,
        reporter: Optional[ProgressReporter] = None,
    ) -> Path:
        rep = reporter or NullReporter()
        if not url or not url.startswith("http"):
            raise DownloadError(f"URL tidak valid: {url}")
        fname = filename or self._filename_from_url(url)
        dest = DOWNLOAD_DIR / fname
        if dest.exists():
            dest.unlink()
        try:
            self._fetch(url, dest, rep)
        except Exception as e:
            dest.unlink(missing_ok=True)
            raise DownloadError(f"Gagal download: {e}") from e
        if dest.stat().st_size < self.min_bytes:
            dest.unlink(missing_ok=True)
            raise DownloadError("File terlalu kecil setelah download")
        LOG.info("Saved %s (%d bytes)", dest, dest.stat().st_size)
        return dest
