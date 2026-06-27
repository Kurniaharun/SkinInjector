"""Interactive CLI menus — responsive, paginated, searchable."""

from __future__ import annotations

import logging
import sys
from typing import Any, Callable, Optional

from rich.console import Console
from rich.progress import BarColumn, Progress, SpinnerColumn, TaskProgressColumn, TextColumn
from rich.table import Table

from ..app import App
from ..catalog_store import catalog_ready, catalog_summary
from ..errors import InjectorError
from ..models import SkinItem
from ..api_client import HERO_ROLES
from ..skin_grade import SKIN_GRADES, grade_label
from .branding import print_banner, print_goodbye, print_status, render_menu
from .console import make_console
from .picker import pick_from_list, pick_skin_labels
from .progress_ui import RichInjectReporter
from .screen import busy, clear_screen
from .theme import PROMPT, PROMPT_SYMBOL

console = make_console()
LOG = logging.getLogger(__name__)


def _pause() -> None:
    try:
        console.input(f"\n[{PROMPT}]{PROMPT_SYMBOL}[/] [dim]Enter = kembali[/] ")
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
    if not _confirm(f"Inject [bold cyan]{skin.label()}[/]"):
        return
    try:
        with RichInjectReporter(console, skin) as ui:
            app.inject_skin(skin, reporter=ui.reporter)
    except InjectorError as e:
        console.print(f"[red]Gagal: {e}[/]")


def _dl_label(app: App) -> str:
    if app.injector and getattr(app.injector, "downloader", None):
        return app.injector.downloader.engine_label()
    return ""


def _render_header(app: App, *, show_banner: bool = False) -> None:
    pf = app.preflight
    if show_banner:
        print_banner(console)
    if pf:
        print_status(console, pf.backend_name, pf.package or "?", _dl_label(app))


def _render_menu() -> None:
    render_menu(console)


def _pick_skin(skins: list[SkinItem], title: str) -> Optional[SkinItem]:
    if not skins:
        console.print("[yellow]Tidak ada skin untuk hero ini.[/]")
        return None
    labels = [s.label() for s in skins]
    idx = pick_skin_labels(console, labels, title)
    return skins[idx] if idx is not None else None


def menu_search(app: App) -> None:
    console.print("\n[bold]Search[/]")
    console.print("[dim]Contoh: layla, gusion, dyrroth venom[/]")
    try:
        query = input("\nKetik nama: ").strip()
    except (EOFError, KeyboardInterrupt):
        return
    if not query:
        return

    app.search.ensure_for_search()
    results: list[SkinItem] = list(app.search.search(query))

    if len(results) < 5:
        app.api.warmup()
        for hero in app.api.search_hero_names(query)[:6]:
            results.extend(app.api.get_skins_for_hero(hero))
        for entry in app.api.search_upgrade_entries(query)[:10]:
            results.extend(app.api.get_upgrade_skins_for_entry(entry))
        results.extend(app.api.search_effects(query))
        results.extend(app.api.search_custom_bundles(query))

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

    labels = [f"{s.label()} [{s.source}]" for s in unique]
    idx = pick_from_list(console, labels, f"Hasil '{query}'")
    if idx is not None:
        _inject_flow(app, unique[idx])
    _pause()


def menu_browse_by_role(app: App) -> None:
    roles = list(HERO_ROLES)
    try:
        cats = app.api.get_role_categories()
        api_roles = [str(x.get("name", "")) for x in cats if x.get("name")]
        if api_roles:
            roles = api_roles
    except Exception as e:
        LOG.warning("role categories: %s", e)

    console.print(f"\n[bold]Browse by Role[/]  [dim]{len(roles)}[/]")
    idx = pick_from_list(console, roles, "Pilih Role")
    if idx is None:
        return

    role = roles[idx]
    try:
        names = app.api.list_heroes_by_role(role)
    except Exception as e:
        console.print(f"[red]{e}[/]")
        _pause()
        return
    if not names:
        console.print("[yellow]Tidak ada hero untuk role ini.[/]")
        _pause()
        return

    console.print(f"\n[bold]{role}[/]  [dim]{len(names)} hero[/]")
    hidx = pick_from_list(console, names, f"Hero — {role}")
    if hidx is None:
        return

    hero = names[hidx]
    try:
        skins = app.api.get_skins_for_hero(hero)
    except Exception as e:
        console.print(f"[red]{e}[/]")
        _pause()
        return

    skin = _pick_skin(skins, f"Skin — {hero}")
    if skin:
        _inject_flow(app, skin)
    _pause()


