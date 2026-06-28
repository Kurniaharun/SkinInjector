import 'package:flutter/material.dart';
import 'package:lucide_icons/lucide_icons.dart';
import 'package:provider/provider.dart';

import '../providers/app_state.dart';
import '../widgets/common_widgets.dart';
import 'home_screen.dart';

class SearchScreen extends StatefulWidget {
  const SearchScreen({super.key});

  @override
  State<SearchScreen> createState() => _SearchScreenState();
}

class _SearchScreenState extends State<SearchScreen> {
  final _controller = TextEditingController();
  var _results = [];
  bool _loading = false;

  Future<void> _search() async {
    final q = _controller.text.trim();
    if (q.isEmpty) return;
    setState(() => _loading = true);
    final results = await context.read<AppState>().api.searchAll(q);
    if (mounted) setState(() { _results = results; _loading = false; });
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(title: const Text('Cari Skin')),
      body: Column(
        children: [
          Padding(
            padding: const EdgeInsets.all(16),
            child: TextField(
              controller: _controller,
              decoration: InputDecoration(
                hintText: 'Hero, skin, recall, upgrade...',
                prefixIcon: const Icon(LucideIcons.search),
                suffixIcon: IconButton(onPressed: _search, icon: const Icon(LucideIcons.arrowRight)),
              ),
              onSubmitted: (_) => _search(),
            ),
          ),
          if (_loading) const LinearProgressIndicator(),
          Expanded(
            child: _results.isEmpty
                ? Center(
                    child: Text(
                      _loading ? 'Mencari...' : 'Ketik kata kunci lalu cari',
                      style: const TextStyle(color: Colors.grey),
                    ),
                  )
                : ListView.builder(
                    padding: const EdgeInsets.symmetric(horizontal: 12),
                    itemCount: _results.length,
                    itemBuilder: (_, i) => SkinListTile(
                      skin: _results[i],
                      onTap: () => openInject(context, _results[i]),
                    ),
                  ),
          ),
        ],
      ),
    );
  }
}
