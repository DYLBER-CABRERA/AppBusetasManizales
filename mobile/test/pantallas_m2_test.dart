import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';

import 'ayudas/api_falsa.dart';
import 'ayudas/canal_falso.dart';
import 'ayudas/datos_ejemplo.dart';
import 'ayudas/montaje.dart';

/// 23:00 en Bogotá (04:00 UTC del día siguiente): fuera del horario 04:45–21:30.
DateTime _veintitresBogota() => DateTime.utc(2026, 10, 30, 4, 0);

Map<String, RespuestaFalsa> _ficha(Map<String, dynamic> busetas) => {
      '/rutas/$idCable': RespuestaFalsa(detalleCable()),
      '/rutas/$idCable/horarios': RespuestaFalsa(horariosCable()),
      '/rutas/$idCable/frecuencias': RespuestaFalsa(frecuenciasCable()),
      '/rutas/$idCable/busetas': RespuestaFalsa(busetas),
    };

Future<void> _abrirEnVivo(
  WidgetTester tester,
  Map<String, dynamic> busetas, {
  DateTime Function()? reloj,
  FabricaCanalesFalsa? fabrica,
}) async {
  await montar(
    tester,
    pantalla: () => const SizedBox(),
    respuestas: _ficha(busetas),
    inicial: '/ruta/$idCable',
    reloj: reloj,
    // Con un canal que conecta: si no, «Reconectando…» anima sin fin y pumpAndSettle no termina.
    fabrica: fabrica ?? FabricaCanalesFalsa([CanalFalso()]),
  );
  await tester.pumpAndSettle();
  await tester.tap(find.text('En vivo'));
  await tester.pumpAndSettle();
}

