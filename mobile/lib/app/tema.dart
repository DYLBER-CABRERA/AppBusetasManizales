import 'package:flutter/material.dart';
import 'package:google_fonts/google_fonts.dart';

/// Identidad visual de los mockups. El amarillo es solo para busetas en vivo y
/// el rojo ladrillo solo para errores.
class Colores {
  Colores._();

  static const verde = Color(0xFF0E7C66);
  static const amarillo = Color(0xFFF6C500);
  static const tinta = Color(0xFF13271E);
  static const fondo = Color(0xFFEDF1EC);
  static const rojoLadrillo = Color(0xFFB3382C);
  static const rojoLadrilloOscuro = Color(0xFFFF8A7A);
}

ThemeData construirTema(Brightness brillo, {bool fuentesWeb = true}) {
  final oscuro = brillo == Brightness.dark;
  final esquema = ColorScheme.fromSeed(
    seedColor: Colores.verde,
    brightness: brillo,
    primary: oscuro ? const Color(0xFF5FD4B8) : Colores.verde,
    onPrimary: oscuro ? Colores.tinta : Colors.white,
    error: oscuro ? Colores.rojoLadrilloOscuro : Colores.rojoLadrillo,
    surface: oscuro ? const Color(0xFF14211B) : Colors.white,
    onSurface: oscuro ? const Color(0xFFE6EFE9) : Colores.tinta,
  );

  final base = ThemeData(
    useMaterial3: true,
    brightness: brillo,
    colorScheme: esquema,
    scaffoldBackgroundColor: oscuro ? const Color(0xFF0D1814) : Colores.fondo,
    materialTapTargetSize: MaterialTapTargetSize.padded,
  );

  // google_fonts 9 usa su propio TextTheme (material_ui); por eso solo se toma
  // el nombre de la familia, que queda registrada al llamarlo.
  final familiaCuerpo = fuentesWeb ? GoogleFonts.atkinsonHyperlegible().fontFamily : null;
  final familiaTitulo = fuentesWeb ? GoogleFonts.bricolageGrotesque().fontFamily : null;
  var texto = base.textTheme.apply(fontFamily: familiaCuerpo);
  TextStyle? titulo(TextStyle? e) => e?.copyWith(fontFamily: familiaTitulo ?? e.fontFamily);
  texto = texto.copyWith(
    displayLarge: titulo(texto.displayLarge),
    displayMedium: titulo(texto.displayMedium),
    displaySmall: titulo(texto.displaySmall),
    headlineLarge: titulo(texto.headlineLarge),
    headlineMedium: titulo(texto.headlineMedium),
    headlineSmall: titulo(texto.headlineSmall),
    titleLarge: titulo(texto.titleLarge),
  );

  return base.copyWith(
    textTheme: texto,
    appBarTheme: AppBarTheme(
      backgroundColor: esquema.surface,
      foregroundColor: esquema.onSurface,
      elevation: 0,
      scrolledUnderElevation: 0,
      titleTextStyle: texto.titleLarge?.copyWith(
        color: esquema.onSurface,
        fontWeight: FontWeight.w700,
      ),
    ),
    navigationBarTheme: NavigationBarThemeData(
      backgroundColor: esquema.surface,
      indicatorColor: esquema.primary.withValues(alpha: 0.18),
      height: 68,
    ),
    inputDecorationTheme: InputDecorationTheme(
      border: OutlineInputBorder(borderRadius: BorderRadius.circular(12)),
      focusedBorder: OutlineInputBorder(
        borderRadius: BorderRadius.circular(12),
        borderSide: BorderSide(color: esquema.primary, width: 2.5),
      ),
    ),
    filledButtonTheme: FilledButtonThemeData(
      style: FilledButton.styleFrom(minimumSize: const Size(44, 48)),
    ),
    outlinedButtonTheme: OutlinedButtonThemeData(
      style: OutlinedButton.styleFrom(minimumSize: const Size(44, 48)),
    ),
    textButtonTheme: TextButtonThemeData(
      style: TextButton.styleFrom(minimumSize: const Size(44, 44)),
    ),
  );
}
