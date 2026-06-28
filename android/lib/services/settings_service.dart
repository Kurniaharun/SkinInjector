import 'package:flutter/services.dart';
import 'package:shared_preferences/shared_preferences.dart';

import '../core/constants.dart';
import '../models/skin_item.dart';

class SettingsService {
  static const _setupDone = 'setup_done';
  static const _accessMode = 'access_mode';
  static const _package = 'mlbb_package';

  Future<bool> isSetupDone() async {
    final p = await SharedPreferences.getInstance();
    return p.getBool(_setupDone) ?? false;
  }

  Future<void> markSetupDone() async {
    final p = await SharedPreferences.getInstance();
    await p.setBool(_setupDone, true);
  }

  Future<AccessMode> getAccessMode() async {
    final p = await SharedPreferences.getInstance();
    final v = p.getString(_accessMode) ?? 'auto';
    return AccessMode.values.firstWhere(
      (e) => e.name == v,
      orElse: () => AccessMode.auto,
    );
  }

  Future<void> setAccessMode(AccessMode mode) async {
    final p = await SharedPreferences.getInstance();
    await p.setString(_accessMode, mode.name);
  }

  Future<String> getPackage() async {
    final p = await SharedPreferences.getInstance();
    return p.getString(_package) ?? AppConstants.packages.first;
  }

  Future<void> setPackage(String pkg) async {
    final p = await SharedPreferences.getInstance();
    await p.setString(_package, pkg);
  }
}

class InjectPlatform {
  static const _channel = MethodChannel('com.kurrxd.skinject/inject');

  Future<bool> hasRoot() async {
    try {
      return await _channel.invokeMethod<bool>('hasRoot') ?? false;
    } catch (_) {
      return false;
    }
  }

  Future<bool> hasShizuku() async {
    try {
      return await _channel.invokeMethod<bool>('hasShizuku') ?? false;
    } catch (_) {
      return false;
    }
  }

  Future<bool> requestShizukuPermission() async {
    try {
      return await _channel.invokeMethod<bool>('requestShizukuPermission') ?? false;
    } catch (_) {
      return false;
    }
  }

  Future<String?> detectPackage() async {
    try {
      return await _channel.invokeMethod<String>('detectPackage', {
        'packages': AppConstants.packages,
      });
    } catch (_) {
      return null;
    }
  }

  Future<PreflightStatus> preflight({
    required AccessMode mode,
    String? package,
  }) async {
    try {
      final result = await _channel.invokeMapMethod<String, dynamic>('preflight', {
        'mode': mode.name,
        'package': package ?? AppConstants.packages.first,
        'packages': AppConstants.packages,
      });
      if (result == null) {
        return PreflightStatus(
          ok: false,
          mode: mode.name,
          backendName: '',
          package: '',
          assetsPath: '',
          messages: ['Platform channel gagal'],
        );
      }
      return PreflightStatus(
        ok: result['ok'] == true,
        mode: result['mode']?.toString() ?? mode.name,
        backendName: result['backend']?.toString() ?? '',
        package: result['package']?.toString() ?? '',
        assetsPath: result['assetsPath']?.toString() ?? '',
        messages: (result['messages'] as List?)?.map((e) => e.toString()).toList() ?? [],
      );
    } catch (e) {
      return PreflightStatus(
        ok: false,
        mode: mode.name,
        backendName: '',
        package: '',
        assetsPath: '',
        messages: ['Error: $e'],
      );
    }
  }

  Future<Map<String, dynamic>> injectSkin({
    required SkinItem skin,
    required AccessMode mode,
    required String package,
    void Function(String step, double progress)? onProgress,
  }) async {
    try {
      final result = await _channel.invokeMapMethod<String, dynamic>('injectSkin', {
        'downloadUrl': skin.downloadUrl,
        'mode': mode.name,
        'package': package,
        'skinName': skin.label,
      });
      return result ?? {'ok': false, 'message': 'Inject gagal'};
    } on PlatformException catch (e) {
      return {'ok': false, 'message': e.message ?? e.code};
    }
  }
}
