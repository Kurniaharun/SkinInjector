#!/usr/bin/env python3
"""SkinJECT Web Server — by KurrXd (Python, port 80)."""

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
    p.add_argument("--port", type=int, default=int(os.environ.get("PORT", "80")), help="Port (default 80)")
    args = p.parse_args()
    run_server(host=args.host, port=args.port)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
