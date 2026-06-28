# SkinJECT Android (Flutter)

Aplikasi **SkinJECT** — MLBB Skin Injector versi APK.  
Mirror fitur script Python: browse hero by role, search, upgrade, custom bundle, effects, inject via **Root** atau **Shizuku**.

## Fitur

- UI purple modern (inspirasi MLBB tool) + **Lucide icons**
- API langsung `imb.expressme.in` (tanpa scrape)
- Popup setup wajib saat pertama buka
- Mode akses: **Auto / Root / Shizuku**
- Auto-detect package MLBB (Global / VN / Huawei)
- Inject: download ZIP → unzip ke `Android/data/.../dragon2017/assets`

## Persyaratan

- Flutter SDK 3.16+ & Android SDK
- HP Android dengan **Root (su)** atau **Shizuku** (wajib Android 11+)
- Mobile Legends terinstall
- Tutup MLBB sebelum inject

## Setup & Build APK

```bash
cd android

# Set path Flutter SDK (Windows)
echo flutter.sdk=C:\\flutter > android\\local.properties

flutter pub get
flutter build apk --release
```

APK output: `build/app/outputs/flutter-apk/app-release.apk`

Debug di device:

```bash
flutter run
```

## Shizuku

1. Install [Shizuku](https://shizuku.rikka.app/)
2. Start Shizuku (ADB / root / wireless)
3. Buka SkinJECT → Pengaturan → mode **Shizuku** → minta izin

## Struktur

```
android/
├── lib/                 # Dart UI + API client
├── android/             # Native Kotlin (Root/Shizuku inject)
├── pubspec.yaml
└── README.md
```

## API (sama Python)

- `GET getConnection.php` → discovery endpoint
- `GET getHeroes2.php` / POST `category={role}`
- `POST getUpgradeSkins.php` · `getEmotes.php` · `getSkinMenu.php`
- `GET getcustomSkinMenu.php?category={bundle name}`

---

**SkinJECT by KurrXd**
