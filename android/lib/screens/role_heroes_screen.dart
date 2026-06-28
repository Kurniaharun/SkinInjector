import 'package:flutter/material.dart';
import 'package:provider/provider.dart';

import '../providers/app_state.dart';
import 'hero_skins_screen.dart';

class RoleHeroesScreen extends StatefulWidget {
  const RoleHeroesScreen({super.key, required this.role});

  final String role;

  @override
  State<RoleHeroesScreen> createState() => _RoleHeroesScreenState();
}

class _RoleHeroesScreenState extends State<RoleHeroesScreen> {
  List<String> _heroes = [];
  bool _loading = true;

  @override
  void initState() {
    super.initState();
    _load();
  }

  Future<void> _load() async {
    final api = context.read<AppState>().api;
    final heroes = await api.listHeroesByRole(widget.role);
    if (mounted) setState(() { _heroes = heroes; _loading = false; });
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(title: Text('Hero · ${widget.role}')),
      body: _loading
          ? const Center(child: CircularProgressIndicator())
          : ListView.builder(
              padding: const EdgeInsets.all(12),
              itemCount: _heroes.length,
              itemBuilder: (_, i) => Card(
                child: ListTile(
                  title: Text(_heroes[i]),
                  trailing: const Icon(Icons.chevron_right),
                  onTap: () => Navigator.push(
                    context,
                    MaterialPageRoute(builder: (_) => HeroSkinsScreen(heroName: _heroes[i])),
                  ),
                ),
              ),
            ),
    );
  }
}
