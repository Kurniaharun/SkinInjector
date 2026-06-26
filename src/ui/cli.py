"""Interactive CLI menus — responsive, paginated, searchable."""

from __future__ import annotations

import logging
import sys
from typing import Any, Callable, Optional

from rich.console import Console
from rich.panel import Panel
from rich.progress import BarColumn, Progress, SpinnerColumn, TaskProgressColumn, TextColumn
from rich.table import Table

from ..app import App
from ..errors import InjectorError
from ..models import SkinItem
from .picker import pick_from_list, pick_skin_labels
from .progress_ui import RichInjectReporter
from .screen import busy, clear_screen, run_busy

console = Console()
LOG = logging.getLogger(__name__)


def _pause() -> None:
    try:
        input("\n[dim]Enter = kembali ke menu[/]")
    except (EOFError, KeyboardInterrupt):
        pass


def _confirm(msg: str, prompt: str = "Lanjut inject? (y/N): ") -> bool:
    try:
        console.print()
        console.print(msg)
        ans = input(prompt).strip().lower()
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


def _render_header(app: App) -> None:
    pf = app.preflight
    backend = pf.backend_name if pf else "?"
    package = pf.package if pf else "N/A"
    try:
        n_heroes = len(app.api.list_hero_names())
    except Exception:
        n_heroes = "?"
    index_n = app.search.count if app.search._loaded else "—"
    console.print(
        Panel(
            f"[bold cyan]MLBB Skin Injector[/] v1.2\n"
            f"Backend: [green]{backend}[/] | MLBB: [yellow]{package}[/]\n"
            f"Hero: [white]{n_heroes}[/] | Index search: [dim]{index_n}[/]",
            title="SkinInjector",
            border_style="cyan",
        )
    )


def _render_menu() -> None:
    console.print(
        "[bold]Menu[/]\n"
        "  [1] Browse Hero        [cyan]~100 hero, paginated + [S] cari[/]\n"
        "  [2] Search Skin        [cyan]ketik nama, langsung cari[/]\n"
        "  [3] Upgrade Skins      [cyan]324 skin upgrade, paginated[/]\n"
        "  [4] Custom Skins\n"
        "  [5] Restore Default\n"
        "  [6] Status & Backup\n"
        "  [7] Refresh index      [dim](opsional, untuk search offline)[/]\n"
        "  [8] Settings\n"
        "  [0] Keluar"
    )


def _pick_skin(skins: list[SkinItem], title: str) -> Optional[SkinItem]:
    if not skins:
        console.print("[yellow]Tidak ada skin untuk hero ini.[/]")
        return None
    labels = [f"{s.skin_name}" for s in skins]
    idx = pick_skin_labels(console, labels, title)
    return skins[idx] if idx is not None else None


def menu_search(app: App) -> None:
    console.print("\n[bold]Search Skin[/]")
    console.print("[dim]Contoh: layla, gusion, dyrroth venom[/]")
    try:
        query = input("\nKetik nama: ").strip()
    except (EOFError, KeyboardInterrupt):
        return
    if not query:
        return

    results: list[SkinItem] = []

    # 1) Cari di hero groups (cepat, 1 API cache)
    try:
        hero_hits = app.api.search_hero_names(query)
        for hero in hero_hits[:8]:
            results.extend(app.api.get_skins_for_hero(hero))
    except Exception as e:
        LOG.warning("hero search: %s", e)

    # 2) Cari di upgrade list
    try:
        for entry in app.api.search_upgrade_entries(query)[:15]:
            cat = str(entry.get("heroName", ""))
            try:
                results.extend(app.api.get_upgrade_skins(cat))
            except Exception:
                pass
    except Exception as e:
        LOG.warning("upgrade search: %s", e)

    # 3) Fallback index lokal
    if len(results) < 3:
        run_busy(console, "Memuat index lokal...", app.search.ensure_for_search)
        results.extend(app.search.search(query))

    # dedupe
    seen: set[str] = set()
    unique: list[SkinItem] = []
    for s in results:
        k = s.download_url
        if k and k not in seen:
            seen.add(k)
            unique.append(s)

    if not unique:
        console.print(f"[yellow]'{query}' tidak ditemukan. Coba kata lebih pendek (mis. 'layla').[/]")
        _pause()
        return

    labels = [f"{s.skin_name} — {s.hero_name} [{s.source}]" for s in unique]
    idx = pick_from_list(console, labels, f"Hasil '{query}' ({len(unique)})", page_size=15)
    if idx is not None:
        _inject_flow(app, unique[idx])
    _pause()


def menu_browse_heroes(app: App) -> None:
    console.print("\n[bold]Browse Hero[/]")
    try:
        names = run_busy(console, "Memuat daftar hero...", app.api.list_hero_names)
    except Exception as e:
        console.print(f"[red]Gagal: {e}[/]")
        _pause()
        return

    if not names:
        console.print("[red]Daftar hero kosong — cek koneksi internet.[/]")
        _pause()
        return

    console.print(f"[green]Loaded {len(names)} hero.[/] Tekan [S] untuk cari, [N]/[P] halaman.\n")
    idx = pick_from_list(console, names, "Pilih Hero")
    if idx is None:
        return

    hero = names[idx]
    try:
        skins = run_busy(console, f"Memuat skin {hero}...", lambda: app.api.get_skins_for_hero(hero))
    except Exception as e:
        console.print(f"[red]{e}[/]")
        _pause()
        return

    skin = _pick_skin(skins, f"Skin — {hero}")
    if skin:
        _inject_flow(app, skin)
    _pause()


