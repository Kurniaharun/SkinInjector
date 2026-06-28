import 'package:flutter/material.dart';
import 'package:lucide_icons/lucide_icons.dart';

import '../core/constants.dart';
import '../core/theme.dart';
import 'effect_skins_screen.dart';

class EffectsMenuScreen extends StatelessWidget {
  const EffectsMenuScreen({super.key});

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(title: const Text('Effect & Recall')),
      body: ListView(
        padding: const EdgeInsets.all(16),
        children: AppConstants.effectCategories.map((cat) {
          final (name, key) = cat;
          return Card(
            child: ListTile(
              leading: Icon(_iconFor(key), color: SkinjectTheme.accent),
              title: Text(name),
              trailing: const Icon(LucideIcons.chevronRight),
              onTap: () => Navigator.push(
                context,
                MaterialPageRoute(builder: (_) => EffectSkinsScreen(category: name)),
              ),
            ),
          );
        }).toList(),
      ),
    );
  }

  IconData _iconFor(String key) => switch (key) {
        'recall' => LucideIcons.rotateCcw,
        'emote' => LucideIcons.smile,
        'trail' => LucideIcons.wind,
        'respawn' => LucideIcons.refreshCw,
        'painted' => LucideIcons.paintbrush,
        'eliminated' => LucideIcons.skull,
        _ => LucideIcons.sparkles,
      };
}
