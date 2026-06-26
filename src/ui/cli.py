"""Interactive CLI menus."""

from __future__ import annotations

import sys
from typing import Callable, Optional

from rich.console import Console
from rich.panel import Panel
from rich.table import Table

from ..app import App
from ..errors import InjectorError
from ..models import SkinItem
from .progress_ui import RichInjectReporter

console = Console()


def _pause() -> None:
    try:
        input("\nTekan Enter untuk lanjut...")
    except (EOFError, KeyboardInterrupt):
        pass


def _pick(prompt: str, options: list[str]) -> Optional[int]:
    if not options:
        console.print("[red]Tidak ada pilihan.[/]")
        return None
    for i, opt in enumerate(options, 1):
        console.print(f"  [cyan][{i}][/] {opt}")
    console.print("  [dim][0] Kembali[/]")
    try:
        raw = input(f"\n{prompt}: ").strip()
        if raw == "0" or raw == "":
            return None
        idx = int(raw)
        if 1 <= idx <= len(options):
            return idx - 1
    except (ValueError, EOFError, KeyboardInterrupt):
        return None
    console.print("[red]Pilihan tidak valid.[/]")
    return None


def _pick_skin(skins: list[SkinItem], title: str) -> Optional[SkinItem]:
    if not skins:
        console.print("[yellow]Tidak ada skin.[/]")
        return None
    labels = [
        f"{s.skin_name} [{s.source}] — {s.hero_name}"
        for s in skins
    ]
    idx = _pick(title, labels)
    return skins[idx] if idx is not None else None


def _confirm(msg: str) -> bool:
    try:
        console.print()
        console.print(msg)
        ans = input("Lanjut inject? (y/N): ").strip().lower()
        return ans in ("y", "yes", "ya")
    except (EOFError, KeyboardInterrupt):
        return False


def _inject_flow(app: App, skin: SkinItem) -> None:
    if not _confirm(f"Inject [bold cyan]{skin.skin_name}[/] — [dim]{skin.hero_name}[/]"):
        return
    try:
        with RichInjectReporter(console, skin) as ui:
            app.inject_skin(skin, reporter=ui.reporter)
    except InjectorError as e:
        console.print(f"[red]Gagal: {e}[/]")


def menu_search(app: App) -> None:
    query = input("\nCari hero/skin: ").strip()
    if not query:
        return
    app.search.load()
    results = app.search.search(query)
    if not results:
        console.print("[yellow]Tidak ditemukan. Coba refresh index (menu 7).[/]")
        _pause()
        return
    skin = _pick_skin(results, "Pilih skin")
    if skin:
        _inject_flow(app, skin)
    _pause()


def menu_browse_heroes(app: App) -> None:
    app.search.load()
    heroes = app.search.heroes_unique()
    if len(heroes) > 80:
        console.print(f"[dim]Menampilkan 80 dari {len(heroes)} hero. Gunakan search untuk spesifik.[/]")
        heroes = heroes[:80]
    idx = _pick("Pilih hero", heroes)
    if idx is None:
        return
    hero = heroes[idx]
    skins = app.search.by_hero(hero)
    if not skins:
        try:
            skins = app.api.get_upgrade_skins(hero)
        except Exception as e:
            console.print(f"[red]{e}[/]")
            _pause()
            return
    skin = _pick_skin(skins, f"Skin untuk {hero}")
    if skin:
        _inject_flow(app, skin)
    _pause()


def menu_upgrade(app: App) -> None:
    try:
        menu = app.api.get_upgrade_menu()
    except Exception as e:
        console.print(f"[red]Gagal load menu: {e}[/]")
        _pause()
        return
    names = [str(x.get("heroName", x.get("name", "?"))) for x in menu]
    idx = _pick("Pilih hero (Upgrade)", names)
    if idx is None:
        return
    hero = names[idx]
    try:
        skins = app.api.get_upgrade_skins(hero)
    except Exception as e:
        console.print(f"[red]{e}[/]")
        _pause()
        return
    skin = _pick_skin(skins, f"Upgrade skin — {hero}")
    if skin:
        _inject_flow(app, skin)
    _pause()


def menu_custom(app: App) -> None:
    try:
        skins = app.api.get_custom_skins()
    except Exception as e:
        console.print(f"[red]{e}[/]")
        _pause()
        return
    skin = _pick_skin(skins, "Custom skin")
    if skin:
        _inject_flow(app, skin)
    _pause()


