import 'package:flutter/material.dart';
import 'package:lucide_icons/lucide_icons.dart';
import 'package:provider/provider.dart';

import '../core/constants.dart';
import '../core/theme.dart';
import '../models/skin_item.dart';
import '../providers/app_state.dart';
import '../widgets/common_widgets.dart';
import 'custom_bundles_screen.dart';
import 'effects_menu_screen.dart';
import 'hero_skins_screen.dart';
import 'inject_screen.dart';
import 'role_heroes_screen.dart';
import 'search_screen.dart';
import 'settings_screen.dart';
import 'upgrade_menu_screen.dart';

class HomeScreen extends StatefulWidget {
  const HomeScreen({super.key});

  @override
  State<HomeScreen> createState() => _HomeScreenState();
}

class _HomeScreenState extends State<HomeScreen> {
  @override
  void initState() {
    super.initState();
    WidgetsBinding.instance.addPostFrameCallback((_) {
      final state = context.read<AppState>();
      if (!state.setupDone) {
        showDialog<void>(
          context: context,
          barrierDismissible: false,
          builder: (_) => SetupGate(
            onSetup: () {
              Navigator.pop(context);
              Navigator.push(context, MaterialPageRoute(builder: (_) => const SettingsScreen(firstSetup: true)));
            },
          ),
        );
      }
    });
  }

  @override
  Widget build(BuildContext context) {
    final state = context.watch<AppState>();

    return Scaffold(
      body: SafeArea(
        child: state.loading
            ? const Center(child: CircularProgressIndicator())
            : RefreshIndicator(
                onRefresh: () => state.init(),
                child: CustomScrollView(
                  slivers: [
                    SliverToBoxAdapter(child: _buildHeader(context, state)),
                    SliverToBoxAdapter(child: SectionHeader(title: 'Pilih Hero')),
                    SliverToBoxAdapter(child: _buildRoles(context, state)),
                    SliverToBoxAdapter(child: SectionHeader(title: 'Kategori Lain')),
                    SliverToBoxAdapter(child: _buildFeatures(context)),
                    const SliverToBoxAdapter(child: SizedBox(height: 24)),
                  ],
                ),
              ),
      ),
      floatingActionButton: FloatingActionButton.extended(
        onPressed: () => Navigator.push(context, MaterialPageRoute(builder: (_) => const SearchScreen())),
        icon: const Icon(LucideIcons.search),
        label: const Text('Cari Skin'),
        backgroundColor: SkinjectTheme.primaryLight,
      ),
    );
  }

