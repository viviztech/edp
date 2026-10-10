import 'package:flutter/material.dart';

/// Mirrors packages/design-tokens/tokens.json for the Material 3 app shell.
abstract final class EdpColors {
  static const ink = Color(0xFF012154);
  static const background = Color(0xFFF6F8FC);
  static const accent = Color(0xFF195DA4);
  static const line = Color(0xFFC8D5E7);
  static const highlight = Color(0xFF195DA4);
  static const paper = Colors.white;
}

abstract final class EdpTheme {
  static ThemeData light() {
    final scheme =
        ColorScheme.fromSeed(
          seedColor: EdpColors.accent,
          brightness: Brightness.light,
        ).copyWith(
          primary: EdpColors.accent,
          tertiary: EdpColors.highlight,
          onPrimary: EdpColors.paper,
          surface: EdpColors.paper,
          onSurface: EdpColors.ink,
          outline: EdpColors.line,
        );
    final base = ThemeData(
      useMaterial3: true,
      colorScheme: scheme,
      scaffoldBackgroundColor: EdpColors.background,
      appBarTheme: const AppBarTheme(
        backgroundColor: EdpColors.background,
        foregroundColor: EdpColors.ink,
        centerTitle: false,
      ),
      inputDecorationTheme: InputDecorationTheme(
        filled: true,
        fillColor: EdpColors.paper,
        border: OutlineInputBorder(
          borderSide: const BorderSide(color: EdpColors.line),
          borderRadius: BorderRadius.circular(4),
        ),
      ),
    );
    const fallback = ['NotoSansTamil'];
    return base.copyWith(
      textTheme: base.textTheme.apply(fontFamilyFallback: fallback),
      primaryTextTheme: base.primaryTextTheme.apply(
        fontFamilyFallback: fallback,
      ),
    );
  }
}
