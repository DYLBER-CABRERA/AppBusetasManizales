import 'package:flutter/material.dart';
import 'package:go_router/go_router.dart';

import '../caracteristicas/ajustes/presentacion/pantalla_ajustes.dart';
import '../caracteristicas/avisos/presentacion/pantalla_avisos.dart';
import '../caracteristicas/buscar/presentacion/pantalla_buscar.dart';
import '../caracteristicas/eta/presentacion/pantalla_eta.dart';
import '../caracteristicas/guardados/presentacion/pantalla_guardados.dart';
import '../caracteristicas/mapa/presentacion/pantalla_mapa.dart';
import '../caracteristicas/ruta/presentacion/pantalla_ruta.dart';
import '../caracteristicas/viajar/presentacion/pantalla_viajar.dart';
import 'shell.dart';

GoRouter construirRouter() {
  StatefulShellBranch rama(String ruta, Widget pantalla) {
    return StatefulShellBranch(routes: [
      GoRoute(path: ruta, builder: (_, _) => pantalla),
    ]);
  }

  return GoRouter(
    initialLocation: '/mapa',
    routes: [
      StatefulShellRoute.indexedStack(
        builder: (context, state, navegacion) => ShellPrincipal(navegacion: navegacion),
        branches: [
          rama('/mapa', const PantallaMapa()),
          rama('/buscar', const PantallaBuscar()),
          rama('/viajar', const PantallaViajar()),
          rama('/guardados', const PantallaGuardados()),
          rama('/avisos', const PantallaAvisos()),
        ],
      ),
      GoRoute(
        path: '/ruta/:id',
        builder: (_, estado) => PantallaRuta(rutaId: estado.pathParameters['id']!),
      ),
      GoRoute(
        path: '/ruta/:rutaId/paradero/:paraderoId',
        builder: (_, estado) => PantallaEta(
          rutaId: estado.pathParameters['rutaId']!,
          paraderoId: estado.pathParameters['paraderoId']!,
        ),
      ),
      GoRoute(path: '/ajustes', builder: (_, _) => const PantallaAjustes()),
    ],
    errorBuilder: (context, state) => const Scaffold(
      body: Center(child: Text('No encontramos esa pantalla.')),
    ),
  );
}