def menu_restore(app: App) -> None:
    backups = app.list_backups()
    if not backups:
        console.print("[yellow]Belum ada backup. Backup dibuat otomatis saat inject pertama.[/]")
        _pause()
        return
    labels = [
        f"{b.hero_name} (id={b.hero_id}) — {b.skin_name} @ {b.injected_at[:19]}"
        for b in backups
    ]
    labels.append(">>> Restore SEMUA backup")
    idx = _pick("Restore default skin", labels)
    if idx is None:
        return

    def _do_restore(hero_id: str, label: str) -> None:
        try:
            with RichInjectReporter(
                console,
                SkinItem(
                    id=hero_id,
                    hero_name=label,
                    skin_name="Default Restore",
                    image_url="",
                    download_url="",
                    source="restore",
                ),
            ) as ui:
                ui.on_step("Restore file asli...", 20, hero_id)
                msg = app.restore_default(hero_id, reporter=ui.reporter)
                ui.finish(True, msg)
        except InjectorError as e:
            console.print(f"[red]{label}: {e}[/]")

    if idx == len(backups):
        for b in backups:
            _do_restore(b.hero_id, b.hero_name)
    else:
        b = backups[idx]
        _do_restore(b.hero_id, b.hero_name)
    _pause()


def menu_status(app: App) -> None:
    pf = app.init()
    table = Table(title="Status")
    table.add_column("Item")
    table.add_column("Nilai")
    table.add_row("Mode config", pf.mode)
    table.add_row("Backend", pf.backend_name)
    table.add_row("Package", pf.package or "-")
    table.add_row("Assets", pf.assets_path or "-")
    table.add_row("OK", "Ya" if pf.ok else "Tidak")
    console.print(table)
    for m in pf.messages:
        console.print(m)
    backups = app.list_backups()
    console.print(f"\n[bold]Backup tersimpan:[/] {len(backups)}")
    for b in backups[:10]:
        console.print(f"  - {b.hero_name} / {b.skin_name} ({len(b.files)} file)")
    _pause()


def menu_settings(app: App) -> None:
    opts = ["Auto (deteksi root → shizuku → direct)", "Root only", "No-root (Shizuku/direct)"]
    idx = _pick("Access mode", opts)
    if idx is None:
        return
    modes = ["auto", "root", "noroot"]
    app.mode_override = modes[idx]
    app.cfg.setdefault("access", {})["mode"] = modes[idx]
    pf = app.init()
    console.print(f"[green]Mode: {pf.backend_name}[/]")
    for m in pf.messages:
        console.print(m)
    _pause()


def run_interactive(app: App) -> None:
    pf = app.init()
    console.print(
        Panel(
            "[bold cyan]MLBB Skin Injector[/] v1.0\n"
            f"Backend: [green]{pf.backend_name}[/] | Package: {pf.package or 'N/A'}",
            title="Termux",
        )
    )
    if not pf.ok and sys.platform != "win32":
        console.print("[yellow]Beberapa cek gagal — fitur inject mungkin terbatas.[/]")

    actions: dict[str, Callable[[App], None]] = {
        "1": menu_browse_heroes,
        "2": menu_search,
        "3": menu_upgrade,
        "4": menu_custom,
        "5": menu_restore,
        "6": menu_status,
        "7": lambda a: (console.print(f"[green]{a.refresh_all()}[/]"), _pause()),
        "8": menu_settings,
    }

    while True:
        console.print(
            "\n[bold]Menu[/]\n"
            "  [1] Browse Hero\n"
            "  [2] Search Skin\n"
            "  [3] Upgrade Skins\n"
            "  [4] Custom Skins\n"
            "  [5] Restore Default Skin\n"
            "  [6] Status & Backup\n"
            "  [7] Refresh cache/index\n"
            "  [8] Settings (root / no-root)\n"
            "  [0] Keluar"
        )
        try:
            choice = input("\nPilih: ").strip()
        except (EOFError, KeyboardInterrupt):
            break
        if choice == "0":
            break
        fn = actions.get(choice)
        if fn:
            try:
                fn(app)
            except KeyboardInterrupt:
                console.print("\n[dim]Dibatalkan.[/]")
            except Exception as e:
                console.print(f"[red]Error: {e}[/]")
                _pause()
        else:
            console.print("[red]Pilihan tidak valid[/]")

    console.print("[dim]Sampai jumpa.[/]")
