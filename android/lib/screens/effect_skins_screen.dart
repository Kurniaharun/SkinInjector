import 'package:flutter/material.dart';
import 'package:provider/provider.dart';

import '../providers/app_state.dart';
import '../widgets/common_widgets.dart';
import 'home_screen.dart';

class EffectSkinsScreen extends StatefulWidget {
  const EffectSkinsScreen({super.key, required this.category});

  final String category;

  @override
  State<EffectSkinsScreen> createState() => _EffectSkinsScreenState();
}

class _EffectSkinsScreenState extends State<EffectSkinsScreen> {
  var _skins = [];
  bool _loading = true;

  @override
  void initState() {
    super.initState();
    _load();
  }

  Future<void> _load() async {
    final skins = await context.read<AppState>().api.getEffects(widget.category);
    if (mounted) setState(() { _skins = skins; _loading = false; });
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(title: Text(widget.category)),
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
