import 'package:flutter/material.dart';
import 'package:lucide_icons/lucide_icons.dart';

import '../core/constants.dart';
import '../core/theme.dart';
import '../models/skin_item.dart';

class SetupGate extends StatelessWidget {
  const SetupGate({super.key, required this.onSetup});

  final VoidCallback onSetup;

  @override
  Widget build(BuildContext context) {
    return Dialog(
      insetPadding: const EdgeInsets.symmetric(horizontal: 20, vertical: 24),
      child: Padding(
        padding: const EdgeInsets.all(24),
        child: Column(
          mainAxisSize: MainAxisSize.min,
          children: [
            Container(
              width: 64,
              height: 64,
              decoration: BoxDecoration(
                color: SkinjectTheme.primaryLight.withValues(alpha: 0.2),
                shape: BoxShape.circle,
              ),
              child: const Icon(LucideIcons.shieldAlert, color: SkinjectTheme.warning, size: 32),
            ),
            const SizedBox(height: 20),
            Text(
              'Pengaturan Diperlukan',
              style: Theme.of(context).textTheme.titleLarge?.copyWith(
                    fontWeight: FontWeight.bold,
                    color: SkinjectTheme.textPrimary,
                  ),
              textAlign: TextAlign.center,
            ),
            const SizedBox(height: 12),
            const Text(
              'Sebelum memakai aplikasi, harap setting aplikasi terlebih dahulu.\n\n'
              'SkinJECT membutuhkan akses Root atau Shizuku untuk inject skin ke folder Mobile Legends.',
              style: TextStyle(color: SkinjectTheme.textMuted, height: 1.5),
              textAlign: TextAlign.center,
            ),
            const SizedBox(height: 8),
            _bullet(LucideIcons.smartphone, 'Deteksi package MLBB'),
            _bullet(LucideIcons.keyRound, 'Pilih mode: Auto / Root / Shizuku'),
            _bullet(LucideIcons.folderLock, 'Verifikasi path assets game'),
            const SizedBox(height: 24),
            SizedBox(
              width: double.infinity,
              child: ElevatedButton.icon(
                onPressed: onSetup,
                icon: const Icon(LucideIcons.settings),
                label: const Text('Buka Pengaturan'),
              ),
            ),
          ],
        ),
      ),
    );
  }

  Widget _bullet(IconData icon, String text) {
    return Padding(
      padding: const EdgeInsets.symmetric(vertical: 4),
      child: Row(
        children: [
          Icon(icon, size: 18, color: SkinjectTheme.accent),
          const SizedBox(width: 10),
          Expanded(child: Text(text, style: const TextStyle(color: SkinjectTheme.textMuted, fontSize: 13))),
        ],
      ),
    );
  }
}

class SectionHeader extends StatelessWidget {
  const SectionHeader({super.key, required this.title});

  final String title;

  @override
  Widget build(BuildContext context) {
    return Padding(
      padding: const EdgeInsets.symmetric(vertical: 12),
      child: Row(
        children: [
          Expanded(child: Divider(color: SkinjectTheme.primaryLight.withValues(alpha: 0.3))),
          Padding(
            padding: const EdgeInsets.symmetric(horizontal: 12),
            child: Text(
              title,
              style: const TextStyle(
                color: SkinjectTheme.textPrimary,
                fontWeight: FontWeight.w600,
                letterSpacing: 0.5,
              ),
            ),
          ),
          Expanded(child: Divider(color: SkinjectTheme.primaryLight.withValues(alpha: 0.3))),
        ],
      ),
    );
  }
}

class RoleChip extends StatelessWidget {
  const RoleChip({
    super.key,
    required this.label,
    required this.icon,
    required this.onTap,
    this.imageUrl,
  });

  final String label;
  final IconData icon;
  final VoidCallback onTap;
  final String? imageUrl;

