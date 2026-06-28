#!/usr/bin/env python3
"""SkinJECT — matikan web server di semua port terdeteksi."""

from __future__ import annotations

import argparse
import os
import re
import signal
import subprocess
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent

# Port default SkinJECT (server.py / main.py web)
DEFAULT_PORTS = (80, 8080, 8765)


def _ports_to_scan(extra: list[int]) -> list[int]:
    ports: set[int] = set(DEFAULT_PORTS)
    env_port = os.environ.get("PORT", "").strip()
    if env_port.isdigit():
        ports.add(int(env_port))
    ports.update(extra)
    return sorted(ports)


def _pids_on_port_windows(port: int) -> set[int]:
    pids: set[int] = set()
    try:
        out = subprocess.check_output(
            ["netstat", "-ano", "-p", "TCP"],
            text=True,
            errors="replace",
            creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
        )
    except (subprocess.CalledProcessError, FileNotFoundError):
        return pids
    suffix = f":{port}"
    for line in out.splitlines():
        if "LISTENING" not in line.upper():
            continue
        parts = line.split()
        if len(parts) < 5:
            continue
        local = parts[1]
        if local.endswith(suffix) or local.rsplit(":", 1)[-1] == str(port):
            try:
                pid = int(parts[-1])
                if pid > 0:
                    pids.add(pid)
            except ValueError:
                pass
    return pids


def _pids_on_port_unix(port: int) -> set[int]:
    pids: set[int] = set()

    # ss (Linux / Termux)
    try:
        out = subprocess.check_output(
            ["ss", "-H", "-tlnp", f"sport = :{port}"],
            text=True,
            errors="replace",
            stderr=subprocess.DEVNULL,
        )
        for line in out.splitlines():
            m = re.search(r"pid=(\d+)", line)
            if m:
                pids.add(int(m.group(1)))
        if pids:
            return pids
    except (subprocess.CalledProcessError, FileNotFoundError):
        pass

    # lsof fallback
    try:
        out = subprocess.check_output(
            ["lsof", "-ti", f":{port}"],
            text=True,
            errors="replace",
            stderr=subprocess.DEVNULL,
        )
        for tok in out.split():
            if tok.isdigit():
                pids.add(int(tok))
        if pids:
            return pids
    except (subprocess.CalledProcessError, FileNotFoundError):
        pass

    # fuser fallback
    try:
        out = subprocess.check_output(
            ["fuser", f"{port}/tcp"],
            text=True,
            errors="replace",
            stderr=subprocess.STDOUT,
        )
        for tok in out.split():
            if tok.isdigit():
                pids.add(int(tok))
    except (subprocess.CalledProcessError, FileNotFoundError):
        pass

    return pids


def pids_on_port(port: int) -> set[int]:
    if sys.platform == "win32":
        return _pids_on_port_windows(port)
    return _pids_on_port_unix(port)


def _cmdline_windows(pid: int) -> str:
    try:
        out = subprocess.check_output(
            [
                "wmic",
                "process",
                "where",
                f"ProcessId={pid}",
                "get",
                "CommandLine",
                "/value",
            ],
            text=True,
            errors="replace",
            creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
        )
        for line in out.splitlines():
            if line.startswith("CommandLine="):
                return line.split("=", 1)[1].strip()
    except (subprocess.CalledProcessError, FileNotFoundError):
        pass
    return ""


def _cmdline_unix(pid: int) -> str:
    try:
        raw = Path(f"/proc/{pid}/cmdline").read_bytes()
        return raw.replace(b"\0", b" ").decode("utf-8", errors="replace").strip()
    except OSError:
        return ""


def process_cmdline(pid: int) -> str:
    if sys.platform == "win32":
        return _cmdline_windows(pid)
    return _cmdline_unix(pid)


def is_skinject_server(pid: int) -> bool:
    cmd = process_cmdline(pid).lower()
    if not cmd:
        return True  # netstat match tanpa cmdline — tetap kill (port target)
    markers = (
        "server.py",
        "main.py",
        "skinject",
        "injectskin",
        str(ROOT).lower(),
        "src.web",
        "run_server",
    )
    if "python" in cmd or "python3" in cmd:
        return any(m in cmd for m in markers)
    return False


def scan_listeners(extra_ports: list[int], *, any_process: bool = False) -> dict[int, set[int]]:
    found: dict[int, set[int]] = {}
    for port in _ports_to_scan(extra_ports):
        for pid in pids_on_port(port):
            if any_process or is_skinject_server(pid):
                found.setdefault(pid, set()).add(port)
    return found


def kill_pid(pid: int, force: bool = False) -> bool:
    if pid == os.getpid():
        return False
    try:
        if sys.platform == "win32":
            args = ["taskkill", "/PID", str(pid)]
            if force:
                args.append("/F")
            subprocess.check_call(
                args,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
            )
        else:
            sig = signal.SIGKILL if force else signal.SIGTERM
            os.kill(pid, sig)
        return True
    except (OSError, subprocess.CalledProcessError):
        return False


def main() -> int:
    p = argparse.ArgumentParser(description="SkinJECT — matikan web server (semua port)")
    p.add_argument(
        "--port",
        type=int,
        action="append",
        default=[],
        dest="ports",
        help="Port tambahan (bisa diulang)",
    )
    p.add_argument(
        "--all-ports",
        action="store_true",
        help="Matikan semua proses di port scan (bukan cuma SkinJECT)",
    )
    p.add_argument(
        "--force",
        "-f",
        action="store_true",
        help="Paksa kill (SIGKILL / taskkill /F)",
    )
    p.add_argument(
        "--dry-run",
        "-n",
        action="store_true",
        help="Hanya tampilkan, jangan kill",
    )
    args = p.parse_args()

    extra = list(args.ports)
    if not args.all_ports and not extra:
        extra = []  # tetap pakai DEFAULT_PORTS via _ports_to_scan

    targets = scan_listeners(extra, any_process=args.all_ports)
    ports_scanned = _ports_to_scan(extra)

    print("")
    print("  SkinJECT killserver")
    print(f"  Scan port: {', '.join(map(str, ports_scanned))}")
    print("")

    if not targets:
        print("  Tidak ada server SkinJECT yang berjalan.")
        print("")
        return 0

    for pid in sorted(targets):
        ports = ", ".join(map(str, sorted(targets[pid])))
        cmd = process_cmdline(pid) or "(unknown)"
        if len(cmd) > 72:
            cmd = cmd[:69] + "..."
        print(f"  PID {pid}  port [{ports}]")
        print(f"         {cmd}")

    if args.dry_run:
        print("")
        print("  Dry-run — tidak ada proses dimatikan.")
        print("")
        return 0

    killed = 0
    for pid in sorted(targets):
        if kill_pid(pid, force=args.force):
            killed += 1
            print(f"  OK Matikan PID {pid}")
        else:
            print(f"  X Gagal matikan PID {pid}")

    if not args.force and killed:
        time.sleep(0.4)
        still = scan_listeners(extra, any_process=args.all_ports)
        for pid in still:
            if kill_pid(pid, force=True):
                print(f"  OK Force kill PID {pid}")

    print("")
    remaining = scan_listeners(extra, any_process=args.all_ports)
    if remaining:
        print(f"  Masih aktif: {len(remaining)} proses (coba --force atau jalankan sebagai admin)")
        print("")
        return 1

    print("  Semua server SkinJECT sudah dimatikan.")
    print("")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
