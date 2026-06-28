import 'package:flutter/material.dart';
import 'package:cached_network_image/cached_network_image.dart';
import 'package:provider/provider.dart';

import '../providers/app_state.dart';
import 'custom_skins_screen.dart';

class CustomBundlesScreen extends StatefulWidget {
  const CustomBundlesScreen({super.key});

  @override
  State<CustomBundlesScreen> createState() => _CustomBundlesScreenState();
}

class _CustomBundlesScreenState extends State<CustomBundlesScreen> {
  var _bundles = <Map<String, dynamic>>[];
  bool _loading = true;

  @override
  void initState() {
    super.initState();
    _load();
  }

  Future<void> _load() async {
    final bundles = await context.read<AppState>().api.getCustomBundles();
    if (mounted) setState(() { _bundles = bundles; _loading = false; });
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(title: const Text('Custom Skin')),
      body: _loading
          ? const Center(child: CircularProgressIndicator())
          : ListView.builder(
              padding: const EdgeInsets.all(12),
              itemCount: _bundles.length,
              itemBuilder: (_, i) {
                final b = _bundles[i];
                final name = (b['name'] ?? '').toString();
                final img = (b['img'] ?? '').toString();
                return Card(
                  margin: const EdgeInsets.only(bottom: 12),
                  clipBehavior: Clip.antiAlias,
                  child: InkWell(
                    onTap: () => Navigator.push(
                      context,
                      MaterialPageRoute(
                        builder: (_) => CustomSkinsScreen(
                          bundleId: (b['id'] ?? '').toString(),
                          bundleName: name,
                        ),
                      ),
                    ),
                    child: img.isNotEmpty
                        ? Stack(
                            children: [
                              CachedNetworkImage(imageUrl: img, height: 100, width: double.infinity, fit: BoxFit.cover),
                              Positioned(
                                left: 16,
                                bottom: 12,
                                child: Text(name, style: const TextStyle(color: Colors.white, fontWeight: FontWeight.bold, fontSize: 18, shadows: [Shadow(blurRadius: 8)])),
                              ),
                            ],
                          )
                        : ListTile(title: Text(name), trailing: const Icon(Icons.chevron_right)),
                  ),
                );
              },
            ),
    );
  }
}
