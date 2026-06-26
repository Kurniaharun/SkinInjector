# MLBB Skin Injector

Script Python inject skin Mobile Legends untuk **Termux**. Dual mode **root** dan **no-root (Shizuku)**.

## Fitur

- Browse hero & pilih skin
- Search skin (fuzzy)
- Upgrade skins & custom skins
- Inject ZIP ke `Android/data/.../dragon2017/assets/`
- **Restore default skin** dari backup otomatis
- Mode: `auto` | `root` | `noroot`
- **Progress bar 0-100%** + spinner saat download & inject (menu interaktif)
- Backup otomatis + rollback kalau inject gagal

## Install di Termux

```bash
pkg update && pkg upgrade -y
pkg install python git unzip -y
cd ~/injectskin
pip install -r requirements.txt
```

### Root (HP kamu)
```bash
python main.py --mode root
```

### No-root (Shizuku)
1. Install Shizuku + pair `rish` di Termux
2. ```bash
   python main.py --mode noroot
   ```

### Auto-detect
```bash
python main.py
```

## Menu

```
[1] Browse Hero
[2] Search Skin
[3] Upgrade Skins
[4] Custom Skins
[5] Restore Default Skin
[6] Status & Backup
[7] Refresh cache
[8] Settings (root/no-root)
```

## CLI one-shot

```bash
python main.py status
python main.py search "layla"
python main.py inject --hero Dyrroth --skin venom
python main.py inject --hero Dyrroth --skin basic --dry-run
python main.py restore --hero-id 47
python main.py restore --all
python main.py refresh
```

## Cara kerja

1. Fetch config API `imb.expressme.in` (sama seperti APK iMOBA)
2. Download ZIP skin dari GitHub/CDN
3. Backup file game yang akan ditimpa
4. `unzip -o` ke folder MLBB via root atau Shizuku
5. Restore = copy backup kembali ke folder game

## Path target

```
/storage/emulated/0/Android/data/com.mobile.legends/files/dragon2017/assets/
```

Package lain: `com.vng.mlbbvn`, `com.mobilelegends.hwag`

## Data lokal

```
data/cache/     — cache API
data/downloads/ — ZIP sementara
data/backups/   — backup default skin
logs/           — injector.log
```

## Keamanan script

- Hanya download dari URL API resmi (GitHub/CDN skin)
- Validasi ZIP (integrity, ukuran, anti path-traversal `../`)
- Backup file asli sebelum timpa
- Auto-rollback jika unzip gagal
- Tidak kirim data pribadi / tidak akses SMS/kontak
- Risiko ban MLBB tetap ada (modifikasi file game)

## Progress inject (menu interaktif)

Saat inject, tampil:
- Panel info skin + URL
- Spinner + bar **0-100%**
- Sub-bar download (MB, kecepatan, ETA)
- Step: validasi ZIP, backup default, inject, cleanup

CLI one-shot (`python main.py inject ...`) menampilkan progress teks `[ 45%] Download 4.2/9.1 MB`

## Catatan

- Tutup MLBB sebelum inject
- Android 11+ tanpa root wajib Shizuku
- HP root: pakai `--mode root`
