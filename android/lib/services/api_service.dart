import 'dart:convert';
import 'dart:io';

import 'package:http/http.dart' as http;
import 'package:path_provider/path_provider.dart';

import '../core/constants.dart';
import '../models/skin_item.dart';

class ApiException implements Exception {
  ApiException(this.message);
  final String message;
  @override
  String toString() => message;
}

class ApiService {
  ApiService();

  final _client = http.Client();
  Map<String, String> _endpoints = {};
  Map<String, List<dynamic>>? _heroGroups;

  Map<String, String> get headers => {'User-Agent': AppConstants.userAgent};

  Future<Map<String, String>> loadEndpoints({bool refresh = false}) async {
    if (_endpoints.isNotEmpty && !refresh) return _endpoints;
    if (!refresh) {
      final cached = await _readCache('endpoints', hours: 24);
      if (cached is List) {
        _endpoints = _mapEndpoints(cached);
        return _endpoints;
      }
    }
    final url = '${AppConstants.apiBase}/${AppConstants.configEndpoint}';
    final raw = await _get(url);
    if (raw is! List) throw ApiException('Format getConnection tidak valid');
    await _writeCache('endpoints', raw);
    _endpoints = _mapEndpoints(raw);
    return _endpoints;
  }

  Map<String, String> _mapEndpoints(List raw) {
    final map = <String, String>{};
    for (final item in raw) {
      if (item is Map) {
        map[item['name'].toString()] = item['value'].toString();
      }
    }
    return map;
  }

  String endpoint(String name) {
    if (!_endpoints.containsKey(name)) {
      throw ApiException("Endpoint '$name' tidak ada");
    }
    return _endpoints[name]!;
  }

  Future<List<Map<String, dynamic>>> getRoleCategories({bool refresh = false}) async {
    await loadEndpoints(refresh: refresh);
    if (!refresh) {
      final c = await _readCache('category1_roles', hours: 6);
      if (c is List) return c.cast<Map<String, dynamic>>();
    }
    final data = await _get(endpoint('getCategory1'));
    if (data is! List) throw ApiException('Format getCategory1 tidak valid');
    await _writeCache('category1_roles', data);
    return data.cast<Map<String, dynamic>>();
  }

  Future<List<String>> listHeroesByRole(String role, {bool refresh = false}) async {
    await loadEndpoints(refresh: refresh);
    final key = 'heroes_role_${role.toLowerCase()}';
    if (!refresh) {
      final c = await _readCache(key, hours: 6);
      if (c is List) return c.map((e) => e.toString()).toList();
    }
    final raw = await _post(endpoint('getHeroes'), {'category': role});
    final names = <String>[];
    if (raw is Map) {
      names.addAll(raw.keys.map((e) => e.toString()));
      names.sort((a, b) => a.toLowerCase().compareTo(b.toLowerCase()));
    } else if (raw is List) {
      for (final x in raw) {
        if (x is Map) {
          final n = x['heroName'] ?? x['heroname'] ?? x['name'];
          if (n != null) names.add(n.toString());
        }
      }
    }
    await _writeCache(key, names);
    return names;
  }

  Future<Map<String, List<dynamic>>> getHeroGroups({bool refresh = false}) async {
    if (_heroGroups != null && !refresh) return _heroGroups!;
    await loadEndpoints(refresh: refresh);
    if (!refresh) {
      final c = await _readCache('heroes_groups', hours: 6);
      if (c is Map) {
        _heroGroups = c.map((k, v) => MapEntry(k.toString(), List<dynamic>.from(v as List)));
        return _heroGroups!;
      }
    }
    final raw = await _get(endpoint('getHeroes'));
    if (raw is! Map) throw ApiException('Format getHeroes tidak valid');
    _heroGroups = raw.map((k, v) => MapEntry(k.toString(), List<dynamic>.from(v as List)));
    await _writeCache('heroes_groups', raw);
    return _heroGroups!;
  }

  Future<List<String>> listHeroNames({bool refresh = false}) async {
    final groups = await getHeroGroups(refresh: refresh);
    final names = groups.keys.toList();
    names.sort((a, b) => a.toLowerCase().compareTo(b.toLowerCase()));
    return names;
  }

  Future<List<SkinItem>> getSkinsForHero(String heroName, {bool refresh = false}) async {
    final groups = await getHeroGroups(refresh: refresh);
    var entries = groups[heroName];
    if (entries == null) {
      for (final e in groups.entries) {
        if (e.key.toLowerCase() == heroName.toLowerCase()) {
          entries = e.value;
          heroName = e.key;
          break;
        }
      }
    }
    entries ??= [];
    return entries
        .whereType<Map<String, dynamic>>()
        .map((x) => SkinItem.fromHeroEntry(x, hero: heroName))
        .where((s) => s.downloadUrl.isNotEmpty)
        .toList();
  }

