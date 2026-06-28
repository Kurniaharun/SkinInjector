import 'package:flutter/material.dart';
import 'package:provider/provider.dart';

import '../providers/app_state.dart';
import '../widgets/common_widgets.dart';
import 'home_screen.dart';

class UpgradeSkinsScreen extends StatefulWidget {
  const UpgradeSkinsScreen({super.key, required this.entry});

  final Map<String, dynamic> entry;

  @override
  State<UpgradeSkinsScreen> createState() => _UpgradeSkinsScreenState();
}

class _UpgradeSkinsScreenState extends State<UpgradeSkinsScreen> {
  var _skins = [];
  bool _loading = true;

  @override
  void initState() {
    super.initState();
    _load();
  }

  Future<void> _load() async {
    final category = (widget.entry['heroName'] ?? widget.entry['name'] ?? '').toString();
    final skins = await context.read<AppState>().api.getUpgradeSkins(category);
    if (mounted) setState(() { _skins = skins; _loading = false; });
  }

  @override
  Widget build(BuildContext context) {
    final title = (widget.entry['heroName'] ?? widget.entry['name'] ?? 'Upgrade').toString();
    return Scaffold(
      appBar: AppBar(title: Text(title)),
      body: _loading
          ? const Center(child: CircularProgressIndicator())
          : ListView.builder(
              padding: const EdgeInsets.all(12),
              itemCount: _skins.length,
              itemBuilder: (_, i) => SkinListTile(
                skin: _skins[i],
                onTap: () => openInject(context, _skins[i]),
              ),
            ),
    );
  }
}
