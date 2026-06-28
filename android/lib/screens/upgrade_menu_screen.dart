import 'package:flutter/material.dart';
import 'package:cached_network_image/cached_network_image.dart';
import 'package:provider/provider.dart';

import '../providers/app_state.dart';
import 'upgrade_skins_screen.dart';

class UpgradeMenuScreen extends StatefulWidget {
  const UpgradeMenuScreen({super.key});

  @override
  State<UpgradeMenuScreen> createState() => _UpgradeMenuScreenState();
}

class _UpgradeMenuScreenState extends State<UpgradeMenuScreen> {
  var _menu = <Map<String, dynamic>>[];
  bool _loading = true;

  @override
  void initState() {
    super.initState();
    _load();
  }

  Future<void> _load() async {
    final menu = await context.read<AppState>().api.getUpgradeMenu();
    if (mounted) setState(() { _menu = menu; _loading = false; });
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(title: const Text('Upgrade Skin')),
      body: _loading
          ? const Center(child: CircularProgressIndicator())
          : ListView.builder(
              padding: const EdgeInsets.all(12),
              itemCount: _menu.length,
              itemBuilder: (_, i) {
                final e = _menu[i];
                final name = (e['heroName'] ?? e['name'] ?? '').toString();
                final img = (e['img'] ?? '').toString();
                return Card(
                  child: ListTile(
                    leading: ClipRRect(
                      borderRadius: BorderRadius.circular(8),
                      child: img.isNotEmpty
                          ? CachedNetworkImage(imageUrl: img, width: 48, height: 48, fit: BoxFit.cover)
                          : const Icon(Icons.star),
                    ),
                    title: Text(name),
                    trailing: const Icon(Icons.chevron_right),
                    onTap: () => Navigator.push(
                      context,
                      MaterialPageRoute(builder: (_) => UpgradeSkinsScreen(entry: e)),
                    ),
                  ),
                );
              },
            ),
    );
  }
}