  Future<List<Map<String, dynamic>>> getUpgradeMenu({bool refresh = false}) async {
    await loadEndpoints(refresh: refresh);
    if (!refresh) {
      final c = await _readCache('getlistUpgradeSkins', hours: 6);
      if (c is List) return c.cast<Map<String, dynamic>>();
    }
    final data = await _get(endpoint('getlistUpgradeSkins'));
    if (data is! List) throw ApiException('Format upgrade menu tidak valid');
    await _writeCache('getlistUpgradeSkins', data);
    return data.cast<Map<String, dynamic>>();
  }

  Future<List<SkinItem>> getUpgradeSkins(String heroName, {bool refresh = false}) async {
    await loadEndpoints(refresh: refresh);
    final key = 'upgrade_$heroName';
    if (!refresh) {
      final c = await _readCache(key, hours: 1);
      if (c is List) {
        return c
            .whereType<Map<String, dynamic>>()
            .map((x) => SkinItem.fromUpgradeEntry(x, hero: heroName))
            .where((s) => s.downloadUrl.isNotEmpty)
            .toList();
      }
    }
    var raw = await _post(endpoint('getUpgradeSkins'), {'category': heroName});
    if (raw is Map) raw = raw['data'] ?? raw['skins'] ?? [raw];
    if (raw is! List) throw ApiException('Format getUpgradeSkins tidak valid');
    await _writeCache(key, raw);
    return raw
        .whereType<Map<String, dynamic>>()
        .map((x) => SkinItem.fromUpgradeEntry(x, hero: heroName))
        .where((s) => s.downloadUrl.isNotEmpty)
        .toList();
  }

  Future<List<Map<String, dynamic>>> getCustomBundles({bool refresh = false}) async {
    await loadEndpoints(refresh: refresh);
    if (!refresh) {
      final c = await _readCache('custom_bundles', hours: 1);
      if (c is List) return c.cast<Map<String, dynamic>>();
    }
    final raw = await _get(endpoint('getCustomSkins'));
    if (raw is! List) throw ApiException('Format getCustomSkins tidak valid');
    await _writeCache('custom_bundles', raw);
    return raw.cast<Map<String, dynamic>>();
  }

  Future<List<SkinItem>> getCustomBundleSkins(
    String bundleId,
    String bundleName, {
    bool refresh = false,
  }) async {
    await loadEndpoints(refresh: refresh);
    final key = 'custom_bundle_$bundleId';
    if (!refresh) {
      final c = await _readCache(key, hours: 1);
      if (c is List) {
        return c
            .whereType<Map<String, dynamic>>()
            .map((x) => SkinItem.fromBundleEntry(x, bundleName: bundleName))
            .where((s) => s.downloadUrl.isNotEmpty)
            .toList();
      }
    }
    final base = endpoint('getcustomSkinMenu');
    final url = '$base${Uri.encodeComponent(bundleName.isNotEmpty ? bundleName : bundleId)}';
    var raw = await _get(url);
    if (raw is! List) throw ApiException('Format custom bundle tidak valid');
    raw = await enrichCustomMenu(raw.cast<Map<String, dynamic>>());
    await _writeCache(key, raw);
    return raw
        .map((x) => SkinItem.fromBundleEntry(x, bundleName: bundleName))
        .where((s) => s.downloadUrl.isNotEmpty)
        .toList();
  }

  Future<List<Map<String, dynamic>>> enrichCustomMenu(List<Map<String, dynamic>> menu) async {
    if (menu.isEmpty) return [];
    final skinMenuUrl = endpoint('getSkinMenu');
    final enriched = <Map<String, dynamic>>[];
    for (final entry in menu) {
      final hero = entry['heroName']?.toString() ?? '';
      if (hero.isEmpty) continue;
      try {
        var raw = await _post(skinMenuUrl, {'category': hero});
        if (raw is Map) raw = raw['data'] ?? raw['items'] ?? [];
        if (raw is! List) continue;
        final pick = _pickCustomDownload(raw.cast<Map<String, dynamic>>(), hero);
        if (pick == null) continue;
        final merged = {...entry, ...pick};
        if ((merged['url'] ?? merged['downloadLink'] ?? '').toString().isNotEmpty) {
          enriched.add(merged);
        }
      } catch (_) {}
    }
    return enriched;
  }

  Map<String, dynamic>? _pickCustomDownload(List<Map<String, dynamic>> options, String heroName) {
    final heroLow = heroName.toLowerCase();
    final valid = options.where((x) {
      final u = x['url'] ?? x['downloadLink'];
      return u != null && u.toString().isNotEmpty;
    }).toList();
    if (valid.isEmpty) return null;
    for (final x in valid) {
      final name = (x['name'] ?? '').toString().toLowerCase();
      if (name.contains('backup') || name.contains('remove')) continue;
      if (heroLow.contains(name) || name.contains(heroLow)) return x;
    }
    for (final x in valid) {
      final name = (x['name'] ?? '').toString().toLowerCase();
      if (!name.contains('backup') && !name.contains('remove')) return x;
    }
    return valid.first;
  }