  Widget _buildHeader(BuildContext context, AppState state) {
    return Container(
      margin: const EdgeInsets.all(16),
      padding: const EdgeInsets.all(20),
      decoration: SkinjectTheme.heroGradient.copyWith(
        borderRadius: BorderRadius.circular(24),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Row(
            children: [
              Container(
                padding: const EdgeInsets.all(10),
                decoration: BoxDecoration(
                  color: Colors.white.withValues(alpha: 0.15),
                  borderRadius: BorderRadius.circular(14),
                ),
                child: const Icon(LucideIcons.zap, color: Colors.white, size: 28),
              ),
              const SizedBox(width: 14),
              Expanded(
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Text(
                      AppConstants.appName,
                      style: const TextStyle(color: Colors.white, fontSize: 24, fontWeight: FontWeight.bold),
                    ),
                    Text(
                      'MLBB Skin Injector · ${AppConstants.author}',
                      style: TextStyle(color: Colors.white.withValues(alpha: 0.85), fontSize: 13),
                    ),
                  ],
                ),
              ),
              IconButton(
                onPressed: () => Navigator.push(context, MaterialPageRoute(builder: (_) => const SettingsScreen())),
                icon: const Icon(LucideIcons.settings, color: Colors.white),
              ),
            ],
          ),
          const SizedBox(height: 16),
          Text(
            'Versi ${AppConstants.version}',
            style: TextStyle(color: Colors.white.withValues(alpha: 0.7), fontSize: 12),
          ),
          const SizedBox(height: 12),
          _statusChip(state),
        ],
      ),
    );
  }

  Widget _statusChip(AppState state) {
    final ok = state.preflight?.ok ?? false;
    return InkWell(
      onTap: () => Navigator.push(context, MaterialPageRoute(builder: (_) => const SettingsScreen())),
      borderRadius: BorderRadius.circular(999),
      child: Container(
        padding: const EdgeInsets.symmetric(horizontal: 14, vertical: 8),
        decoration: BoxDecoration(
          color: ok ? SkinjectTheme.success.withValues(alpha: 0.2) : SkinjectTheme.warning.withValues(alpha: 0.2),
          borderRadius: BorderRadius.circular(999),
          border: Border.all(color: ok ? SkinjectTheme.success : SkinjectTheme.warning),
        ),
        child: Row(
          mainAxisSize: MainAxisSize.min,
          children: [
            Icon(ok ? LucideIcons.checkCircle2 : LucideIcons.alertCircle, size: 16, color: ok ? SkinjectTheme.success : SkinjectTheme.warning),
            const SizedBox(width: 8),
            Text(
              ok ? 'Akses ${state.preflight?.backendName ?? "OK"}' : 'Atur Permission',
              style: TextStyle(color: ok ? SkinjectTheme.success : SkinjectTheme.warning, fontWeight: FontWeight.w600, fontSize: 13),
            ),
          ],
        ),
      ),
    );
  }

  Widget _buildRoles(BuildContext context, AppState state) {
    final roles = state.roleCategories.isNotEmpty
        ? state.roleCategories
        : AppConstants.heroRoles.map((r) => {'name': r}).toList();

    return SizedBox(
      height: 110,
      child: ListView.builder(
        scrollDirection: Axis.horizontal,
        padding: const EdgeInsets.symmetric(horizontal: 16),
        itemCount: roles.length,
        itemBuilder: (_, i) {
          final role = roles[i]['name']?.toString() ?? '';
          return RoleChip(
            label: role,
            icon: RoleChip.iconForRole(role),
            imageUrl: roles[i]['img']?.toString(),
            onTap: () => Navigator.push(
              context,
              MaterialPageRoute(builder: (_) => RoleHeroesScreen(role: role)),
            ),
          );
        },
      ),
    );
  }

  Widget _buildFeatures(BuildContext context) {
    return Padding(
      padding: const EdgeInsets.symmetric(horizontal: 16),
      child: Column(
        children: [
          FeatureTile(
            title: 'UPGRADE SKIN',
            subtitle: 'Semua skin upgrade dari API resmi',
            icon: LucideIcons.arrowUpCircle,
            onTap: () => Navigator.push(context, MaterialPageRoute(builder: (_) => const UpgradeMenuScreen())),
          ),
          FeatureTile(
            title: 'CUSTOM SKIN',
            subtitle: 'Koleksi bundle custom (Naruto, dll)',
            icon: LucideIcons.palette,
            onTap: () => Navigator.push(context, MaterialPageRoute(builder: (_) => const CustomBundlesScreen())),
          ),
          FeatureTile(
            title: 'EFFECT & RECALL',
            subtitle: 'Recall · Emote · Trail · Respawn',
            icon: LucideIcons.sparkles,
            onTap: () => Navigator.push(context, MaterialPageRoute(builder: (_) => const EffectsMenuScreen())),
          ),
          FeatureTile(
            title: 'BROWSE ALL HERO',
            subtitle: 'Daftar lengkap ~130 hero',
            icon: LucideIcons.users,
            onTap: () => _browseAllHeroes(context),
          ),
        ],
      ),
    );
  }

  Future<void> _browseAllHeroes(BuildContext context) async {
    final api = context.read<AppState>().api;
    final heroes = await api.listHeroNames();
    if (!context.mounted) return;
    await Navigator.push(
      context,
      MaterialPageRoute(
        builder: (_) => _HeroPickerScreen(heroes: heroes),
      ),
    );
  }
}

class _HeroPickerScreen extends StatelessWidget {
  const _HeroPickerScreen({required this.heroes});
  final List<String> heroes;

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(title: const Text('Semua Hero')),
      body: ListView.builder(
        itemCount: heroes.length,
        itemBuilder: (_, i) => ListTile(
          leading: CircleAvatar(
            backgroundColor: SkinjectTheme.cardLight,
            child: Text(heroes[i][0], style: const TextStyle(fontWeight: FontWeight.bold)),
          ),
          title: Text(heroes[i]),
          trailing: const Icon(LucideIcons.chevronRight),
          onTap: () => Navigator.push(
            context,
            MaterialPageRoute(builder: (_) => HeroSkinsScreen(heroName: heroes[i])),
          ),
        ),
      ),
    );
  }
}

void openInject(BuildContext context, SkinItem skin) {
  Navigator.push(context, MaterialPageRoute(builder: (_) => InjectScreen(skin: skin)));
}
