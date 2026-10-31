import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:intl/date_symbol_data_local.dart';
import 'package:latlong2/latlong.dart';

import 'package:busetas_app/caracteristicas/viajar/dominio/viaje.dart';
import 'package:busetas_app/caracteristicas/viajar/presentacion/pantalla_viajar.dart';

import 'ayudas/api_falsa.dart';
import 'ayudas/datos_ejemplo.dart';
import 'ayudas/montaje.dart';

const _manizales = LatLng(5.0689, -75.5174);

Map<String, dynamic> _paradero(String id, String nombre, double distanciaM) => {
      'paraderoId': id,
      'nombre': nombre,
      'lat': 5.07,
      'lng': -75.51,
      'distanciaM': distanciaM,
    };

Map<String, dynamic> _opcion({
  String servicioId = 's1',
  double caminata = 4.2,
  double espera = 6,
  double bus = 12,
}) =>
    {
      'tipo': 'directa',
      'rutaId': idCable,
      'servicioId': servicioId,
      'paraderoOrigen': _paradero('p1', 'Paradero Fundadores', 336),
      'paraderoDestino': _paradero('p2', 'Paradero Catedral', 120),
      'caminataMin': caminata,
      'esperaMin': espera,
      'busMin': bus,
      'totalMin': caminata + espera + bus,
    };

Map<String, RespuestaFalsa> _base([Map<String, RespuestaFalsa>? extra]) => {
      '/rutas': RespuestaFalsa([resumenCable]),
      '/busqueda/hitos': RespuestaFalsa([hitoCatedral()]),
      ...?extra,
    };

Future<void> _elegirAtajo(WidgetTester tester, String campo, String atajo) async {
  await tester.tap(find.text(campo));
  await tester.pumpAndSettle();
  await tester.tap(find.widgetWithText(ActionChip, atajo));
  await tester.pumpAndSettle();
}

Future<void> _elegirMiUbicacion(WidgetTester tester, String campo) async {
  await tester.tap(find.text(campo));
  await tester.pumpAndSettle();
  await tester.tap(find.text('Mi ubicación').last);
  await tester.pumpAndSettle();
}

