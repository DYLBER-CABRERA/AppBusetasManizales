import 'package:flutter/material.dart';
import 'package:go_router/go_router.dart';

import 'banner_ejemplo.dart';

class _Destino {
  const _Destino(this.etiqueta, this.icono, this.iconoActivo);
  final String etiqueta;
  final IconData icono;
  final IconData iconoActivo;
}

const _destinos = [
  _Destino('Mapa', Icons.map_outlined, Icons.map),
  _Destino('Buscar', Icons.search, Icons.search),
  _Destino('Viajar', Icons.directions_bus_outlined, Icons.directions_bus),
  _Destino('Guardados', Icons.bookmark_border, Icons.bookmark),
  _Destino('Avisos', Icons.notifications_none, Icons.notifications),
];

/// Barra superior + banner permanente + barra inferior de 5 destinos.
class ShellPrincipal extends StatelessWidget {
  const ShellPrincipal({super.key, required this.navegacion});

  final StatefulNavigationShell navegacion;

  @override
  Widget build(BuildContext context) {
    final indice = navegacion.currentIndex;
    return Scaffold(
      appBar: AppBar(
        title: Text(_destinos[indice].etiqueta),
        actions: [
          if (indice == 0)
            IconButton(
              tooltip: 'Ajustes',
              icon: const Icon(Icons.settings_outlined),
              constraints: const BoxConstraints(minWidth: 48, minHeight: 48),
              onPressed: () => context.push('/ajustes'),
            ),
        ],
      ),
      body: Column(
        children: [
          const BannerEjemplo(),
          Expanded(child: navegacion),
        ],
      ),
      bottomNavigationBar: NavigationBar(
        selectedIndex: indice,
        onDestinationSelected: (i) =>
            navegacion.goBranch(i, initialLocation: i == navegacion.currentIndex),
        destinations: [
          for (final d in _destinos)
            NavigationDestination(
              icon: Icon(d.icono),
              selectedIcon: Icon(d.iconoActivo),
              label: d.etiqueta,
            ),
        ],
      ),
    );
  }
}
