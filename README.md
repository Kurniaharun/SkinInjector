```
  ____  _             _   ___       _           _
 / ___|(_)_ __  _   _| | |_ _|_ __ | |_ ___  __| |___
 \___ \| | '_ \| | | | |  | || '_ \| __/ _ \/ _` / __|
  ___) | | | | | |_| | |  | || | | | ||  __/ (_| \__ \
 |____/|_|_| |_|\__,_|_| |___|_| |_|\__\___|\__,_|___/
        MLBB Skin Injector · Termux · Root & Shizuku
```

<p align="center">
  <a href="https://github.com/Kurniaharun/SkinInjector"><img src="https://img.shields.io/badge/python-3.10+-blue?style=for-the-badge&logo=python&logoColor=white" alt="Python"></a>
  <a href="https://github.com/Kurniaharun/SkinInjector"><img src="https://img.shields.io/badge/platform-Termux%20%7C%20Android-green?style=for-the-badge&logo=android&logoColor=white" alt="Termux"></a>
  <a href="https://github.com/Kurniaharun/SkinInjector"><img src="https://img.shields.io/badge/mode-root%20%7C%20shizuku-cyan?style=for-the-badge" alt="Mode"></a>
</p>

---

Script Python untuk **inject skin Mobile Legends** langsung dari Termux.  
UI terminal modern dengan **figlet banner**, progress bar Rich, dan menu interaktif.

> Sumber skin sama dengan APK iMOBA — API `imb.expressme.in`

---

## Fitur

| Kategori | Fitur |
|----------|-------|
| **Skin** | Browse hero · Search · Upgrade · Custom |
| **Effects** | Recall · Emote · Trail · Respawn · Painted |
| **Safety** | Backup otomatis · Rollback · Restore default |
| **API** | Backup official per hero · 130+ hero · 300+ upgrade |
| **UX** | Figlet splash · Tabel menu · Pagination · Filter `[S]` |
| **Akses** | Root · Shizuku · Auto-detect |

---

## Quick Start

### 1. Install Termux

```bash
pkg update && pkg upgrade -y
pkg install python git unzip -y
```

### 2. Clone & setup

```bash
git clone https://github.com/Kurniaharun/SkinInjector.git
cd SkinInjector
pip install -r requirements.txt
pkg install aria2 -y    # opsional — download 16x lebih cepat
```

### 3. Jalankan

```bash
# Root (recommended)
python main.py --mode root

# Shizuku (no-root)
python main.py --mode noroot

# Auto-detect
python main.py
```

---

## Menu Interaktif

```
╔════╦════════════════════╦══════════════════════════════════╗
║  # ║ Menu               ║ Info                             ║
╠════╬════════════════════╬══════════════════════════════════╣
║  1 ║ Browse Hero        ║ ~130 hero · paginated · [S] cari ║
║  2 ║ Search Skin        ║ hero, skin, recall, effect        ║
║  3 ║ Upgrade Skins      ║ 324 skin upgrade                  ║
║  4 ║ Custom Skins       ║ skin custom dari API              ║
║  5 ║ Restore Default    ║ backup lokal                      ║
║  6 ║ Status & Backup    ║ info sistem                       ║
║  7 ║ Refresh Index      ║ opsional                          ║
║  8 ║ Settings           ║ root / shizuku / auto             ║
║  9 ║ Effects & Recall   ║ recall · emote · trail · respawn  ║
║ 10 ║ Backup Official    ║ BACKUP.zip dari server            ║
║  0 ║ Keluar             ║                                   ║
╚════╩════════════════════╩══════════════════════════════════╝
```

---

## CLI One-Shot

```bash
python main.py status
python main.py search "chou king"
python main.py inject --hero Chou --skin "King Of Muai Thai"
python main.py inject --hero Dyrroth --skin venom --dry-run
python main.py restore --hero-id 47
python main.py restore --all
python main.py refresh
```

---

## Cara Kerja

```
┌─────────────┐     ┌──────────────┐     ┌─────────────────┐
│  API iMOBA  │────▶│ Download ZIP │────▶│ Backup default  │
└─────────────┘     └──────────────┘     └────────┬────────┘
                                                  │
                                                  ▼
                                         ┌─────────────────┐
                                         │ unzip → assets/ │
                                         └─────────────────┘
```

1. Fetch config dari `imb.expressme.in`
2. Download ZIP skin (GitHub / CDN)
3. Backup file game yang akan ditimpa
4. Extract ke folder MLBB via **root** atau **Shizuku**
5. Restore = kembalikan backup lokal

---

## Path Target

```
/storage/emulated/0/Android/data/com.mobile.legends/files/dragon2017/assets/
```

| Package | Region |
|---------|--------|
| `com.mobile.legends` | Global |
| `com.vng.mlbbvn` | Vietnam |
| `com.mobilelegends.hwag` | Huawei |

---

## Struktur Data

```
SkinInjector/
├── main.py              # entry point
├── config/default.yaml  # konfigurasi
├── src/
│   ├── api_client.py    # API imb.expressme.in
│   ├── injector.py      # inject + rollback
│   ├── backup_manager.py
│   └── ui/
│       ├── branding.py  # figlet banner
│       ├── cli.py       # menu interaktif
│       └── progress_ui.py
└── data/
    ├── cache/           # cache API
    ├── downloads/       # ZIP temp
    └── backups/         # backup skin default
```

---

## Download Cepat (aria2)

Script otomatis pakai **aria2c** kalau terinstall (16 koneksi paralel). Tanpa aria2 → HTTP fallback buffer 256KB.

```bash
pkg install aria2 -y
```

Setting: Menu **8** → Download → Auto / aria2 / HTTP

Saat inject tampil:

- Figlet banner + status panel
- Panel info skin + tipe (recall / upgrade / hero)
- Progress bar **0–100%** + sub-bar download
- Step: validasi ZIP → backup → inject → cleanup

---

## Keamanan

- Download hanya dari URL API resmi
- Validasi ZIP (ukuran, integrity, anti `../`)
- Backup otomatis sebelum timpa file game
- Auto-rollback jika unzip gagal
- Tidak kirim data pribadi

> **Risiko ban MLBB tetap ada** — modifikasi file game.

---

## Tips

- Tutup **MLBB** sebelum inject
- Android 11+ tanpa root → wajib **Shizuku**
- HP root → `python main.py --mode root`
- Nama skin terpotong di API? Tool otomatis expand ke nama lengkap

---

<p align="center">
  <b>SkinInjector</b> · made for Termux · <a href="https://github.com/Kurniaharun/SkinInjector">GitHub</a>
</p>