def menu_upgrade(app: App) -> None:
    console.print("\n[bold]Upgrade Skins[/]")
    try:
        menu = run_busy(console, "Memuat daftar upgrade...", app.api.get_upgrade_menu)
    except Exception as e:
        console.print(f"[red]Gagal: {e}[/]")
        _pause()
        return

    if not menu:
        console.print("[yellow]Daftar upgrade kosong.[/]")
        _pause()
        return

    labels = [str(x.get("heroName", x.get("name", "?"))) for x in menu]
    console.print(f"[green]{len(labels)} upgrade skin.[/] [S] cari | [N]/[P] halaman\n")

    idx = pick_from_list(console, labels, "Pilih Upgrade Skin")
    if idx is None:
        return

    entry = menu[idx]
    cat = str(entry.get("heroName", ""))
    try:
        skins = run_busy(
            console,
            f"Memuat {cat[:40]}...",
            lambda: app.api.get_upgrade_skins_for_entry(entry),
        )
    except Exception as e:
        console.print(f"[red]{e}[/]")
        _pause()
        return

    if not skins:
        console.print(f"[yellow]Tidak ada file skin untuk '{cat}'.[/]")
        _pause()
        return

    skin = _pick_skin(skins, f"Upgrade — {cat}")
    if skin:
        _inject_flow(app, skin)
    _pause()


def menu_custom(app: App) -> None:
    try:
        skins = run_busy(console, "Memuat custom skins...", app.api.get_custom_skins)
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
        console.print("[yellow]Belum ada backup. Dibuat otomatis saat inject pertama.[/]")
        _pause()
        return
    labels = [
        f"{b.hero_name} (id={b.hero_id}) — {b.skin_name}"
        for b in backups
    ]
    labels.append(">>> Restore SEMUA backup")
    idx = pick_from_list(console, labels, "Restore Default Skin", page_size=15)
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
        _do_restore(backups[idx].hero_id, backups[idx].hero_name)
    _pause()


def menu_status(app: App) -> None:
    pf = app.preflight or app.init()
    table = Table(title="Status")
    table.add_column("Item")
    table.add_column("Nilai")
    table.add_row("Mode", pf.mode)
    table.add_row("Backend", pf.backend_name)
    table.add_row("Package", pf.package or "-")
    table.add_row("Assets", (pf.assets_path or "-")[-60:])
    table.add_row("OK", "Ya" if pf.ok else "Tidak")
    try:
        table.add_row("Hero tersedia", str(len(app.api.list_hero_names())))
        table.add_row("Upgrade skin", str(len(app.api.get_upgrade_menu())))
    except Exception:
        pass
    table.add_row("Index search", str(app.search.count))
    console.print(table)
    for m in pf.messages:
        console.print(m)
    backups = app.list_backups()
    console.print(f"\n[bold]Backup:[/] {len(backups)}")
    for b in backups[:10]:
        console.print(f"  - {b.hero_name} / {b.skin_name} ({len(b.files)} file)")
    _pause()


def menu_settings(app: App) -> None:
    opts = ["Auto (root → shizuku → direct)", "Root only", "No-root (Shizuku)"]
    idx = pick_from_list(console, opts, "Access Mode", page_size=10)
    if idx is None:
        return
    modes = ["auto", "root", "noroot"]
    app.mode_override = modes[idx]
    app.cfg.setdefault("access", {})["mode"] = modes[idx]
    app.init(force=True)
    pf = app.preflight
    console.print(f"[green]Mode: {pf.backend_name if pf else '?'}[/]")
    if pf:
        for m in pf.messages:
            console.print(m)
    _pause()


def menu_refresh_full(app: App) -> None:
    console.print("[yellow]Refresh index (opsional) — untuk search offline lebih lengkap.[/]")
    if not _confirm("Lanjut refresh index?", "Lanjut? (y/N): "):
        return

    with Progress(
        SpinnerColumn(),
        TextColumn("[bold]{task.description}"),
        BarColumn(bar_width=30),
        TaskProgressColumn(),
        console=console,
    ) as progress:
        task = progress.add_task("Memulai...", total=100)

        def on_prog(msg: str, cur: int, total: int) -> None:
            progress.update(task, completed=cur, description=msg)

        n = app.search.build_full(refresh=True, on_progress=on_prog)

    console.print(f"[green]Index: {n} skin[/]")
    _pause()


def run_interactive(app: App) -> None:
    logging.getLogger().setLevel(logging.WARNING)

    clear_screen()
    with busy(console, "Inisialisasi..."):
        pf = app.init()
        app.search.load(allow_build=False)
        try:
            run_busy(console, "Memuat hero...", app.api.list_hero_names)
        except Exception:
            pass

    if not pf.ok and sys.platform != "win32":
        console.print("[yellow]Beberapa cek gagal — inject mungkin terbatas.[/]")

    actions: dict[str, Callable[[App], None]] = {
        "1": menu_browse_heroes,
        "2": menu_search,
        "3": menu_upgrade,
        "4": menu_custom,
        "5": menu_restore,
        "6": menu_status,
        "7": menu_refresh_full,
        "8": menu_settings,
    }

    while True:
        clear_screen()
        _render_header(app)
        _render_menu()

        try:
            choice = input("\nPilih: ").strip()
        except (EOFError, KeyboardInterrupt):
            break

        if choice == "0":
            clear_screen()
            console.print("[dim]Sampai jumpa.[/]")
            break

        fn = actions.get(choice)
        if not fn:
            console.print("[red]Pilihan tidak valid.[/]")
            try:
                input("")
            except (EOFError, KeyboardInterrupt):
                pass
            continue

        try:
            fn(app)
        except KeyboardInterrupt:
            console.print("\n[dim]Dibatalkan.[/]")
            _pause()
        except Exception as e:
            LOG.exception("menu error")
            console.print(f"[red]Error: {e}[/]")
            _pause()
