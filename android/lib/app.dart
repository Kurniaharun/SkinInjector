import 'package:flutter/material.dart';
import 'package:provider/provider.dart';

import 'core/theme.dart';
import 'providers/app_state.dart';
import 'screens/home_screen.dart';

class SkinjectApp extends StatelessWidget {
  const SkinjectApp({super.key});

  @override
  Widget build(BuildContext context) {
    return ChangeNotifierProvider(
      create: (_) => AppState()..init(),
      child: MaterialApp(
        title: 'SkinJECT',
        debugShowCheckedModeBanner: false,
        theme: SkinjectTheme.dark(),
        home: const HomeScreen(),
      ),
    );
  }
}
