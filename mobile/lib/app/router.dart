import 'package:flutter/material.dart';
import 'package:go_router/go_router.dart';

import '../caracteristicas/ajustes/presentacion/pantalla_ajustes.dart';
import '../caracteristicas/buscar/presentacion/pantalla_buscar.dart';
import '../caracteristicas/mapa/presentacion/pantalla_mapa.dart';
import '../caracteristicas/ruta/presentacion/pantalla_ruta.dart';
import 'pantalla_pendiente.dart';
import 'shell.dart';

GoRouter construirRouter() {
  StatefulShellBranch rama(String ruta, Widget pantalla) {
    return StatefulShellBranch(routes: [
      GoRoute(path: ruta, builder: (_, _) => pantalla),
    ]);
  }

  StatefulShellBranch ramaPendiente(String ruta, String titulo, String bloque) =>
      rama(ruta, PantallaPendiente(titulo: titulo, bloque: bloque));

  return GoRouter(
    initialLocation: '/mapa',
    routes: [
      StatefulShellRoute.indexedStack(
        builder: (context, state, navegacion) => ShellPrincipal(navegacion: navegacion),
        branches: [
          rama('/mapa', const PantallaMapa()),
          rama('/buscar', const PantallaBuscar()),
          ramaPendiente('/viajar', 'Viajar', 'M4'),
          ramaPendiente('/guardados', 'Guardados', 'M3'),
          ramaPendiente('/avisos', 'Avisos', 'M3'),
        ],
      ),
      GoRoute(
        path: '/ruta/:id',
        builder: (_, estado) => PantallaRuta(rutaId: estado.pathParameters['id']!),
      ),
      GoRoute(path: '/ajustes', builder: (_, _) => const PantallaAjustes()),
    ],
    errorBuilder: (context, state) => const Scaffold(
      body: Center(child: Text('No encontramos esa pantalla.')),
    ),
  );
}
