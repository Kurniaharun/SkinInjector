import 'package:flutter/material.dart';
import 'package:provider/provider.dart';

import '../providers/app_state.dart';
import '../widgets/common_widgets.dart';
import 'home_screen.dart';

class CustomSkinsScreen extends StatefulWidget {
  const CustomSkinsScreen({super.key, required this.bundleId, required this.bundleName});

  final String bundleId;
  final String bundleName;

  @override
  State<CustomSkinsScreen> createState() => _CustomSkinsScreenState();
}

class _CustomSkinsScreenState extends State<CustomSkinsScreen> {
  var _skins = [];
  bool _loading = true;
  String? _error;

  @override
  void initState() {
    super.initState();
    _load();
  }

  Future<void> _load() async {
    try {
      final skins = await context.read<AppState>().api.getCustomBundleSkins(
            widget.bundleId,
            widget.bundleName,
          );
      if (mounted) setState(() { _skins = skins; _loading = false; });
    } catch (e) {
      if (mounted) setState(() { _error = e.toString(); _loading = false; });
    }
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(title: Text(widget.bundleName)),
      body: _loading
          ? const Center(child: CircularProgressIndicator())
          : _error != null
              ? Center(child: Text(_error!))
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
