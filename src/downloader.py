"""Download skin ZIP — aria2 multi-connection + fast HTTP fallback."""

from __future__ import annotations

import logging
import time
from pathlib import Path
from typing import Optional
from urllib.parse import urlparse

import requests
from requests.adapters import HTTPAdapter
from tenacity import retry, stop_after_attempt, wait_exponential
from urllib3.util.retry import Retry

from .config import DOWNLOAD_DIR
from .download_aria import download_with_aria2, find_aria2
from .errors import DownloadError
from .progress import NullReporter, ProgressReporter

LOG = logging.getLogger(__name__)


class Downloader:
    def __init__(self, cfg: dict) -> None:
        self.cfg = cfg
        dl = cfg.get("download", {})
        self.chunk = int(dl.get("chunk_size", 262144))
        self.min_bytes = int(dl.get("min_zip_bytes", 1024))
        self.engine = str(dl.get("engine", "auto")).lower()
        self.aria_splits = int(dl.get("aria_splits", 16))
        self.aria_path = find_aria2(dl.get("aria2_path"))
        self.timeout = int(dl.get("timeout", 180))
        ua = cfg["api"].get("user_agent", "MLBB-Skin-Injector/1.0")
        self.session = requests.Session()
        self.session.headers.update({"User-Agent": ua})
        retry = Retry(total=2, backoff_factor=0.5, status_forcelist=(502, 503, 504))
        adapter = HTTPAdapter(pool_connections=8, pool_maxsize=8, max_retries=retry)
        self.session.mount("https://", adapter)
        self.session.mount("http://", adapter)

    def engine_label(self) -> str:
        if self._want_aria():
            return f"aria2 x{self.aria_splits}"
        return "http"

    def _want_aria(self) -> bool:
        if self.engine == "requests":
            return False
        if self.engine == "aria2":
            return self.aria_path is not None
        return self.aria_path is not None

    def _filename_from_url(self, url: str) -> str:
        name = Path(urlparse(url).path).name
        return name or self.cfg["inject"].get("temp_zip_name", "IMB.zip")

    def _head_size(self, url: str) -> int:
        try:
            r = self.session.head(url, timeout=20, allow_redirects=True)
            return int(r.headers.get("content-length", 0))
        except requests.RequestException:
            return 0

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=1, max=20),
        reraise=True,
    )
    def _fetch_http(self, url: str, dest: Path, reporter: ProgressReporter) -> None:
        LOG.info("HTTP download %s", url)
        reporter.on_step("Menghubungkan server...", 3, "http")
        total = self._head_size(url)
        with self.session.get(url, stream=True, timeout=self.timeout) as r:
            r.raise_for_status()
            if not total:
                total = int(r.headers.get("content-length", 0))
            reporter.on_download(0, total, 0)
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
                    if now - last_t >= 0.12 or (total and downloaded >= total):
                        speed = downloaded / max(now - t0, 0.001)
                        reporter.on_download(downloaded, total, speed)
                        last_t = now
            if total and downloaded < total:
                raise DownloadError(f"Tidak lengkap: {downloaded}/{total}")
        reporter.on_download(downloaded, total or downloaded, 0)

    def _fetch(self, url: str, dest: Path, reporter: ProgressReporter) -> None:
        if self._want_aria():
            try:
                total = self._head_size(url)
                download_with_aria2(
                    url,
                    dest,
                    user_agent=self.session.headers.get("User-Agent", ""),
                    splits=self.aria_splits,
                    aria2_path=self.aria_path or None,
                    timeout=self.timeout,
                    reporter=reporter,
                    total_hint=total,
                )
                return
            except Exception as e:
                LOG.warning("aria2 gagal (%s), fallback http", e)
                dest.unlink(missing_ok=True)
                reporter.on_step("Fallback HTTP...", 10, "")
        self._fetch_http(url, dest, reporter)

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
        dest.unlink(missing_ok=True)
        try:
            self._fetch(url, dest, rep)
        except Exception as e:
            dest.unlink(missing_ok=True)
            raise DownloadError(f"Gagal download: {e}") from e
        if dest.stat().st_size < self.min_bytes:
            dest.unlink(missing_ok=True)
            raise DownloadError("File terlalu kecil")
        LOG.info("Saved %s (%d bytes) via %s", dest, dest.stat().st_size, self.engine_label())
        return dest
