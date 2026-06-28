import 'package:flutter/foundation.dart';

import '../core/constants.dart';
import '../models/skin_item.dart';
import 'api_service.dart';
import 'settings_service.dart';

class AppState extends ChangeNotifier {
  AppState({
    ApiService? api,
    SettingsService? settings,
    InjectPlatform? platform,
  })  : _api = api ?? ApiService(),
        _settings = settings ?? SettingsService(),
        _platform = platform ?? InjectPlatform();

  final ApiService _api;
  final SettingsService _settings;
  final InjectPlatform _platform;

  bool setupDone = false;
  bool loading = false;
  String? error;
  AccessMode accessMode = AccessMode.auto;
  String mlbbPackage = AppConstants.packages.first;
  PreflightStatus? preflight;
  bool hasRoot = false;
  bool hasShizuku = false;
  List<Map<String, dynamic>> announcements = [];
  List<Map<String, dynamic>> roleCategories = [];

  Future<void> init() async {
    loading = true;
    notifyListeners();
    try {
      setupDone = await _settings.isSetupDone();
      accessMode = await _settings.getAccessMode();
      mlbbPackage = await _settings.getPackage();
      hasRoot = await _platform.hasRoot();
      hasShizuku = await _platform.hasShizuku();
      if (setupDone) {
        await _refreshPreflight();
      }
      await _api.loadEndpoints();
      announcements = await _api.getAnnouncements();
      roleCategories = await _api.getRoleCategories();
    } catch (e) {
      error = e.toString();
    } finally {
      loading = false;
      notifyListeners();
    }
  }

  Future<void> completeSetup({
    required AccessMode mode,
    required String package,
  }) async {
    accessMode = mode;
    mlbbPackage = package;
    await _settings.setAccessMode(mode);
    await _settings.setPackage(package);
    await _settings.markSetupDone();
    setupDone = true;
    if (mode == AccessMode.shizuku) {
      await _platform.requestShizukuPermission();
    }
    hasRoot = await _platform.hasRoot();
    hasShizuku = await _platform.hasShizuku();
    await _refreshPreflight();
    notifyListeners();
  }

  Future<void> _refreshPreflight() async {
    preflight = await _platform.preflight(mode: accessMode, package: mlbbPackage);
  }

  Future<void> refreshPermissions() async {
    hasRoot = await _platform.hasRoot();
    hasShizuku = await _platform.hasShizuku();
    await _refreshPreflight();
    notifyListeners();
  }

  Future<String?> autoDetectPackage() async {
    final pkg = await _platform.detectPackage();
    if (pkg != null && pkg.isNotEmpty) {
      mlbbPackage = pkg;
      notifyListeners();
    }
    return pkg;
  }

  Future<Map<String, dynamic>> inject(SkinItem skin) async {
    return _platform.injectSkin(
      skin: skin,
      mode: accessMode,
      package: mlbbPackage,
    );
  }

  ApiService get api => _api;
  InjectPlatform get platform => _platform;

  @override
  void dispose() {
    _api.dispose();
    super.dispose();
  }
}
