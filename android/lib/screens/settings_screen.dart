import 'package:flutter/material.dart';
import 'package:lucide_icons/lucide_icons.dart';
import 'package:provider/provider.dart';
import 'package:url_launcher/url_launcher.dart';

import '../core/constants.dart';
import '../core/theme.dart';
import '../providers/app_state.dart';

class SettingsScreen extends StatefulWidget {
  const SettingsScreen({super.key, this.firstSetup = false});

  final bool firstSetup;

  @override
  State<SettingsScreen> createState() => _SettingsScreenState();
}

class _SettingsScreenState extends State<SettingsScreen> {
  AccessMode _mode = AccessMode.auto;
  String _package = AppConstants.packages.first;
  bool _saving = false;

  @override
  void initState() {
    super.initState();
    final state = context.read<AppState>();
    _mode = state.accessMode;
    _package = state.mlbbPackage;
  }

  Future<void> _save() async {
    setState(() => _saving = true);
    final state = context.read<AppState>();
    await state.completeSetup(mode: _mode, package: _package);
    if (!mounted) return;
    setState(() => _saving = false);
    if (widget.firstSetup) {
      Navigator.popUntil(context, (r) => r.isFirst);
    } else {
      Navigator.pop(context);
    }
    ScaffoldMessenger.of(context).showSnackBar(
      const SnackBar(content: Text('Pengaturan disimpan')),
    );
  }

  @override
  Widget build(BuildContext context) {
    final state = context.watch<AppState>();

    return Scaffold(
      appBar: AppBar(
        title: Text(widget.firstSetup ? 'Setup Awal' : 'Pengaturan'),
        leading: widget.firstSetup ? null : const BackButton(),
      ),
      body: ListView(
        padding: const EdgeInsets.all(16),
        children: [
          if (widget.firstSetup) ...[
            Container(
              padding: const EdgeInsets.all(16),
              decoration: BoxDecoration(
                color: SkinjectTheme.warning.withValues(alpha: 0.15),
                borderRadius: BorderRadius.circular(16),
                border: Border.all(color: SkinjectTheme.warning.withValues(alpha: 0.5)),
              ),
              child: const Row(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Icon(LucideIcons.info, color: SkinjectTheme.warning),
                  SizedBox(width: 12),
                  Expanded(
                    child: Text(
                      'Sebelum memakai aplikasi, harap setting aplikasi terlebih dahulu. '
                      'Pilih mode akses dan pastikan Mobile Legends terinstall.',
                      style: TextStyle(color: SkinjectTheme.textMuted, height: 1.4),
                    ),
                  ),
                ],
              ),
            ),
            const SizedBox(height: 20),
          ],
          _sectionTitle('Mode Akses Storage'),
          ...AccessMode.values.map((m) => RadioListTile<AccessMode>(
                value: m,
                groupValue: _mode,
                onChanged: (v) => setState(() => _mode = v!),
                title: Text(m.label),
                subtitle: Text(m.description, style: const TextStyle(fontSize: 12)),
                secondary: Icon(_modeIcon(m)),
              )),
          const SizedBox(height: 8),
          _statusRow('Root', state.hasRoot, LucideIcons.terminal),
          _statusRow('Shizuku', state.hasShizuku, LucideIcons.shield),
          TextButton.icon(
            onPressed: () => state.refreshPermissions(),
            icon: const Icon(LucideIcons.refreshCw),
            label: const Text('Refresh deteksi'),
          ),
          if (_mode == AccessMode.shizuku && !state.hasShizuku) ...[
            OutlinedButton.icon(
              onPressed: () async {
                await state.platform.requestShizukuPermission();
                await state.refreshPermissions();
              },
              icon: const Icon(LucideIcons.externalLink),
              label: const Text('Minta izin Shizuku'),
            ),
            TextButton(
              onPressed: () => launchUrl(Uri.parse('https://shizuku.rikka.app/')),
              child: const Text('Install / buka Shizuku'),
            ),
          ],
          const SizedBox(height: 16),
          _sectionTitle('Package Mobile Legends'),
          ...AppConstants.packages.map((pkg) => RadioListTile<String>(
                value: pkg,
                groupValue: _package,
                onChanged: (v) => setState(() => _package = v!),
                title: Text(pkg, style: const TextStyle(fontSize: 13)),
                dense: true,
              )),
          TextButton.icon(
            onPressed: () async {
              final pkg = await state.autoDetectPackage();
              if (pkg != null) setState(() => _package = pkg);
            },
            icon: const Icon(LucideIcons.scanSearch),
            label: const Text('Auto-detect package terinstall'),
          ),
          if (state.preflight != null) ...[
            const SizedBox(height: 16),
            _sectionTitle('Status Preflight'),
            Card(
              child: Padding(
                padding: const EdgeInsets.all(16),
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Text('Backend: ${state.preflight!.backendName.isEmpty ? "-" : state.preflight!.backendName}'),
                    Text('Package: ${state.preflight!.package}'),
                    Text('Path: ${state.preflight!.assetsPath}', style: const TextStyle(fontSize: 11)),
                    const SizedBox(height: 8),
                    ...state.preflight!.messages.map((m) => Text('• $m', style: const TextStyle(fontSize: 12, color: SkinjectTheme.textMuted))),
                  ],
                ),
              ),
            ),
          ],
          const SizedBox(height: 24),
          SizedBox(
            width: double.infinity,
            child: ElevatedButton.icon(
              onPressed: _saving ? null : _save,
              icon: _saving
                  ? const SizedBox(width: 18, height: 18, child: CircularProgressIndicator(strokeWidth: 2, color: Colors.white))
                  : const Icon(LucideIcons.check),
              label: Text(widget.firstSetup ? 'Simpan & Mulai' : 'Simpan Pengaturan'),
            ),
          ),
        ],
      ),
    );
  }

  Widget _sectionTitle(String t) => Padding(
        padding: const EdgeInsets.only(bottom: 8),
        child: Text(t, style: const TextStyle(fontWeight: FontWeight.bold, fontSize: 16)),
      );

  Widget _statusRow(String label, bool ok, IconData icon) {
    return ListTile(
      dense: true,
      leading: Icon(icon, color: ok ? SkinjectTheme.success : SkinjectTheme.textMuted),
      title: Text(label),
      trailing: Icon(ok ? LucideIcons.checkCircle2 : LucideIcons.xCircle, color: ok ? SkinjectTheme.success : SkinjectTheme.danger),
    );
  }

  IconData _modeIcon(AccessMode m) => switch (m) {
        AccessMode.auto => LucideIcons.wand2,
        AccessMode.root => LucideIcons.terminal,
        AccessMode.shizuku => LucideIcons.shield,
      };
}
