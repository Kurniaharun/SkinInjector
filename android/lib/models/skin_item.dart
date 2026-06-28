class SkinItem {
  SkinItem({
    required this.id,
    required this.heroName,
    required this.skinName,
    required this.imageUrl,
    required this.downloadUrl,
    this.category = '',
    this.miniPatch = false,
    this.source = 'heroes',
    this.apiCategory = '',
  });

  final String id;
  final String heroName;
  final String skinName;
  final String imageUrl;
  final String downloadUrl;
  final String category;
  final bool miniPatch;
  final String source;
  final String apiCategory;

  String get label => skinName.isNotEmpty ? skinName : heroName;

  String get subtitle {
    if (heroName.isNotEmpty && skinName.isNotEmpty && heroName != skinName) {
      return heroName;
    }
    return category;
  }

  factory SkinItem.fromHeroEntry(
    Map<String, dynamic> data, {
    String hero = '',
  }) {
    final img = _str(data['img']);
    final dl = _str(data['downloadLink'] ?? data['url']);
    final rawSkin = _str(data['heroname'] ?? data['heroName'] ?? data['name']);
    final heroName = hero.isNotEmpty ? hero : _str(data['heroName']);
    return SkinItem(
      id: _str(data['id']),
      heroName: heroName,
      skinName: _cleanName(rawSkin.isNotEmpty ? rawSkin : heroName),
      imageUrl: img,
      downloadUrl: dl,
      category: _str(data['category']),
      miniPatch: _bool(data['mini_patch']),
      source: 'heroes',
      apiCategory: rawSkin,
    );
  }

  factory SkinItem.fromUpgradeEntry(
    Map<String, dynamic> data, {
    String hero = '',
  }) {
    final img = _str(data['img'] ?? data['image']);
    final dl = _str(data['url'] ?? data['downloadLink']);
    final rawName = _str(data['name'] ?? data['skinName'] ?? data['heroname']);
    final apiCat = hero.isNotEmpty ? hero : _str(data['heroName'] ?? data['category']);
    return SkinItem(
      id: _str(data['id']),
      heroName: _cleanName(apiCat),
      skinName: _cleanName(rawName),
      imageUrl: img,
      downloadUrl: dl,
      category: _str(data['category'] ?? apiCat),
      miniPatch: _bool(data['mini_patch']),
      source: 'upgrade',
      apiCategory: apiCat,
    );
  }

  factory SkinItem.fromEffectEntry(Map<String, dynamic> data) {
    final img = _str(data['img']);
    final dl = _str(data['downloadLink'] ?? data['url']);
    final cat = _str(data['category']);
    final rawName = _str(data['name'] ?? data['skinName']);
    const sourceMap = {
      'Recall Animations': 'recall',
      'TRAIL ANIMATION': 'trail',
      'RESPAWN ANIMATION': 'respawn',
      'Emotes': 'emote',
      'PAINTED SKIN': 'painted',
      'ELIMINATED BATTLE': 'eliminated',
    };
    return SkinItem(
      id: _str(data['id']),
      heroName: cat,
      skinName: _cleanName(rawName),
      imageUrl: img,
      downloadUrl: dl,
      category: cat,
      miniPatch: _bool(data['mini_patch']),
      source: sourceMap[cat] ?? 'effect',
      apiCategory: cat,
    );
  }

  factory SkinItem.fromBundleEntry(
    Map<String, dynamic> data, {
    String bundleName = '',
  }) {
    final img = _str(data['img']);
    final dl = _str(data['downloadLink'] ?? data['url']);
    final rawSkin = _str(
      data['heroname'] ?? data['heroName'] ?? data['name'] ?? data['skinName'],
    );
    final hero = _str(data['heroName'] ?? bundleName);
    return SkinItem(
      id: _str(data['id']),
      heroName: hero.isNotEmpty ? hero : bundleName,
      skinName: _cleanName(rawSkin),
      imageUrl: img,
      downloadUrl: dl,
      category: _str(data['category'] ?? bundleName),
      miniPatch: _bool(data['mini_patch']),
      source: 'custom_bundle',
      apiCategory: hero,
    );
  }

  Map<String, dynamic> toJson() => {
        'id': id,
        'heroName': heroName,
        'skinName': skinName,
        'imageUrl': imageUrl,
        'downloadUrl': downloadUrl,
        'category': category,
        'miniPatch': miniPatch,
        'source': source,
        'apiCategory': apiCategory,
      };

  factory SkinItem.fromJson(Map<String, dynamic> j) => SkinItem(
        id: _str(j['id']),
        heroName: _str(j['heroName']),
        skinName: _str(j['skinName']),
        imageUrl: _str(j['imageUrl']),
        downloadUrl: _str(j['downloadUrl']),
        category: _str(j['category']),
        miniPatch: j['miniPatch'] == true,
        source: _str(j['source'], fallback: 'heroes'),
        apiCategory: _str(j['apiCategory']),
      );

  static String _str(dynamic v, {String fallback = ''}) =>
      v == null ? fallback : v.toString();

  static bool _bool(dynamic v) {
    if (v == null) return false;
    if (v is bool) return v;
    return int.tryParse(v.toString()) == 1;
  }

  static String _cleanName(String raw) {
    return raw
        .replaceAll(RegExp(r'\[/?[bi]\]', caseSensitive: false), '')
        .replaceAll('..', '')
        .trim();
  }
}

class PreflightStatus {
  PreflightStatus({
    required this.ok,
    required this.mode,
    required this.backendName,
    required this.package,
    required this.assetsPath,
    this.messages = const [],
  });

  final bool ok;
  final String mode;
  final String backendName;
  final String package;
  final String assetsPath;
  final List<String> messages;
}
