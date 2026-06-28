#!/usr/bin/env python3
"""SkinJECT Web Server — by KurrXd (Python, default port 8080)."""

from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.web import run_server


def main() -> int:
    p = argparse.ArgumentParser(description="SkinJECT Web Server — by KurrXd")
    p.add_argument("--host", default="0.0.0.0", help="Bind address")
    default_port = int(os.environ.get("PORT", "8080"))
    p.add_argument(
        "--port",
        type=int,
        default=default_port,
        help="Port HTTP (default 8080, port 80 butuh root/admin)",
    )
    args = p.parse_args()
    run_server(host=args.host, port=args.port)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