  @override
  Widget build(BuildContext context) {
    return GestureDetector(
      onTap: onTap,
      child: Container(
        width: 88,
        margin: const EdgeInsets.only(right: 12),
        child: Column(
          children: [
            Container(
              width: 72,
              height: 72,
              decoration: BoxDecoration(
                gradient: const LinearGradient(
                  colors: [SkinjectTheme.primary, SkinjectTheme.primaryLight],
                ),
                borderRadius: BorderRadius.circular(18),
                boxShadow: [
                  BoxShadow(
                    color: SkinjectTheme.primaryLight.withValues(alpha: 0.35),
                    blurRadius: 12,
                    offset: const Offset(0, 4),
                  ),
                ],
              ),
              child: imageUrl != null && imageUrl!.isNotEmpty
                  ? ClipRRect(
                      borderRadius: BorderRadius.circular(18),
                      child: Image.network(imageUrl!, fit: BoxFit.cover, errorBuilder: (_, __, ___) => Icon(icon, color: Colors.white)),
                    )
                  : Icon(icon, color: Colors.white, size: 28),
            ),
            const SizedBox(height: 8),
            Text(
              label,
              style: const TextStyle(color: SkinjectTheme.textPrimary, fontSize: 12, fontWeight: FontWeight.w500),
              textAlign: TextAlign.center,
              maxLines: 1,
              overflow: TextOverflow.ellipsis,
            ),
          ],
        ),
      ),
    );
  }

  static IconData iconForRole(String role) {
    return switch (role.toLowerCase()) {
      'assassin' => LucideIcons.sword,
      'fighter' => LucideIcons.swords,
      'tank' => LucideIcons.shield,
      'support' => LucideIcons.heartPulse,
      'mage' => LucideIcons.sparkles,
      'marksman' => LucideIcons.crosshair,
      _ => LucideIcons.user,
    };
  }
}

class FeatureTile extends StatelessWidget {
  const FeatureTile({
    super.key,
    required this.title,
    required this.subtitle,
    required this.icon,
    required this.onTap,
    this.imageUrl,
  });

  final String title;
  final String subtitle;
  final IconData icon;
  final VoidCallback onTap;
  final String? imageUrl;

  @override
  Widget build(BuildContext context) {
    return Padding(
      padding: const EdgeInsets.only(bottom: 12),
      child: Material(
        color: Colors.transparent,
        child: InkWell(
          onTap: onTap,
          borderRadius: BorderRadius.circular(18),
          child: Ink(
            decoration: SkinjectTheme.cardGradient,
            padding: const EdgeInsets.all(14),
            child: Row(
              children: [
                Container(
                  width: 56,
                  height: 56,
                  decoration: BoxDecoration(
                    borderRadius: BorderRadius.circular(14),
                    color: SkinjectTheme.primaryDark,
                  ),
                  child: imageUrl != null && imageUrl!.isNotEmpty
                      ? ClipRRect(
                          borderRadius: BorderRadius.circular(14),
                          child: Image.network(imageUrl!, fit: BoxFit.cover),
                        )
                      : Icon(icon, color: Colors.white),
                ),
                const SizedBox(width: 14),
                Expanded(
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      Text(title, style: const TextStyle(color: Colors.white, fontWeight: FontWeight.bold, fontSize: 16)),
                      const SizedBox(height: 4),
                      Text(subtitle, style: const TextStyle(color: SkinjectTheme.textMuted, fontSize: 12)),
                    ],
                  ),
                ),
                const Icon(LucideIcons.chevronRight, color: SkinjectTheme.accent),
              ],
            ),
          ),
        ),
      ),
    );
  }
}

class SkinListTile extends StatelessWidget {
  const SkinListTile({super.key, required this.skin, required this.onTap});

  final SkinItem skin;
  final VoidCallback onTap;

  @override
  Widget build(BuildContext context) {
    return Card(
      margin: const EdgeInsets.only(bottom: 10),
      child: ListTile(
        onTap: onTap,
        leading: ClipRRect(
          borderRadius: BorderRadius.circular(10),
          child: Image.network(
            skin.imageUrl,
            width: 52,
            height: 52,
            fit: BoxFit.cover,
            errorBuilder: (_, __, ___) => Container(
              width: 52,
              height: 52,
              color: SkinjectTheme.cardLight,
              child: const Icon(LucideIcons.image),
            ),
          ),
        ),
        title: Text(skin.label, style: const TextStyle(fontWeight: FontWeight.w600)),
        subtitle: Text('${skin.subtitle} · ${skin.source}'),
        trailing: const Icon(LucideIcons.syringe, color: SkinjectTheme.accent),
      ),
    );
  }
}
