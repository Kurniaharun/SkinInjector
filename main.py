#!/usr/bin/env python3
"""
MLBB Skin Injector — Termux Python
Dual mode: root / no-root (Shizuku)
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.app import App
from src.errors import InjectorError
from src.progress import ConsoleReporter
from src.ui.branding import print_banner, VERSION
from src.ui.cli import run_interactive
from src.ui.console import make_console


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        description="MLBB Skin Injector — inject & restore default skin",
    )
    p.add_argument(
        "--mode",
        choices=["auto", "root", "noroot"],
        default=None,
        help="Akses storage: auto | root | noroot",
    )
    sub = p.add_subparsers(dest="command")

    sub.add_parser("menu", help="Menu interaktif (default)")

    sp = sub.add_parser("status", help="Cek status")
    sp = sub.add_parser("refresh", help="Refresh API cache & search index")

    sp = sub.add_parser("search", help="Cari skin")
    sp.add_argument("query", help="Kata kunci")

    sp = sub.add_parser("inject", help="Inject skin")
    sp.add_argument("--hero", required=True)
    sp.add_argument("--skin", required=True)
    sp.add_argument("--dry-run", action="store_true")

    sp = sub.add_parser("restore", help="Restore default skin")
    sp.add_argument("--hero-id", help="ID hero dari backup")
    sp.add_argument("--all", action="store_true", dest="restore_all")

    return p


def cmd_status(app: App) -> int:
    con = make_console()
    print_banner(con)
    pf = app.init()
    for m in pf.messages:
        con.print(m)
    return 0 if pf.ok else 1


def cmd_search(app: App, query: str) -> int:
    app.init()
    app.search.ensure_for_search()
    for s in app.search.search(query):
        print(f"{s.hero_name} | {s.skin_name} | [{s.source}] | {s.download_url}")
    return 0


def cmd_inject(app: App, hero: str, skin: str, dry_run: bool) -> int:
    app.init()
    app.search.ensure_for_search()
    results = app.search.search(f"{hero} {skin}")
    if not results:
        results = [x for x in app.search.by_hero(hero) if skin.lower() in x.skin_name.lower()]
    if not results:
        print(f"Tidak ditemukan: {hero} / {skin}", file=sys.stderr)
        return 1
    target = results[0]
    rep = ConsoleReporter()
    try:
        print(f"\n=== INJECT: {target.hero_name} / {target.skin_name} ===")
        print(f"URL: {target.download_url}\n")
        print(app.inject_skin(target, dry_run=dry_run, reporter=rep))
        return 0
    except InjectorError as e:
        print(f"Gagal: {e}", file=sys.stderr)
        return 1


def cmd_restore(app: App, hero_id: str | None, restore_all: bool) -> int:
    app.init()
    backups = app.list_backups()
    if not backups:
        print("Tidak ada backup", file=sys.stderr)
        return 1
    if restore_all:
        for b in backups:
            try:
                print(f"{b.hero_name}: {app.restore_default(b.hero_id)}")
            except InjectorError as e:
                print(f"{b.hero_name}: {e}", file=sys.stderr)
        return 0
    if not hero_id:
        print("Pakai --hero-id atau --all", file=sys.stderr)
        return 1
    try:
        print(app.restore_default(hero_id))
        return 0
    except InjectorError as e:
        print(f"Gagal: {e}", file=sys.stderr)
        return 1


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()
    app = App(mode=args.mode)

    cmd = args.command
    if cmd is None or cmd == "menu":
        run_interactive(app)
        return 0
    if cmd == "status":
        return cmd_status(app)
    if cmd == "refresh":
        app.init()
        print(app.refresh_all())
        return 0
    if cmd == "search":
        return cmd_search(app, args.query)
    if cmd == "inject":
        return cmd_inject(app, args.hero, args.skin, args.dry_run)
    if cmd == "restore":
        return cmd_restore(app, args.hero_id, args.restore_all)
    parser.print_help()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
