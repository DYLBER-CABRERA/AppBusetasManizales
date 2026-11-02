import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';

import 'package:busetas_app/caracteristicas/buscar/presentacion/pantalla_buscar.dart';
import 'package:busetas_app/caracteristicas/mapa/presentacion/pantalla_mapa.dart';
import 'package:busetas_app/caracteristicas/ruta/presentacion/widgets/fila_ruta.dart';

import 'ayudas/api_falsa.dart';
import 'ayudas/datos_ejemplo.dart';
import 'ayudas/montaje.dart';

void main() {
  group('Buscar', () {
    final base = {
      '/rutas/$idCable/busetas': RespuestaFalsa(busetasVacio()),
    };

    testWidgets('escribir busca rutas y lugares; tocar un resultado abre la ficha', (tester) async {
      await montar(
        tester,
        pantalla: () => const PantallaBuscar(),
        respuestas: {
          ...base,
          '/busqueda/rutas': RespuestaFalsa([resumenCable]),
          '/busqueda/hitos': RespuestaFalsa([hitoCatedral()]),
          '/rutas/$idCable': RespuestaFalsa(detalleCable()),
          '/rutas/$idCable/horarios': RespuestaFalsa(horariosCable()),
          '/rutas/$idCable/frecuencias': RespuestaFalsa(frecuenciasCable()),
        },
      );

      await tester.enterText(find.byType(TextField), 'cable');
      await tester.pump(const Duration(milliseconds: 400));
      await tester.pumpAndSettle();

      expect(find.byType(FilaRuta), findsOneWidget);
      expect(find.text('Lugares'), findsOneWidget);
      expect(find.text('Catedral'), findsWidgets);

      await tester.tap(find.byType(FilaRuta));
      await tester.pumpAndSettle();
      expect(find.text('Recorrido'), findsOneWidget);
      expect(find.text('Terminal'), findsOneWidget);
    });

    testWidgets('sin coincidencias muestra el texto del documento de UX', (tester) async {
      await montar(
        tester,
        pantalla: () => const PantallaBuscar(),
        respuestas: {
          '/busqueda/rutas': const RespuestaFalsa(<Object>[]),
          '/busqueda/hitos': const RespuestaFalsa(<Object>[]),
        },
      );

      await tester.enterText(find.byType(TextField), 'xyz');
      await tester.pump(const Duration(milliseconds: 400));
      await tester.pumpAndSettle();

      expect(find.text('Sin resultados para “xyz”.'), findsOneWidget);
      expect(
        find.text('Prueba con un hito como Catedral o con el número de la ruta.'),
        findsOneWidget,
      );
    });

    testWidgets('el chip de un hito lista las rutas que pasan', (tester) async {
      await montar(
        tester,
        pantalla: () => const PantallaBuscar(),
        respuestas: {
          '/busqueda/hitos': RespuestaFalsa([hitoCatedral()]),
          '/hitos/h1/rutas': RespuestaFalsa({
            'cobertura': true,
            'rutas': [resumenCable],
          }),
        },
      );

      await tester.tap(find.widgetWithText(ActionChip, 'Catedral'));
      await tester.pumpAndSettle();

      expect(find.text('Rutas que pasan por Catedral'), findsOneWidget);
      expect(find.byType(FilaRuta), findsOneWidget);
    });

    testWidgets('hito sin cobertura indica el paradero más cercano', (tester) async {
      await montar(
        tester,
        pantalla: () => const PantallaBuscar(),
        respuestas: {
          '/busqueda/hitos': RespuestaFalsa([hitoCatedral()]),
          '/hitos/h1/rutas': const RespuestaFalsa({
            'cobertura': false,
            'rutas': <Object>[],
            'paraderoMasCercano': {
              'paraderoId': 'p1',
              'nombre': 'Fundadores',
              'lat': 5.07,
              'lng': -75.5,
              'distanciaM': 1200,
            },
          }),
        },
      );

      await tester.tap(find.widgetWithText(ActionChip, 'Catedral'));
      await tester.pumpAndSettle();

      expect(find.text('No hay rutas cerca de Catedral.'), findsOneWidget);
      expect(find.text('El paradero más cercano está en Fundadores, a 1,2 km.'), findsOneWidget);
    });

    testWidgets('error de conexión muestra el banner con Reintentar y se recupera', (tester) async {
      final respuestas = <String, RespuestaFalsa>{
        '/busqueda/hitos': errorFalso(503, 'SERVICIO_EXTERNO_NO_DISPONIBLE', 'Base de datos no disponible.'),
      };
      await montar(tester, pantalla: () => const PantallaBuscar(), respuestas: respuestas);

      await tester.tap(find.widgetWithText(ActionChip, 'Catedral'));
      await tester.pumpAndSettle();
      expect(find.text('Base de datos no disponible.'), findsOneWidget);
      expect(find.text('Reintentar'), findsOneWidget);

      respuestas['/busqueda/hitos'] = RespuestaFalsa([hitoCatedral()]);
      respuestas['/hitos/h1/rutas'] = RespuestaFalsa({'cobertura': true, 'rutas': [resumenCable]});
      await tester.tap(find.text('Reintentar'));
      await tester.pumpAndSettle();
      expect(find.text('Rutas que pasan por Catedral'), findsOneWidget);
    });
  });

  group('Ficha de ruta', () {
    final respuestas = {
      '/rutas/$idCable': RespuestaFalsa(detalleCable()),
      '/rutas/$idCable/horarios': RespuestaFalsa(horariosCable()),
      '/rutas/$idCable/frecuencias': RespuestaFalsa(frecuenciasCable()),
      '/rutas': RespuestaFalsa([resumenCable]),
    };

    testWidgets('cabecera con empresas, avisos y paraderos en orden', (tester) async {
      await montar(
        tester,
        pantalla: () => const SizedBox(),
        respuestas: respuestas,
        inicial: '/ruta/$idCable',
      );
      await tester.pumpAndSettle();

      expect(find.text('Sideral · 39'), findsOneWidget);
      expect(find.text('Cierre por obras en la carrera 23'), findsOneWidget);
      final terminal = tester.getTopLeft(find.text('Terminal')).dy;
      final carrera = tester.getTopLeft(find.text('Carrera 23').last).dy;
      expect(terminal, lessThan(carrera));
    });

    testWidgets('Horarios resalta hoy y marca el sábado como pendiente', (tester) async {
      await montar(
        tester,
        pantalla: () => const SizedBox(),
        respuestas: respuestas,
        inicial: '/ruta/$idCable',
      );
      await tester.pumpAndSettle();

      await tester.tap(find.text('Horarios'));
      await tester.pumpAndSettle();

      expect(find.text('Lun–vie (hoy)'), findsOneWidget);
      expect(find.text('04:45'), findsOneWidget);
      expect(find.text('Sábados'), findsOneWidget);
      expect(find.text('Información pendiente de actualización'), findsOneWidget);
    });

    testWidgets('Frecuencia muestra el rango y pendiente donde no hay franja', (tester) async {
      await montar(
        tester,
        pantalla: () => const SizedBox(),
        respuestas: respuestas,
        inicial: '/ruta/$idCable',
      );
      await tester.pumpAndSettle();

      await tester.tap(find.text('Frecuencia'));
      await tester.pumpAndSettle();

      expect(find.text('De 8 a 10 min'), findsOneWidget);
      expect(find.text('Información pendiente de actualización'), findsNWidgets(2));
    });

    testWidgets('ruta inexistente ofrece las rutas cercanas', (tester) async {
      await montar(
        tester,
        pantalla: () => const SizedBox(),
        respuestas: {
          '/rutas/no-existe': errorFalso(404, 'NO_ENCONTRADO', 'Ruta no encontrada.'),
          '/rutas/cercanas': RespuestaFalsa({
            'rutas': [resumenCable],
          }),
          '/rutas/$idCable/busetas': RespuestaFalsa(busetasVacio()),
        },
        inicial: '/ruta/no-existe',
      );
      await tester.pumpAndSettle();

      expect(
        find.text('No encontramos esa ruta. Estas rutas cercanas podrían servirte:'),
        findsOneWidget,
      );
      expect(find.text('El Cable'), findsOneWidget);
    });
  });

  group('Mapa', () {
    testWidgets('lista las rutas cercanas con distancia y unidades en servicio', (tester) async {
      await montar(
        tester,
        pantalla: () => const PantallaMapa(),
        respuestas: {
          '/rutas/cercanas': RespuestaFalsa({
            'rutas': [resumenCable, resumenEnea],
          }),
          '/rutas': RespuestaFalsa([resumenCable, resumenEnea]),
          '/rutas/$idCable': RespuestaFalsa(detalleCable()),
          '/rutas/$idCable/busetas': RespuestaFalsa({...busetasVacio(), 'unidadesEnServicio': 2}),
          '/rutas/$idEnea/busetas': RespuestaFalsa(busetasVacio()),
        },
      );
      await tester.pumpAndSettle();

      expect(find.text('Rutas cerca de ti'), findsOneWidget);
      expect(find.text('El Cable'), findsOneWidget);
      expect(find.textContaining('a 220 m'), findsOneWidget);
      expect(find.text('2 en servicio'), findsOneWidget);
      expect(find.text('Sin busetas en servicio ahora'), findsOneWidget);
      expect(find.text('© OpenStreetMap contributors'), findsOneWidget);
    });

    testWidgets('sin rutas a 800 m indica el paradero más cercano', (tester) async {
      await montar(
        tester,
        pantalla: () => const PantallaMapa(),
        respuestas: {
          '/rutas/cercanas': const RespuestaFalsa({
            'rutas': <Object>[],
            'paraderoMasCercano': {
              'paraderoId': 'p1',
              'nombre': 'Terminal',
              'lat': 5.05,
              'lng': -75.5,
              'distanciaM': 1234,
            },
          }),
          '/rutas': const RespuestaFalsa(<Object>[]),
        },
      );
      await tester.pumpAndSettle();

      expect(find.text('No hay rutas a menos de 800 m.'), findsOneWidget);
      expect(find.text('El paradero más cercano está en Terminal, a 1,2 km.'), findsOneWidget);
      expect(find.text('Sin tu ubicación: mostramos el centro de Manizales.'), findsOneWidget);
    });

    testWidgets('error de conexión muestra el banner con Reintentar', (tester) async {
      await montar(
        tester,
        pantalla: () => const PantallaMapa(),
        respuestas: {
          '/rutas/cercanas':
              errorFalso(503, 'SERVICIO_EXTERNO_NO_DISPONIBLE', 'Base de datos no disponible.'),
          '/rutas': const RespuestaFalsa(<Object>[]),
        },
      );
      await tester.pumpAndSettle();

      expect(find.text('Base de datos no disponible.'), findsOneWidget);
      expect(find.text('Reintentar'), findsOneWidget);
    });
  });
}