def menu_browse_heroes(app: App) -> None:
    try:
        names = app.api.list_hero_names()
    except Exception as e:
        console.print(f"[red]{e}[/]")
        _pause()
        return
    if not names:
        console.print("[red]Kosong.[/]")
        _pause()
        return

    console.print(f"\n[bold]Browse Hero[/]  [dim]{len(names)}[/]")
    idx = pick_from_list(console, names, "Pilih Hero")
    if idx is None:
        return

    hero = names[idx]
    try:
        skins = app.api.get_skins_for_hero(hero)
    except Exception as e:
        console.print(f"[red]{e}[/]")
        _pause()
        return

    skin = _pick_skin(skins, f"Skin — {hero}")
    if skin:
        _inject_flow(app, skin)
    _pause()


def menu_upgrade(app: App) -> None:
    try:
        menu = app.api.get_upgrade_menu()
        labels = app.api.get_upgrade_menu_labels()
    except Exception as e:
        console.print(f"[red]{e}[/]")
        _pause()
        return
    if not menu:
        console.print("[yellow]Kosong.[/]")
        _pause()
        return

    console.print(f"\n[bold]Upgrade[/]  [dim]{len(labels)}[/]")

    idx = pick_from_list(console, labels, "Pilih Upgrade")
    if idx is None:
        return

    entry = menu[idx]
    cat_label = labels[idx]
    try:
        skins = app.api.get_upgrade_skins_for_entry(entry)
    except Exception as e:
        console.print(f"[red]{e}[/]")
        _pause()
        return

    if not skins:
        console.print(f"[yellow]Tidak ada file skin untuk '{cat_label}'.[/]")
        _pause()
        return

    skin = _pick_skin(skins, f"Upgrade — {cat_label}")
    if skin:
        _inject_flow(app, skin)
    _pause()


def menu_effects(app: App) -> None:
    console.print("\n[bold]Effects[/]")
    cats = app.api.list_effect_categories()
    labels = [name for name, _src in cats]
    idx = pick_from_list(console, labels, "Kategori", page_size=10)
    if idx is None:
        return

    cat_name, _src = cats[idx]
    try:
        items = app.api.get_effects(cat_name)
    except Exception as e:
        console.print(f"[red]Gagal: {e}[/]")
        _pause()
        return

    if not items:
        console.print("[yellow]Kosong.[/]")
        _pause()
        return

    skin = _pick_skin(items, cat_name)
    if skin:
        _inject_flow(app, skin)
    _pause()


def menu_api_backup(app: App) -> None:
    console.print("\n[bold]Backup API[/]")
    try:
        names = app.api.list_hero_names()
    except Exception as e:
        console.print(f"[red]{e}[/]")
        _pause()
        return

    idx = pick_from_list(console, names, "Pilih Hero (Backup API)")
    if idx is None:
        return

    hero = names[idx]
    try:
        backups = app.api.list_backup_skins(hero)
    except Exception as e:
        console.print(f"[red]{e}[/]")
        _pause()
        return

    if not backups:
        console.print(f"[yellow]Tidak ada entry BACKUP untuk {hero} di API.[/]")
        _pause()
        return

    skin = _pick_skin(backups, f"Backup — {hero}")
    if skin:
        if _confirm(
            f"[yellow]Inject backup official[/] [bold]{skin.label()}[/]\n"
            "[dim]Ini akan timpa file skin hero di folder game.[/]",
            "Lanjut? (y/N): ",
        ):
            try:
                with RichInjectReporter(console, skin) as ui:
                    app.inject_skin(skin, reporter=ui.reporter)
            except InjectorError as e:
                console.print(f"[red]Gagal: {e}[/]")
    _pause()


def menu_custom(app: App) -> None:
    try:
        bundles = app.api.get_custom_bundles()
    except Exception as e:
        console.print(f"[red]{e}[/]")
        _pause()
        return
    if not bundles:
        console.print("[yellow]Kosong.[/]")
        _pause()
        return

    labels = [str(b.get("name", f"Bundle {b.get('id', '?')}")) for b in bundles]
    console.print(f"\n[bold]Custom Bundle[/]  [dim]{len(labels)} koleksi[/]")
    idx = pick_from_list(console, labels, "Pilih Koleksi")
    if idx is None:
        return

    bundle = bundles[idx]
    bid = str(bundle.get("id", ""))
    bname = labels[idx]
    try:
        skins = app.api.get_custom_bundle_skins(bid, bname)
    except Exception as e:
        console.print(f"[red]{e}[/]")
        _pause()
        return

    skin = _pick_skin(skins, f"Custom — {bname}")
    if skin:
        _inject_flow(app, skin)
    _pause()


