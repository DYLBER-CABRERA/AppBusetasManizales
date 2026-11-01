import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:go_router/go_router.dart';
import 'package:latlong2/latlong.dart';
import 'package:shared_preferences/shared_preferences.dart';

import 'package:busetas_app/app/raiz_alertas.dart';
import 'package:busetas_app/app/tema.dart';
import 'package:busetas_app/caracteristicas/eta/presentacion/pantalla_eta.dart';
import 'package:busetas_app/caracteristicas/ruta/presentacion/pantalla_ruta.dart';
import 'package:busetas_app/nucleo/auth.dart';
import 'package:busetas_app/nucleo/cliente_api.dart';
import 'package:busetas_app/nucleo/configuracion.dart';
import 'package:busetas_app/nucleo/conexion_ws.dart';
import 'package:busetas_app/nucleo/notificacion_local.dart';
import 'package:busetas_app/nucleo/reloj.dart';
import 'package:busetas_app/nucleo/ubicacion.dart';

import 'api_falsa.dart';
import 'auth_falso.dart';
import 'canal_falso.dart';
import 'ubicacion_nula.dart';

/// Tiempos largos: ningún temporizador del tiempo real se dispara durante una prueba de pantalla.
const tiemposLargos = TiemposTiempoReal(
  intervaloRefresco: Duration(hours: 1),
  esperasReconexion: [Duration(hours: 1)],
  latido: Duration(hours: 1),
);

/// Monta una pantalla con la API falsa, sin ubicación y con WebSocket que no conecta
/// (salvo que se pase [fabrica]). Incluye las rutas de la ficha y del ETA.
Future<AdaptadorFalso> montar(
  WidgetTester tester, {
  required Map<String, RespuestaFalsa> respuestas,
  required Widget Function() pantalla,
  String inicial = '/',
  FabricaCanalesFalsa? fabrica,
  DateTime Function()? reloj,
  AuthFalso? auth,
  NotificacionLocalFalsa? locales,
  LatLng? ubicacion,
}) async {
  // Pantalla alta: la ficha lleva cabecera, mini mapa y pestañas antes de la lista.
  tester.view.physicalSize = const Size(800, 1600);
  tester.view.devicePixelRatio = 1.0;
  addTearDown(tester.view.reset);

  SharedPreferences.setMockInitialValues({});
  final preferencias = await SharedPreferences.getInstance();
  final adaptador = AdaptadorFalso(respuestas);
  final canales = fabrica ?? FabricaCanalesFalsa();
  final autenticacion = auth ?? AuthFalso();
  final router = GoRouter(initialLocation: inicial, routes: [
    GoRoute(path: '/', builder: (_, _) => Scaffold(body: pantalla())),
    GoRoute(path: '/ruta/:id', builder: (_, e) => PantallaRuta(rutaId: e.pathParameters['id']!)),
    GoRoute(
      path: '/ruta/:rutaId/paradero/:paraderoId',
      builder: (_, e) => PantallaEta(
        rutaId: e.pathParameters['rutaId']!,
        paraderoId: e.pathParameters['paraderoId']!,
      ),
    ),
    GoRoute(path: '/mapa', builder: (_, _) => const Scaffold(body: Text('mapa'))),
    GoRoute(path: '/buscar', builder: (_, _) => const Scaffold(body: Text('buscar'))),
  ]);
  await tester.pumpWidget(ProviderScope(
    retry: (_, _) => null,
    overrides: [
      preferenciasProvider.overrideWithValue(preferencias),
      authProvider.overrideWithValue(autenticacion),
      notificacionLocalProvider.overrideWithValue(locales ?? NotificacionLocalFalsa()),
      clienteApiProvider.overrideWithValue(
        crearApiFalsa(adaptador, tokenActual: () => autenticacion.token),
      ),
      ubicacionProvider.overrideWith(
        ubicacion == null ? UbicacionNula.new : () => UbicacionFija(ubicacion),
      ),
      fabricaCanalProvider.overrideWithValue(canales.crear),
      tiemposTiempoRealProvider.overrideWithValue(tiemposLargos),
      if (reloj != null) relojProvider.overrideWithValue(reloj),
    ],
    child: MaterialApp.router(
      theme: construirTema(Brightness.light, fuentesWeb: false),
      routerConfig: router,
      builder: (context, child) => RaizAlertas(child: child ?? const SizedBox.shrink()),
    ),
  ));
  return adaptador;
}
