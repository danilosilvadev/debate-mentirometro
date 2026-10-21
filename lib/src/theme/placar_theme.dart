import 'package:flutter/material.dart';

/// Cores do visor da urna, copiadas do placar web.
class PlacarColors {
  const PlacarColors._();

  static const fundo = Color(0xFFE4E6E3);
  static const tela = Color(0xFFFBFBF8);
  static const tinta = Color(0xFF1B1D1C);
  static const apagado = Color(0xFF5E625F);
  static const borda = Color(0xFFB9BDB8);
  static const verdadeiro = Color(0xFF1D8A4A);
  static const impreciso = Color(0xFFE07B14);
  static const falso = Color(0xFFC62828);
  static const proposta = Color(0xFF2457A6);
  static const ataque = Color(0xFFB5367A);
  static const defesa = Color(0xFF8A8F8B);
  static const balanco = Color(0xFFC9CCC8);
  static const aviso = Color(0xFFFFF6E8);
}

class PlacarType {
  const PlacarType._();

  static const _family = 'Archivo';

  static TextStyle title(double size) {
    return TextStyle(
      fontFamily: _family,
      fontSize: size,
      height: 1,
      color: PlacarColors.tinta,
      fontVariations: const [
        FontVariation('wght', 900),
        FontVariation('wdth', 62),
      ],
    );
  }

  static TextStyle heading(double size) {
    return TextStyle(
      fontFamily: _family,
      fontSize: size,
      height: 1.05,
      letterSpacing: -0.2,
      color: PlacarColors.tinta,
      fontVariations: const [
        FontVariation('wght', 800),
        FontVariation('wdth', 75),
      ],
    );
  }

  static TextStyle body([double size = 16]) {
    return TextStyle(
      fontFamily: _family,
      fontSize: size,
      height: 1.45,
      color: PlacarColors.tinta,
      fontVariations: const [
        FontVariation('wght', 400),
        FontVariation('wdth', 100),
      ],
    );
  }

  static TextStyle strong([double size = 16]) {
    return body(size).copyWith(
      fontVariations: const [
        FontVariation('wght', 800),
        FontVariation('wdth', 100),
      ],
    );
  }

  static TextStyle muted([double size = 14]) {
    return body(size).copyWith(color: PlacarColors.apagado, height: 1.4);
  }
}

ThemeData placarTheme() {
  final base = PlacarType.body();
  return ThemeData(
    useMaterial3: true,
    fontFamily: 'Archivo',
    scaffoldBackgroundColor: PlacarColors.fundo,
    colorScheme: const ColorScheme.light(
      primary: PlacarColors.tinta,
      onPrimary: Colors.white,
      secondary: PlacarColors.proposta,
      onSecondary: Colors.white,
      surface: PlacarColors.tela,
      onSurface: PlacarColors.tinta,
    ),
    textTheme: TextTheme(
      bodyMedium: base,
      bodyLarge: PlacarType.body(18),
      titleLarge: PlacarType.title(32),
    ),
    appBarTheme: const AppBarTheme(
      backgroundColor: PlacarColors.fundo,
      foregroundColor: PlacarColors.tinta,
      elevation: 0,
      scrolledUnderElevation: 0,
    ),
    splashColor: PlacarColors.tinta.withValues(alpha: 0.06),
    highlightColor: PlacarColors.tinta.withValues(alpha: 0.04),
  );
}
