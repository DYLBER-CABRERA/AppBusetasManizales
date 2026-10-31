import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:intl/date_symbol_data_local.dart';
import 'package:shared_preferences/shared_preferences.dart';
import 'package:supabase_flutter/supabase_flutter.dart';

import 'app/app.dart';
import 'nucleo/configuracion.dart';
import 'nucleo/notificacion_local.dart';

Future<void> main() async {
  WidgetsFlutterBinding.ensureInitialized();
  await initializeDateFormatting('es');
  final preferencias = await SharedPreferences.getInstance();
  // Supabase solo para Auth; sin URL ni clave la app funciona sin cuenta.
  if (Configuracion.supabaseUrl.isNotEmpty && Configuracion.supabaseAnonKey.isNotEmpty) {
    await Supabase.initialize(
      url: Configuracion.supabaseUrl,
      publishableKey: Configuracion.supabaseAnonKey,
    );
  }
  final notificaciones = await NotificacionLocalReal.inicializar();
  runApp(ProviderScope(
    // Sin reintentos automáticos: cada pantalla ofrece su propio «Reintentar».
    retry: (_, _) => null,
    overrides: [
      preferenciasProvider.overrideWithValue(preferencias),
      notificacionLocalProvider.overrideWithValue(notificaciones),
    ],
    child: const BusetasApp(),
  ));
}