def menu_announcements(app: App) -> None:
    try:
        items = app.api.get_announcements()
    except Exception as e:
        console.print(f"[red]{e}[/]")
        _pause()
        return
    if not items:
        console.print("[yellow]Belum ada pengumuman.[/]")
        _pause()
        return

    console.print(f"\n[bold]News / Update[/]  [dim]{len(items)}[/]\n")
    for i, item in enumerate(items, 1):
        name = str(item.get("name", item.get("title", f"#{i}")))
        date = str(item.get("date", item.get("created", "")))
        des = str(item.get("des", item.get("description", "")))
        console.print(f"[cyan]{i}.[/] [bold]{name}[/]")
        if date:
            console.print(f"   [dim]{date}[/]")
        if des:
            short = des if len(des) <= 200 else des[:197] + "..."
            console.print(f"   {short}")
        console.print()
    _pause()


def menu_restore(app: App) -> None:
    backups = app.list_backups()
    if not backups:
        console.print("[yellow]Belum ada backup lokal.[/]")
        console.print("[dim]Pakai menu [13] Backup Official API untuk restore default.[/]")
        _pause()
        return
    labels = [
        f"{b.hero_name} (id={b.hero_id}) — {b.skin_name}"
        for b in backups
    ]
    labels.append(">>> Restore SEMUA backup")
    idx = pick_from_list(console, labels, "Restore")
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
        table.add_row("Recall", str(len(app.api.get_effects("Recall Animations"))))
        table.add_row("Emotes", str(len(app.api.get_effects("Emotes"))))
        table.add_row("Eliminated", str(len(app.api.get_effects("ELIMINATED BATTLE"))))
        table.add_row("Custom bundle", str(len(app.api.get_custom_bundles())))
        table.add_row("News", str(len(app.api.get_announcements())))
    except Exception:
        pass
    table.add_row("Katalog", catalog_summary() if catalog_ready() else "belum ada")
    table.add_row("Index search", str(app.search.count))
    if app.injector and getattr(app.injector, "downloader", None):
        table.add_row("Download", app.injector.downloader.engine_label())
    console.print(table)
    for m in pf.messages:
        console.print(m)
    backups = app.list_backups()
    console.print(f"\n[bold]Backup:[/] {len(backups)}")
    for b in backups[:10]:
        console.print(f"  - {b.hero_name} / {b.skin_name} ({len(b.files)} file)")
    _pause()


def menu_advanced_batch(app: App) -> None:
    console.print("\n[bold]Advanced — Batch Apply[/]")
    console.print(
        "[dim]Inject satu tipe skin ke semua hero dalam role yang punya skin tersebut.[/]"
    )
    console.print("[yellow]Tutup MLBB sebelum batch inject.[/]\n")

    roles = list(HERO_ROLES)
    try:
        cats = app.api.get_role_categories()
        api_roles = [str(x.get("name", "")) for x in cats if x.get("name")]
        if api_roles:
            roles = api_roles
    except Exception as e:
        LOG.warning("role categories: %s", e)

    ridx = pick_from_list(console, roles, "Pilih Role Hero")
    if ridx is None:
        return
    role = roles[ridx]

    try:
        counts = app.api.grade_counts_for_role(role)
        heroes_in_role = app.api.list_heroes_by_role(role)
    except Exception as e:
        console.print(f"[red]{e}[/]")
        _pause()
        return

    grade_labels: list[str] = []
    grade_keys: list[str] = []
    for label, key in SKIN_GRADES:
        n = counts.get(key, 0)
        if n > 0:
            grade_labels.append(f"{label} ({n}/{len(heroes_in_role)} hero)")
            grade_keys.append(key)

    if not grade_labels:
        console.print(f"[yellow]Tidak ada skin bertipe standar untuk role {role}.[/]")
        _pause()
        return

    console.print(f"\n[bold]{role}[/]  [dim]{len(heroes_in_role)} hero[/]")
    gidx = pick_from_list(console, grade_labels, "Pilih Tipe Skin")
    if gidx is None:
        return

    grade = grade_keys[gidx]
    try:
        matches = app.api.find_skins_for_role_grade(role, grade)
    except Exception as e:
        console.print(f"[red]{e}[/]")
        _pause()
        return

    if not matches:
        console.print(f"[yellow]Tidak ada hero {role} dengan skin {grade_label(grade)}.[/]")
        _pause()
        return

    console.print(f"\n[bold]Preview[/] — {grade_label(grade)} → {len(matches)} hero")
    table = Table(show_header=True, header_style="bold cyan")
    table.add_column("#", style="dim", width=4)
    table.add_column("Hero")
    table.add_column("Skin")
    for i, (hero, skin) in enumerate(matches, 1):
        table.add_row(str(i), hero, skin.label())
    console.print(table)

    if not _confirm(
        f"\n[yellow]Batch inject[/] [bold]{grade_label(grade)}[/] ke "
        f"[bold]{len(matches)}[/] hero [cyan]{role}[/]?\n"
        "[dim]Proses bisa lama. Jangan buka MLBB.[/]",
        "Lanjut batch inject? (y/N): ",
    ):
        _pause()
        return

    ok_n = 0
    fail_n = 0
    with Progress(
        SpinnerColumn(),
        TextColumn("[bold]{task.description}"),
        BarColumn(bar_width=32),
        TaskProgressColumn(),
        console=console,
    ) as progress:
        task = progress.add_task("Memulai...", total=len(matches))

        def on_start(cur: int, total: int, hero: str, skin: SkinItem) -> None:
            progress.update(
                task,
                completed=cur - 1,
                description=f"[cyan]{hero}[/] — {skin.skin_name[:40]}",
            )

        def on_done(cur: int, total: int, hero: str, success: bool, msg: str) -> None:
            nonlocal ok_n, fail_n
            if success:
                ok_n += 1
            else:
                fail_n += 1
            progress.update(
                task,
                completed=cur,
                description=f"{'[green]OK' if success else '[red]FAIL'}[/] {hero}",
            )

        try:
            result = app.inject_batch(
                matches,
                on_hero_start=on_start,
                on_hero_done=on_done,
            )
        except InjectorError as e:
            console.print(f"[red]{e}[/]")
            _pause()
            return

    console.print(
        f"\n[bold]Selesai[/] — [green]{result.success_count} OK[/]"
        f"{f', [red]{result.fail_count} gagal[/]' if result.fail_count else ''}"
    )
    if result.failed:
        console.print("\n[red]Gagal:[/]")
        for hero, err in result.failed:
            console.print(f"  [dim]•[/] {hero}: {err}")
    _pause()


