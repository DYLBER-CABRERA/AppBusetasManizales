import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:latlong2/latlong.dart';

import 'package:flutter_riverpod/flutter_riverpod.dart';

import 'package:busetas_app/app/widgets/punto_usuario.dart';
import 'package:busetas_app/caracteristicas/viajar/dominio/viaje.dart';
import 'package:busetas_app/caracteristicas/viajar/presentacion/capa_puntos_elegidos.dart';
import 'package:busetas_app/caracteristicas/viajar/presentacion/viajar_provider.dart';

import 'ayudas/api_falsa.dart';
import 'ayudas/canal_falso.dart';
import 'ayudas/datos_ejemplo.dart';
import 'ayudas/montaje.dart';

Map<String, RespuestaFalsa> _ficha() => {
      '/rutas/$idCable': RespuestaFalsa(detalleCable()),
      '/rutas/$idCable/horarios': RespuestaFalsa(horariosCable()),
      '/rutas/$idCable/frecuencias': RespuestaFalsa(frecuenciasCable()),
      '/rutas/$idCable/busetas': RespuestaFalsa(busetasVacio()),
    };

Future<void> _abrirFicha(WidgetTester tester, {LatLng? ubicacion}) async {
  await montar(
    tester,
    pantalla: () => const SizedBox(),
    respuestas: _ficha(),
    inicial: '/ruta/$idCable',
    ubicacion: ubicacion,
    fabrica: FabricaCanalesFalsa([CanalFalso()]),
  );
  await tester.pumpAndSettle();
}

void main() {
  testWidgets('el mini mapa de la ficha muestra el punto azul con el permiso concedido', (tester) async {
    await _abrirFicha(tester, ubicacion: const LatLng(5.0689, -75.5174));

    expect(find.byType(PuntoUsuario), findsOneWidget);
  });

  testWidgets('sin permiso de ubicación no se dibuja el punto', (tester) async {
    await _abrirFicha(tester);

    expect(find.byType(PuntoUsuario), findsNothing);
  });

  testWidgets('el punto elegido a mano en Viajar se marca aparte del punto azul', (tester) async {
    await _abrirFicha(tester, ubicacion: const LatLng(5.0689, -75.5174));
    expect(find.text('Destino'), findsNothing);

    final contenedor = ProviderScope.containerOf(tester.element(find.byType(CapaPuntosElegidos)));
    contenedor.read(viajarProvider.notifier).elegirDestino(const LugarViaje.enMapa(LatLng(5.0689, -75.5174)));
    await tester.pumpAndSettle();

    expect(find.text('Destino'), findsOneWidget);
    expect(find.byType(PuntoUsuario), findsOneWidget);
  });

  testWidgets('un hito elegido como origen también se marca, con bandera y su nombre', (tester) async {
    await _abrirFicha(tester, ubicacion: const LatLng(5.0689, -75.5174));

    final contenedor = ProviderScope.containerOf(tester.element(find.byType(CapaPuntosElegidos)));
    contenedor.read(viajarProvider.notifier).elegirOrigen(
          const LugarViaje.hito(id: 'h1', nombre: 'Catedral', punto: LatLng(5.0689, -75.5174)),
        );
    await tester.pumpAndSettle();

    expect(find.text('Origen · Catedral'), findsOneWidget);
    expect(find.byIcon(Icons.flag), findsOneWidget);
  });
}