void main() {
  setUpAll(() => initializeDateFormatting('es'));

  group('modelos', () {
    test('Lugar manda exactamente una forma: coordenadas o hitoId', () {
      expect(const LugarViaje.miUbicacion(_manizales).aJson(), {'lat': 5.0689, 'lng': -75.5174});
      expect(const LugarViaje.enMapa(_manizales).aJson(), {'lat': 5.0689, 'lng': -75.5174});
      expect(const LugarViaje.hito(id: 'h1', nombre: 'Catedral').aJson(), {'hitoId': 'h1'});
    });

    test('minutos: se redondean y nunca prometen 0 min', () {
      expect(minutosViaje(21.6), '22 min');
      expect(minutosViaje(0.2), '1 min');
      expect(minutosViaje(0), '1 min');
    });

    test('la respuesta lee opciones, motivo y paradero más cercano', () {
      final r = RespuestaPlanificacion.desdeJson({
        'opciones': <Object>[],
        'motivo': 'No hay paraderos a menos de 600 m del destino.',
        'paraderoMasCercano': _paradero('p9', 'Paradero Lejano', 1450),
      });
      expect(r.opciones, isEmpty);
      expect(r.motivo, startsWith('No hay paraderos'));
      expect(r.paraderoMasCercano!.distanciaM, 1450);
      expect(
        RespuestaPlanificacion.desdeJson({'opciones': [_opcion()]}).opciones.single.totalMin,
        closeTo(22.2, 0.001),
      );
    });
  });

  group('pantalla Viajar', () {
    testWidgets('sin lugares explica qué hacer y no deja buscar', (tester) async {
      await montar(tester, pantalla: () => const PantallaViajar(), respuestas: _base());
      await tester.pumpAndSettle();

      expect(find.text('Planifica tu viaje'), findsOneWidget);
      expect(find.textContaining('Solo mostramos rutas directas'), findsOneWidget);
      expect(tester.widget<FilledButton>(find.widgetWithText(FilledButton, 'Buscar rutas')).onPressed, isNull);
    });

    testWidgets('Mi ubicación → hito: manda el Lugar correcto y muestra la opción con su barra de tramos',
        (tester) async {
      final adaptador = await montar(
        tester,
        pantalla: () => const PantallaViajar(),
        ubicacion: _manizales,
        respuestas: _base({
          'POST /viajes/planificar': RespuestaFalsa({
            'opciones': [_opcion(), _opcion(servicioId: 's2', espera: 9)],
            'motivo': null,
            'paraderoMasCercano': null,
          }),
        }),
      );
      await tester.pumpAndSettle();

      await _elegirMiUbicacion(tester, 'Elige el origen');
      await _elegirAtajo(tester, 'Elige el destino', 'Catedral');
      expect(find.text('Mi ubicación'), findsOneWidget);
      expect(find.text('Catedral'), findsOneWidget);

      await tester.tap(find.widgetWithText(FilledButton, 'Buscar rutas'));
      await tester.pumpAndSettle();

      final llamada = adaptador.de('POST', '/viajes/planificar').single;
      expect(llamada.cuerpo, {
        'origen': {'lat': 5.0689, 'lng': -75.5174},
        'destino': {'hitoId': 'h1'},
      });

      expect(find.text('Directa · El Cable'), findsNWidgets(2));
      expect(find.text('22 min'), findsOneWidget);
      expect(find.text('4 a pie'), findsNWidgets(2));
      expect(find.text('6 espera'), findsOneWidget);
      expect(find.text('12 bus'), findsNWidgets(2));
      expect(find.text('Camina 336 m hasta Paradero Fundadores'), findsNWidgets(2));
      expect(find.text('Toma Sideral y baja en Paradero Catedral'), findsOneWidget);
      expect(find.text('Toma la buseta y baja en Paradero Catedral'), findsOneWidget,
          reason: 'un servicio que la ruta ya no lista no rompe la tarjeta');
      expect(find.byType(Semantics), findsWidgets);
    });

    testWidgets('sin opciones muestra el motivo y el paradero más cercano', (tester) async {
      await montar(
        tester,
        pantalla: () => const PantallaViajar(),
        ubicacion: _manizales,
        respuestas: _base({
          'POST /viajes/planificar': RespuestaFalsa({
            'opciones': <Object>[],
            'motivo': 'No hay paraderos a menos de 600 m del destino.',
            'paraderoMasCercano': _paradero('p9', 'Paradero Lejano', 1450),
          }),
        }),
      );
      await tester.pumpAndSettle();
      await _elegirMiUbicacion(tester, 'Elige el origen');
      await _elegirAtajo(tester, 'Elige el destino', 'Catedral');
      await tester.tap(find.widgetWithText(FilledButton, 'Buscar rutas'));
      await tester.pumpAndSettle();

      expect(find.text('No encontramos una ruta directa'), findsOneWidget);
      expect(find.textContaining('No hay paraderos a menos de 600 m del destino.'), findsOneWidget);
      expect(find.textContaining('El paradero más cercano es Paradero Lejano, a 1,5 km.'), findsOneWidget);
    });

    testWidgets('sin viaje directo sugiere las rutas que pasan junto al origen y su paradero', (tester) async {
      final adaptador = await montar(
        tester,
        pantalla: () => const PantallaViajar(),
        ubicacion: _manizales,
        respuestas: _base({
          'POST /viajes/planificar': const RespuestaFalsa({
            'opciones': <Object>[],
            'motivo': 'No hay una ruta directa entre esos paraderos en este horario.',
            'paraderoMasCercano': null,
          }),
          '/rutas/cercanas': RespuestaFalsa({
            'rutas': [rutaResumen(idCable, 'El Cable', [servicio('Sideral', '39')], distanciaM: 27)],
            'paraderoMasCercano': null,
          }),
          '/paraderos/cercanos': RespuestaFalsa([_paradero('p7', 'Paradero El Cable 2', 653)]),
        }),
      );
      await tester.pumpAndSettle();
      await _elegirMiUbicacion(tester, 'Elige el origen');
      await _elegirAtajo(tester, 'Elige el destino', 'Catedral');
      await tester.tap(find.widgetWithText(FilledButton, 'Buscar rutas'));
      await tester.pumpAndSettle();

      expect(find.textContaining('No hay una ruta directa entre esos paraderos'), findsOneWidget);
      expect(find.textContaining('solo se sube y se baja en paraderos'), findsOneWidget);
      expect(find.text('Rutas que pasan cerca de tu origen'), findsOneWidget);
      expect(
        find.text('Pasa a 27 m de ti. Su paradero más cercano es Paradero El Cable 2, a 653 m.'),
        findsOneWidget,
      );
      expect(find.text('¿Cuándo llega?'), findsOneWidget);
      final consulta = adaptador.peticiones.firstWhere((u) => u.path.endsWith('/paraderos/cercanos'));
      expect(consulta.queryParameters['rutaId'], idCable);
      expect(consulta.queryParameters['lat'], '5.0689');
    });

    testWidgets('si la sugerencia falla, igual se muestra la respuesta principal', (tester) async {
      await montar(
        tester,
        pantalla: () => const PantallaViajar(),
        ubicacion: _manizales,
        respuestas: _base({
          'POST /viajes/planificar': const RespuestaFalsa({
            'opciones': <Object>[],
            'motivo': 'No hay una ruta directa entre esos paraderos en este horario.',
            'paraderoMasCercano': null,
          }),
          '/rutas/cercanas': errorFalso(503, 'SERVICIO_EXTERNO_NO_DISPONIBLE', 'Sin base de datos.'),
        }),
      );
      await tester.pumpAndSettle();
      await _elegirMiUbicacion(tester, 'Elige el origen');
      await _elegirAtajo(tester, 'Elige el destino', 'Catedral');
      await tester.tap(find.widgetWithText(FilledButton, 'Buscar rutas'));
      await tester.pumpAndSettle();

      expect(find.text('No encontramos una ruta directa'), findsOneWidget);
      expect(find.text('Rutas que pasan cerca de tu origen'), findsNothing);
    });

    testWidgets('error de conexión: banner con Reintentar que se recupera', (tester) async {
      final respuestas = _base({
        'POST /viajes/planificar':
            errorFalso(503, 'SERVICIO_EXTERNO_NO_DISPONIBLE', 'Base de datos no disponible.'),
      });
      await montar(
        tester,
        pantalla: () => const PantallaViajar(),
        ubicacion: _manizales,
        respuestas: respuestas,
      );
      await tester.pumpAndSettle();
      await _elegirMiUbicacion(tester, 'Elige el origen');
      await _elegirAtajo(tester, 'Elige el destino', 'Catedral');
      await tester.tap(find.widgetWithText(FilledButton, 'Buscar rutas'));
      await tester.pumpAndSettle();
      expect(find.text('Base de datos no disponible.'), findsOneWidget);

      respuestas['POST /viajes/planificar'] =
          RespuestaFalsa({'opciones': [_opcion()], 'motivo': null, 'paraderoMasCercano': null});
      await tester.tap(find.text('Reintentar'));
      await tester.pumpAndSettle();
      expect(find.text('Directa · El Cable'), findsOneWidget);
      expect(find.text('Base de datos no disponible.'), findsNothing);
    });

    testWidgets('origen y destino iguales: avisa y no busca', (tester) async {
      final adaptador = await montar(tester, pantalla: () => const PantallaViajar(), respuestas: _base());
      await tester.pumpAndSettle();
      await _elegirAtajo(tester, 'Elige el origen', 'Catedral');
      await _elegirAtajo(tester, 'Elige el destino', 'Catedral');

      expect(find.text('El origen y el destino son el mismo lugar. Elige uno distinto.'), findsOneWidget);
      expect(tester.widget<FilledButton>(find.widgetWithText(FilledButton, 'Buscar rutas')).onPressed, isNull);
      expect(adaptador.de('POST', '/viajes/planificar'), isEmpty);
    });

    testWidgets('sin permiso de ubicación, Mi ubicación no se puede elegir y se explica', (tester) async {
      await montar(tester, pantalla: () => const PantallaViajar(), respuestas: _base());
      await tester.pumpAndSettle();
      await tester.tap(find.text('Elige el origen'));
      await tester.pumpAndSettle();

      expect(find.textContaining('No tenemos tu ubicación'), findsOneWidget);
      await tester.tap(find.text('Mi ubicación'));
      await tester.pumpAndSettle();
      expect(find.text('Origen'), findsWidgets, reason: 'la hoja sigue abierta');
      expect(find.textContaining('No tenemos tu ubicación'), findsOneWidget);
    });

    testWidgets('buscar un lugar por texto y elegirlo', (tester) async {
      await montar(tester, pantalla: () => const PantallaViajar(), respuestas: _base());
      await tester.pumpAndSettle();
      await tester.tap(find.text('Elige el destino'));
      await tester.pumpAndSettle();

      await tester.enterText(find.byType(TextField), 'catedral');
      await tester.pump(const Duration(milliseconds: 400));
      await tester.pumpAndSettle();
      await tester.tap(find.widgetWithText(ListTile, 'Catedral'));
      await tester.pumpAndSettle();

      expect(find.text('Elige el destino'), findsNothing);
      expect(find.text('Catedral'), findsOneWidget);
    });

    testWidgets('intercambiar cambia origen y destino', (tester) async {
      await montar(
        tester,
        pantalla: () => const PantallaViajar(),
        ubicacion: _manizales,
        respuestas: _base(),
      );
      await tester.pumpAndSettle();
      await _elegirMiUbicacion(tester, 'Elige el origen');
      await _elegirAtajo(tester, 'Elige el destino', 'Catedral');

      await tester.tap(find.byTooltip('Intercambiar origen y destino'));
      await tester.pumpAndSettle();

      expect(find.bySemanticsLabel('Origen: Catedral'), findsOneWidget);
      expect(find.bySemanticsLabel('Destino: Mi ubicación'), findsOneWidget);
    });
  });
}
