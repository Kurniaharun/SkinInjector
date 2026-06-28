import 'package:flutter/material.dart';
import 'package:lucide_icons/lucide_icons.dart';
import 'package:provider/provider.dart';

import '../core/theme.dart';
import '../models/skin_item.dart';
import '../providers/app_state.dart';

class InjectScreen extends StatefulWidget {
  const InjectScreen({super.key, required this.skin});

  final SkinItem skin;

  @override
  State<InjectScreen> createState() => _InjectScreenState();
}

class _InjectScreenState extends State<InjectScreen> {
  bool _injecting = false;
  String _status = '';
  double _progress = 0;

  Future<void> _confirmInject() async {
    final ok = await showDialog<bool>(
      context: context,
      builder: (ctx) => AlertDialog(
        title: const Row(
          children: [
            Icon(LucideIcons.syringe, color: SkinjectTheme.accent),
            SizedBox(width: 10),
            Text('Konfirmasi Inject'),
          ],
        ),
        content: Column(
          mainAxisSize: MainAxisSize.min,
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Text('Skin: ${widget.skin.label}', style: const TextStyle(fontWeight: FontWeight.bold)),
            Text('Hero: ${widget.skin.heroName}'),
            const SizedBox(height: 12),
            const Text(
              'Pastikan Mobile Legends sudah ditutup sebelum inject. '
              'Proses akan download ZIP dan extract ke folder assets game.',
              style: TextStyle(color: SkinjectTheme.textMuted, fontSize: 13),
            ),
          ],
        ),
        actions: [
          TextButton(onPressed: () => Navigator.pop(ctx, false), child: const Text('Batal')),
          ElevatedButton(onPressed: () => Navigator.pop(ctx, true), child: const Text('Inject')),
        ],
      ),
    );
    if (ok != true || !mounted) return;

    setState(() {
      _injecting = true;
      _status = 'Memulai inject...';
      _progress = 0.1;
    });

    final state = context.read<AppState>();
    if (!state.setupDone || !(state.preflight?.ok ?? false)) {
      setState(() {
        _injecting = false;
        _status = 'Setup belum selesai — buka Pengaturan dulu';
      });
      return;
    }

    setState(() { _status = 'Download & inject via ${state.accessMode.label}...'; _progress = 0.4; });

    final result = await state.inject(widget.skin);

    if (!mounted) return;
    setState(() {
      _injecting = false;
      _progress = result['ok'] == true ? 1.0 : 0;
      _status = result['message']?.toString() ?? (result['ok'] == true ? 'Berhasil!' : 'Gagal');
    });
  }

  @override
  Widget build(BuildContext context) {
    final skin = widget.skin;
    return Scaffold(
      appBar: AppBar(title: const Text('Inject Skin')),
      body: Padding(
        padding: const EdgeInsets.all(20),
        child: Column(
          children: [
            ClipRRect(
              borderRadius: BorderRadius.circular(20),
              child: Image.network(
                skin.imageUrl,
                height: 200,
                width: double.infinity,
                fit: BoxFit.cover,
                errorBuilder: (_, __, ___) => Container(
                  height: 200,
                  color: SkinjectTheme.cardLight,
                  child: const Icon(LucideIcons.image, size: 48),
                ),
              ),
            ),
            const SizedBox(height: 20),
            Text(skin.label, style: Theme.of(context).textTheme.headlineSmall?.copyWith(fontWeight: FontWeight.bold)),
            Text('${skin.heroName} · ${skin.source}', style: const TextStyle(color: SkinjectTheme.textMuted)),
            const Spacer(),
            if (_injecting) ...[
              LinearProgressIndicator(value: _progress > 0 ? _progress : null),
              const SizedBox(height: 12),
              Text(_status, textAlign: TextAlign.center),
            ] else if (_status.isNotEmpty) ...[
              Icon(
                _progress == 1.0 ? LucideIcons.checkCircle2 : LucideIcons.xCircle,
                color: _progress == 1.0 ? SkinjectTheme.success : SkinjectTheme.danger,
                size: 48,
              ),
              const SizedBox(height: 8),
              Text(_status, textAlign: TextAlign.center),
            ],
            const Spacer(),
            SizedBox(
              width: double.infinity,
              child: ElevatedButton.icon(
                onPressed: _injecting ? null : _confirmInject,
                icon: const Icon(LucideIcons.syringe),
                label: const Text('Inject Skin'),
              ),
            ),
          ],
        ),
      ),
    );
  }
}
