"""Filesystem and shell helpers."""

from __future__ import annotations

import logging
import os
import platform
import re
import shutil
import subprocess
import zipfile
from pathlib import Path
from typing import Optional

from .errors import ZipInvalidError

LOG = logging.getLogger(__name__)

DANGEROUS_ZIP = re.compile(r"(^|/)\.\.(/|$)")


def setup_logging(log_dir: Path, quiet_console: bool = False) -> None:
    log_dir.mkdir(parents=True, exist_ok=True)
    log_file = log_dir / "injector.log"
    handlers: list[logging.Handler] = [logging.FileHandler(log_file, encoding="utf-8")]
    if not quiet_console:
        handlers.append(logging.StreamHandler())
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        handlers=handlers,
        force=True,
    )


def is_android() -> bool:
    return "android" in platform.system().lower() or Path("/system/bin/sh").exists()


def has_root() -> bool:
    if os.name == "nt":
        return False
    for cmd in (
        ["su", "-c", "id"],
        ["su", "0", "id"],
    ):
        try:
            r = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=10,
            )
            if r.returncode == 0 and "uid=0" in (r.stdout + r.stderr):
                return True
        except (FileNotFoundError, subprocess.TimeoutExpired, OSError):
            continue
    return False


def has_shizuku() -> bool:
    if os.name == "nt":
        return False
    if shutil.which("shizuku"):
        return True
    if shutil.which("rish"):
        return True
    if os.environ.get("RISH_SERVER"):
        return True
    try:
        r = subprocess.run(
            ["shizuku", "ping"],
            capture_output=True,
            text=True,
            timeout=8,
        )
        return r.returncode == 0
    except (FileNotFoundError, subprocess.TimeoutExpired, OSError):
        return False


def android_sdk_int() -> int:
    try:
        r = subprocess.run(
            ["getprop", "ro.build.version.sdk"],
            capture_output=True,
            text=True,
            timeout=5,
        )
        if r.returncode == 0 and r.stdout.strip().isdigit():
            return int(r.stdout.strip())
    except (FileNotFoundError, subprocess.TimeoutExpired, OSError):
        pass
    return 30


def free_bytes(path: str) -> int:
    try:
        st = os.statvfs(path) if hasattr(os, "statvfs") else None
        if st:
            return st.f_bavail * st.f_frsize
    except OSError:
        pass
    try:
        usage = shutil.disk_usage(path)
        return usage.free
    except OSError:
        return 0


def list_zip_members(zip_path: Path) -> list[str]:
    with zipfile.ZipFile(zip_path, "r") as zf:
        return [i.filename for i in zf.infolist() if not i.is_dir()]


def validate_skin_zip(zip_path: Path, min_bytes: int = 1024) -> list[str]:
    if not zip_path.is_file():
        raise ZipInvalidError(f"File tidak ada: {zip_path}")
    if zip_path.stat().st_size < min_bytes:
        raise ZipInvalidError("ZIP terlalu kecil / corrupt")
    try:
        with zipfile.ZipFile(zip_path, "r") as zf:
            if zf.testzip() is not None:
                raise ZipInvalidError("ZIP gagal integrity test")
            members = [i.filename for i in zf.infolist() if not i.is_dir()]
    except zipfile.BadZipFile as e:
        raise ZipInvalidError(f"Bukan file ZIP valid: {e}") from e
    if not members:
        raise ZipInvalidError("ZIP kosong")
    for m in members:
        if DANGEROUS_ZIP.search(m):
            raise ZipInvalidError(f"Path traversal terdeteksi: {m}")
    return members


def python_unzip(zip_path: Path, target_dir: Path) -> bool:
    target_dir.mkdir(parents=True, exist_ok=True)
    try:
        with zipfile.ZipFile(zip_path, "r") as zf:
            for info in zf.infolist():
                if info.is_dir():
                    continue
                name = info.filename
                if DANGEROUS_ZIP.search(name):
                    continue
                dest = target_dir / name
                dest.parent.mkdir(parents=True, exist_ok=True)
                with zf.open(info) as src, open(dest, "wb") as out:
                    shutil.copyfileobj(src, out)
        return True
    except OSError as e:
        LOG.error("python_unzip gagal: %s", e)
        return False


def run_shell(cmd: str, timeout: int = 120) -> tuple[int, str, str]:
    LOG.debug("shell: %s", cmd)
    try:
        r = subprocess.run(
            cmd,
            shell=True,
            capture_output=True,
            text=True,
            timeout=timeout,
        )
        return r.returncode, r.stdout or "", r.stderr or ""
    except subprocess.TimeoutExpired:
        return -1, "", "timeout"
    except OSError as e:
        return -1, "", str(e)


def pkg_installed(package: str) -> bool:
    if os.name == "nt":
        return False
    for cmd in (
        f"pm path {package}",
        f"su -c 'pm path {package}'",
    ):
        code, out, _ = run_shell(cmd, timeout=15)
        if code == 0 and "package:" in out:
            return True
    return False
