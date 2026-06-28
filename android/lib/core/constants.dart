/// SkinJECT constants — mirror Python config/default.yaml
class AppConstants {
  static const appName = 'SkinJECT';
  static const author = 'KurrXd';
  static const version = '1.0.0';

  static const apiBase = 'https://imb.expressme.in/api/public_connection';
  static const configEndpoint = 'getConnection.php';
  static const userAgent = 'SkinJECT/1.0 KurrXd Flutter';

  static const storageRoot = '/storage/emulated/0';
  static const assetsSubpath = 'files/dragon2017/assets';

  static const packages = [
    'com.mobile.legends',
    'com.vng.mlbbvn',
    'com.mobilelegends.hwag',
  ];

  static const heroRoles = [
    'Assassin',
    'Fighter',
    'Tank',
    'Support',
    'Mage',
    'Marksman',
  ];

  static const effectCategories = [
    ('Recall Animations', 'recall'),
    ('Emotes', 'emote'),
    ('TRAIL ANIMATION', 'trail'),
    ('RESPAWN ANIMATION', 'respawn'),
    ('PAINTED SKIN', 'painted'),
    ('ELIMINATED BATTLE', 'eliminated'),
  ];

  static String assetsPath(String package) =>
      '$storageRoot/Android/data/$package/$assetsSubpath';
}

enum AccessMode { auto, root, shizuku }

extension AccessModeLabel on AccessMode {
  String get label => switch (this) {
        AccessMode.auto => 'Auto',
        AccessMode.root => 'Root',
        AccessMode.shizuku => 'Shizuku',
      };

  String get description => switch (this) {
        AccessMode.auto =>
          'Deteksi otomatis — Root prioritas, lalu Shizuku',
        AccessMode.root => 'Wajib akses su/root',
        AccessMode.shizuku => 'Shizuku + izin shell (Android 11+)',
      };
}