def menu_settings(app: App) -> None:
    section = pick_from_list(
        console,
        ["Akses MLBB (root/shizuku)", "Download (aria2/http)"],
        "Settings",
        page_size=10,
    )
    if section is None:
        return

    if section == 0:
        opts = ["Auto", "Root only", "No-root Shizuku"]
        idx = pick_from_list(console, opts, "Akses", page_size=10)
        if idx is None:
            return
        modes = ["auto", "root", "noroot"]
        app.mode_override = modes[idx]
        app.cfg.setdefault("access", {})["mode"] = modes[idx]
    else:
        opts = ["Auto (aria2 kalau ada)", "Paksa aria2", "HTTP saja"]
        idx = pick_from_list(console, opts, "Download", page_size=10)
        if idx is None:
            return
        engines = ["auto", "aria2", "requests"]
        app.cfg.setdefault("download", {})["engine"] = engines[idx]

    app.init(force=True)
    pf = app.preflight
    console.print(f"[green]OK[/] {_dl_label(app) or pf.backend_name if pf else '?'}")
    _pause()


def menu_update_catalog(app: App) -> None:
    if not _confirm(
        "[yellow]Update katalog[/] — download data terbaru dari API.\n"
        "[dim]Butuh internet. Proses ~1-3 menit.[/]",
        "Lanjut update? (y/N): ",
    ):
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

        try:
            msg = app.update_catalog(on_progress=on_prog)
        except InjectorError as e:
            console.print(f"[red]{e}[/]")
            _pause()
            return

    console.print(f"[green]{msg}[/]")
    try:
        n = app.search.build_full(refresh=True)
        console.print(f"[green]Search index: {n} skin[/]")
    except Exception as e:
        console.print(f"[yellow]Index: {e}[/]")
    _pause()


def menu_refresh_full(app: App) -> None:
    if not catalog_ready():
        console.print("[yellow]Katalog belum ada — pakai menu [10] Update Katalog dulu.[/]")
        _pause()
        return
    console.print("[dim]Rebuild search index dari katalog lokal (tanpa internet).[/]")
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
    with busy(console, "Loading..."):
        pf = app.init()
        app.search.load(allow_build=False)

    first_draw = True

    if not pf.ok and sys.platform != "win32":
        console.print("[yellow]! Beberapa cek gagal — inject mungkin terbatas.[/]\n")

    actions: dict[str, Callable[[App], None]] = {
        "1": menu_browse_heroes,
        "2": menu_browse_by_role,
        "3": menu_search,
        "4": menu_upgrade,
        "5": menu_custom,
        "6": menu_effects,
        "7": menu_restore,
        "8": menu_announcements,
        "9": menu_status,
        "10": menu_update_catalog,
        "11": menu_refresh_full,
        "12": menu_settings,
        "13": menu_api_backup,
        "14": menu_advanced_batch,
    }

    while True:
        clear_screen()
        if first_draw:
            _render_header(app, show_banner=True)
            first_draw = False
        else:
            pf = app.preflight
            if pf:
                print_status(console, pf.backend_name, pf.package or "?", _dl_label(app))
        _render_menu()

        try:
            choice = console.input(f"\n[{PROMPT}]{PROMPT_SYMBOL}[/] Pilih menu: ").strip()
        except (EOFError, KeyboardInterrupt):
            break

        if choice == "0":
            clear_screen()
            print_goodbye(console)
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
