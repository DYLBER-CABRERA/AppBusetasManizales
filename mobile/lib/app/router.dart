import 'package:flutter/material.dart';
import 'package:go_router/go_router.dart';

import '../caracteristicas/ajustes/presentacion/pantalla_ajustes.dart';
import 'pantalla_pendiente.dart';
import 'shell.dart';

GoRouter construirRouter() {
  StatefulShellBranch rama(String ruta, String titulo, String bloque) {
    return StatefulShellBranch(routes: [
      GoRoute(
        path: ruta,
        builder: (_, _) => PantallaPendiente(titulo: titulo, bloque: bloque),
      ),
    ]);
  }

  return GoRouter(
    initialLocation: '/mapa',
    routes: [
      StatefulShellRoute.indexedStack(
        builder: (context, state, navegacion) => ShellPrincipal(navegacion: navegacion),
        branches: [
          rama('/mapa', 'Mapa', 'M1'),
          rama('/buscar', 'Buscar', 'M1'),
          rama('/viajar', 'Viajar', 'M4'),
          rama('/guardados', 'Guardados', 'M3'),
          rama('/avisos', 'Avisos', 'M3'),
        ],
      ),
      GoRoute(path: '/ajustes', builder: (_, _) => const PantallaAjustes()),
    ],
    errorBuilder: (context, state) => const Scaffold(
      body: Center(child: Text('No encontramos esa pantalla.')),
    ),
  );
}
