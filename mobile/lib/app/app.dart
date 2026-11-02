import 'package:flutter/material.dart';
import 'package:flutter_localizations/flutter_localizations.dart';
import 'package:go_router/go_router.dart';

import 'raiz_alertas.dart';
import 'router.dart';
import 'tema.dart';

class BusetasApp extends StatefulWidget {
  const BusetasApp({super.key, this.fuentesWeb = true});

  /// En las pruebas se desactiva para no descargar tipografías.
  final bool fuentesWeb;

  @override
  State<BusetasApp> createState() => _BusetasAppState();
}

class _BusetasAppState extends State<BusetasApp> {
  late final GoRouter _router = construirRouter();

  @override
  void dispose() {
    _router.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    return MaterialApp.router(
      title: 'BusetasApp',
      debugShowCheckedModeBanner: false,
      theme: construirTema(Brightness.light, fuentesWeb: widget.fuentesWeb),
      darkTheme: construirTema(Brightness.dark, fuentesWeb: widget.fuentesWeb),
      themeMode: ThemeMode.system,
      locale: const Locale('es'),
      supportedLocales: const [Locale('es')],
      localizationsDelegates: const [
        GlobalMaterialLocalizations.delegate,
        GlobalWidgetsLocalizations.delegate,
        GlobalCupertinoLocalizations.delegate,
      ],
      routerConfig: _router,
      builder: (context, child) => RaizAlertas(child: child ?? const SizedBox.shrink()),
    );
  }
}