void main() {
  group('Ficha · En vivo', () {
    testWidgets('lista las busetas con su estado y la antigüedad del reporte', (tester) async {
      await _abrirEnVivo(
        tester,
        busetasJson([
          busetaJson('b1', '1544'),
          busetaJson('b2', '1520', estado: 'sin_senal'),
        ]),
        reloj: () => DateTime.parse('2026-10-29T10:00:05-05:00'),
      );

      expect(find.text('2 en servicio'), findsOneWidget);
      expect(find.text('Sideral · En ruta'), findsOneWidget);
      expect(find.text('Reportó hace 5 s · 33 km/h'), findsOneWidget);
      expect(find.text('Sideral · Sin señal'), findsOneWidget);
      expect(
        find.text('Ubicación no disponible. Última señal hace más de 60 s.'),
        findsOneWidget,
      );
      // El número lateral aparece en el marcador del mini mapa y en la lista.
      expect(find.text('1544'), findsWidgets);
    });

    testWidgets('sin busetas fuera de horario dice que el servicio ya cerró', (tester) async {
      await _abrirEnVivo(tester, busetasJson([]), reloj: _veintitresBogota);

      expect(find.text('No hay busetas en servicio en esta ruta en este momento.'), findsOneWidget);
      expect(find.text('El servicio de esta ruta ya cerró.'), findsOneWidget);
    });

    testWidgets('sin busetas antes de abrir dice a qué hora sale', (tester) async {
      await _abrirEnVivo(
        tester,
        busetasJson([]),
        reloj: () => DateTime.utc(2026, 10, 29, 8, 0), // 03:00 en Bogotá
      );

      expect(
        find.text('El servicio de esta ruta aún no inicia; sale a las 04:45.'),
        findsOneWidget,
      );
    });

    testWidgets('con unidades pero sin GPS explica que no hay ubicación', (tester) async {
      await _abrirEnVivo(
        tester,
        busetasJson([], unidades: 2),
        reloj: () => DateTime.utc(2026, 10, 29, 17, 0), // 12:00 en Bogotá
      );

      expect(find.text('Esta ruta no tiene ubicación de busetas en este momento.'), findsOneWidget);
      expect(
        find.text('Hay 2 en servicio, pero sin GPS. Consulta el horario y la frecuencia.'),
        findsOneWidget,
      );
    });

    testWidgets('un mensaje del WebSocket agrega busetas a la lista', (tester) async {
      final canal = CanalFalso();
      await _abrirEnVivo(
        tester,
        busetasJson([busetaJson('b1', '1544')]),
        fabrica: FabricaCanalesFalsa([canal]),
        reloj: () => DateTime.parse('2026-10-29T10:00:05-05:00'),
      );
      expect(find.text('1 en servicio'), findsOneWidget);

      canal.servidorEnvia({
        'tipo': 'posiciones',
        'rutaId': idCable,
        'calculadoEn': '2026-10-29T10:00:03-05:00',
        'busetas': [busetaJson('b9', '1388', lat: 5.062)],
      });
      await tester.pump();
      await tester.pump(const Duration(milliseconds: 1100)); // termina la animación de marcadores

      expect(find.text('2 en servicio'), findsOneWidget);
      expect(find.text('1388'), findsWidgets);
    });
  });

  group('ETA de una parada', () {
    Future<Map<String, RespuestaFalsa>> abrirEta(
      WidgetTester tester,
      Map<String, RespuestaFalsa> extra,
    ) async {
      final todas = {..._ficha(busetasJson([])), ...extra};
      await montar(
        tester,
        pantalla: () => const SizedBox(),
        respuestas: todas,
        inicial: '/ruta/$idCable/paradero/p2',
      );
      await tester.pumpAndSettle();
      return todas;
    }

    testWidgets('con GPS: minutos, buseta y fuente con antigüedad', (tester) async {
      await abrirEta(tester, {
        '/paraderos/p2/eta': RespuestaFalsa(etaJson([resultadoEtaJson()])),
      });

      expect(find.text('Paradero Carrera 23'), findsOneWidget);
      expect(find.text('4 min'), findsOneWidget);
      expect(find.text('Buseta 1544 viene hacia aquí'), findsOneWidget);
      expect(find.text('Fuente: GPS · hace 3 s'), findsOneWidget);
    });

    testWidgets('por horario: «Hasta N min» con el aviso de estimación', (tester) async {
      const aviso =
          'Sin ubicación de busetas. Estimación por horario: cada 4 min. Esté pendiente de la siguiente buseta.';
      await abrirEta(tester, {
        '/paraderos/p2/eta': RespuestaFalsa(etaJson([
          resultadoEtaJson(fuente: 'horario', etaSegundos: null, maxSegundos: 240, mensaje: aviso),
        ])),
      });

      expect(find.text('Hasta 4 min'), findsOneWidget);
      expect(find.text('Fuente: horario'), findsOneWidget);
      expect(find.text(aviso), findsOneWidget);
    });

    testWidgets('sin datos: muestra el mensaje del servidor', (tester) async {
      await abrirEta(tester, {
        '/paraderos/p2/eta': RespuestaFalsa(etaJson([
          resultadoEtaJson(fuente: 'no_disponible', etaSegundos: null, mensaje: 'El servicio ya cerró.'),
        ])),
      });

      expect(find.text('El servicio ya cerró.'), findsOneWidget);
      expect(find.text('Fuente: sin datos'), findsOneWidget);
    });

    testWidgets('varios servicios: una tarjeta por empresa', (tester) async {
      await abrirEta(tester, {
        '/paraderos/p2/eta': RespuestaFalsa(etaJson([
          resultadoEtaJson(),
          {
            ...resultadoEtaJson(fuente: 'horario', etaSegundos: null, maxSegundos: 240, mensaje: 'Estimación.'),
            'empresa': 'Serviturismo',
            'codigoPublico': null,
          },
        ])),
      });

      expect(find.text('Sideral · 39'), findsOneWidget);
      expect(find.text('Serviturismo · sin código'), findsOneWidget);
    });

    testWidgets('error de conexión: banner con Reintentar que se recupera', (tester) async {
      final respuestas = await abrirEta(tester, {
        '/paraderos/p2/eta':
            errorFalso(503, 'SERVICIO_EXTERNO_NO_DISPONIBLE', 'Base de datos no disponible.'),
      });
      expect(find.text('Base de datos no disponible.'), findsOneWidget);

      respuestas['/paraderos/p2/eta'] = RespuestaFalsa(etaJson([resultadoEtaJson()]));
      await tester.tap(find.text('Reintentar'));
      await tester.pumpAndSettle();
      expect(find.text('4 min'), findsOneWidget);
    });

    testWidgets('tocar un paradero del Recorrido abre su ETA', (tester) async {
      await montar(
        tester,
        pantalla: () => const SizedBox(),
        respuestas: {
          ..._ficha(busetasJson([])),
          '/paraderos/p1/eta': RespuestaFalsa(etaJson([resultadoEtaJson()])),
        },
        inicial: '/ruta/$idCable',
      );
      await tester.pumpAndSettle();

      expect(find.text('Toca un paradero para ver cuánto falta.'), findsOneWidget);
      await tester.tap(find.text('Terminal'));
      await tester.pumpAndSettle();

      expect(find.text('Paradero Terminal'), findsOneWidget);
      expect(find.text('4 min'), findsOneWidget);
    });
  });
}