  Future<List<SkinItem>> getEffects(String category, {bool refresh = false}) async {
    await loadEndpoints(refresh: refresh);
    final safe = category.replaceAll('/', '_').replaceAll(' ', '_');
    final key = 'effects_$safe';
    if (!refresh) {
      final c = await _readCache(key, hours: 1);
      if (c is List) {
        return c
            .whereType<Map<String, dynamic>>()
            .map(SkinItem.fromEffectEntry)
            .where((s) => s.downloadUrl.isNotEmpty)
            .toList();
      }
    }
    var raw = await _post(endpoint('getEmotes'), {'category': category});
    if (raw is Map) raw = raw['data'] ?? raw['items'] ?? [];
    if (raw is! List) throw ApiException('Format getEmotes tidak valid');
    await _writeCache(key, raw);
    return raw
        .whereType<Map<String, dynamic>>()
        .map(SkinItem.fromEffectEntry)
        .where((s) => s.downloadUrl.isNotEmpty)
        .toList();
  }

  Future<List<Map<String, dynamic>>> getAnnouncements({bool refresh = false}) async {
    await loadEndpoints(refresh: refresh);
    if (!refresh) {
      final c = await _readCache('announcements', hours: 24);
      if (c is List) return c.cast<Map<String, dynamic>>();
    }
    final raw = await _get(endpoint('getAnnouncement'));
    if (raw is! List) return [];
    await _writeCache('announcements', raw);
    return raw.cast<Map<String, dynamic>>();
  }

  Future<List<SkinItem>> searchAll(String query, {int limit = 25}) async {
    final q = query.toLowerCase().trim();
    if (q.isEmpty) return [];
    final results = <SkinItem>[];
    final seen = <String>{};

    void add(SkinItem s) {
      if (s.downloadUrl.isEmpty || seen.contains(s.downloadUrl)) return;
      seen.add(s.downloadUrl);
      results.add(s);
    }

    for (final hero in await listHeroNames()) {
      if (hero.toLowerCase().contains(q)) {
        for (final s in await getSkinsForHero(hero)) {
          add(s);
          if (results.length >= limit) return results;
        }
      }
    }

    for (final entry in await getUpgradeMenu()) {
      final label = (entry['heroName'] ?? entry['name'] ?? '').toString();
      if (label.toLowerCase().contains(q)) {
        for (final s in await getUpgradeSkins(label)) {
          add(s);
          if (results.length >= limit) return results;
        }
      }
    }

    for (final bundle in await getCustomBundles()) {
      final name = (bundle['name'] ?? '').toString();
      if (name.toLowerCase().contains(q)) {
        final skins = await getCustomBundleSkins(
          (bundle['id'] ?? '').toString(),
          name,
        );
        for (final s in skins) {
          add(s);
          if (results.length >= limit) return results;
        }
      }
    }

    for (final (cat, _) in AppConstants.effectCategories) {
      for (final s in await getEffects(cat)) {
        if (s.skinName.toLowerCase().contains(q) || s.category.toLowerCase().contains(q)) {
          add(s);
          if (results.length >= limit) return results;
        }
      }
    }

    return results.take(limit).toList();
  }

  Future<dynamic> _get(String url) async {
    try {
      final r = await _client.get(Uri.parse(url), headers: headers).timeout(const Duration(seconds: 30));
      if (r.statusCode != 200) throw ApiException('GET $url → ${r.statusCode}');
      return jsonDecode(r.body);
    } on ApiException {
      rethrow;
    } catch (e) {
      throw ApiException('GET gagal: $e');
    }
  }

  Future<dynamic> _post(String url, Map<String, String> data) async {
    try {
      final r = await _client
          .post(Uri.parse(url), headers: headers, body: data)
          .timeout(const Duration(seconds: 30));
      if (r.statusCode != 200) throw ApiException('POST $url → ${r.statusCode}');
      return jsonDecode(r.body);
    } on ApiException {
      rethrow;
    } catch (e) {
      throw ApiException('POST gagal: $e');
    }
  }

  Future<File> _cacheDir() async {
    final dir = await getApplicationDocumentsDirectory();
    final cache = Directory('${dir.path}/api_cache');
    if (!await cache.exists()) await cache.create(recursive: true);
    return cache;
  }

  Future<dynamic> _readCache(String key, {required double hours}) async {
    try {
      final file = File('${(await _cacheDir()).path}/$key.json');
      if (!await file.exists()) return null;
      final age = DateTime.now().difference(await file.lastModified()).inMinutes / 60;
      if (age > hours) return null;
      return jsonDecode(await file.readAsString());
    } catch (_) {
      return null;
    }
  }

  Future<void> _writeCache(String key, dynamic data) async {
    try {
      final file = File('${(await _cacheDir()).path}/$key.json');
      await file.writeAsString(jsonEncode(data));
    } catch (_) {}
  }

  void dispose() => _client.close();
}
