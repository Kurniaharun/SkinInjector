import 'package:flutter/material.dart';

class SkinjectTheme {
  static const primary = Color(0xFF6B21A8);
  static const primaryDark = Color(0xFF4C1D95);
  static const primaryLight = Color(0xFF9333EA);
  static const accent = Color(0xFF22D3EE);
  static const surface = Color(0xFF1E1033);
  static const card = Color(0xFF2D1B4E);
  static const cardLight = Color(0xFF3B2667);
  static const textPrimary = Color(0xFFF8FAFC);
  static const textMuted = Color(0xFFCBD5E1);
  static const success = Color(0xFF22C55E);
  static const warning = Color(0xFFF59E0B);
  static const danger = Color(0xFFEF4444);

  static ThemeData dark() {
    const scheme = ColorScheme.dark(
      primary: primaryLight,
      secondary: accent,
      surface: surface,
      onPrimary: Colors.white,
      onSurface: textPrimary,
    );
    return ThemeData(
      useMaterial3: true,
      brightness: Brightness.dark,
      colorScheme: scheme,
      scaffoldBackgroundColor: surface,
      fontFamily: 'Roboto',
      appBarTheme: const AppBarTheme(
        backgroundColor: Colors.transparent,
        elevation: 0,
        centerTitle: true,
        foregroundColor: textPrimary,
      ),
      cardTheme: CardThemeData(
        color: card,
        elevation: 0,
        shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(16)),
      ),
      dialogTheme: DialogThemeData(
        backgroundColor: card,
        shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(20)),
      ),
      snackBarTheme: SnackBarThemeData(
        behavior: SnackBarBehavior.floating,
        backgroundColor: cardLight,
      ),
      elevatedButtonTheme: ElevatedButtonThemeData(
        style: ElevatedButton.styleFrom(
          backgroundColor: primaryLight,
          foregroundColor: Colors.white,
          padding: const EdgeInsets.symmetric(horizontal: 24, vertical: 14),
          shape: RoundedRectangleBorder(
            borderRadius: BorderRadius.circular(14),
          ),
        ),
      ),
      inputDecorationTheme: InputDecorationTheme(
        filled: true,
        fillColor: cardLight,
        border: OutlineInputBorder(
          borderRadius: BorderRadius.circular(14),
          borderSide: BorderSide.none,
        ),
        hintStyle: const TextStyle(color: textMuted),
      ),
    );
  }

  static BoxDecoration heroGradient = const BoxDecoration(
    gradient: LinearGradient(
      begin: Alignment.topLeft,
      end: Alignment.bottomRight,
      colors: [primaryDark, primary, Color(0xFF7C3AED)],
    ),
  );

  static BoxDecoration cardGradient = BoxDecoration(
    gradient: LinearGradient(
      begin: Alignment.topLeft,
      end: Alignment.bottomRight,
      colors: [card, cardLight.withValues(alpha: 0.9)],
    ),
    borderRadius: BorderRadius.circular(18),
    border: Border.all(color: primaryLight.withValues(alpha: 0.25)),
  );
}
