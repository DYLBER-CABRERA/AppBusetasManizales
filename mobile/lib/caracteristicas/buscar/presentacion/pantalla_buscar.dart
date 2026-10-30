import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';

import '../../../app/widgets/banner_error.dart';
import '../../../app/widgets/esqueleto.dart';
import '../../../app/widgets/vacio_con_accion.dart';
import '../../../nucleo/formato.dart';
import '../../ruta/presentacion/widgets/fila_ruta.dart';
import '../dominio/hito.dart';
import 'buscar_provider.dart';

class PantallaBuscar extends ConsumerStatefulWidget {
  const PantallaBuscar({super.key});

  @override
  ConsumerState<PantallaBuscar> createState() => _PantallaBuscarState();
}

class _PantallaBuscarState extends ConsumerState<PantallaBuscar> {
  final _campo = TextEditingController();

  @override
  void dispose() {
    _campo.dispose();
    super.dispose();
  }

  void _limpiar() {
    _campo.clear();
    ref.read(busquedaProvider.notifier).limpiar();
  }

  @override
  Widget build(BuildContext context) {
    final estado = ref.watch(busquedaProvider);
    final notificador = ref.read(busquedaProvider.notifier);

    return ListView(
      keyboardDismissBehavior: ScrollViewKeyboardDismissBehavior.onDrag,
      padding: const EdgeInsets.only(bottom: 24),
      children: [
        Padding(
          padding: const EdgeInsets.fromLTRB(16, 16, 16, 8),
          child: TextField(
            controller: _campo,
            textInputAction: TextInputAction.search,
            decoration: InputDecoration(
              labelText: 'Ruta, barrio o lugar',
              prefixIcon: const Icon(Icons.search),
              suffixIcon: _campo.text.isEmpty
                  ? null
                  : IconButton(
                      tooltip: 'Borrar texto',
                      icon: const Icon(Icons.clear),
                      onPressed: _limpiar,
                    ),
            ),
            onChanged: (texto) {
              setState(() {});
              notificador.escribir(texto);
            },
          ),
        ),
        Padding(
          padding: const EdgeInsets.symmetric(horizontal: 16),
          child: Wrap(
            spacing: 8,
            runSpacing: 4,
            children: [
              for (final nombre in hitosAtajo)
                ActionChip(
                  label: Text(nombre),
                  materialTapTargetSize: MaterialTapTargetSize.padded,
                  onPressed: () {
                    _campo.text = nombre;
                    setState(() {});
                    FocusScope.of(context).unfocus();
                    notificador.elegirAtajo(nombre);
                  },
                ),
            ],
          ),
        ),
        const SizedBox(height: 8),
        _Resultados(
          estado: estado,
          onElegirHito: (hito) {
            _campo.text = hito.nombre;
            setState(() {});
            FocusScope.of(context).unfocus();
            notificador.elegirHito(hito);
          },
        ),
      ],
    );
  }
}

class _Resultados extends ConsumerWidget {
  const _Resultados({required this.estado, required this.onElegirHito});

  final EstadoBusqueda estado;
  final void Function(Hito hito) onElegirHito;

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    switch (estado) {
      case BusquedaInactiva():
        return const VacioConAccion(
          titulo: 'Busca una ruta o un lugar',
          causa: 'Escribe el número de la ruta, un barrio o toca un hito.',
          icono: Icons.search,
        );
      case BusquedaCargando():
        return const EsqueletoLista();
      case BusquedaFallida(:final mensaje):
        return BannerError(
          mensaje: mensaje,
          onReintentar: () => ref.read(busquedaProvider.notifier).reintentar(),
        );
      case BusquedaConResultados(:final texto, :final rutas, :final hitos, :final vacia):
        if (vacia) {
          return VacioConAccion(
            titulo: 'Sin resultados para “$texto”.',
            causa: 'Prueba con un hito como Catedral o con el número de la ruta.',
            icono: Icons.search_off,
          );
        }
        return Column(
          crossAxisAlignment: CrossAxisAlignment.stretch,
          children: [
            if (rutas.isNotEmpty) ...[
              const _Encabezado('Rutas'),
              for (final ruta in rutas)
                FilaRuta(
                  ruta: ruta,
                  mostrarServicio: false,
                  onTap: () => context.push('/ruta/${ruta.id}'),
                ),
            ],
            if (hitos.isNotEmpty) ...[
              const _Encabezado('Lugares'),
              for (final hito in hitos)
                ListTile(
                  minTileHeight: 56,
                  leading: const Icon(Icons.place_outlined),
                  title: Text(hito.nombre),
                  subtitle: const Text('Ver rutas que pasan cerca'),
                  onTap: () => onElegirHito(hito),
                ),
            ],
          ],
        );
      case BusquedaDeHito(:final hito, :final resultado):
        final paradero = resultado.paraderoMasCercano;
        return Column(
          crossAxisAlignment: CrossAxisAlignment.stretch,
          children: [
            _Encabezado('Rutas que pasan por ${hito.nombre}'),
            if (!resultado.cobertura || resultado.rutas.isEmpty)
              VacioConAccion(
                titulo: 'No hay rutas cerca de ${hito.nombre}.',
                causa: paradero == null
                    ? null
                    : 'El paradero más cercano está en ${paradero.nombre}, a ${formatearDistancia(paradero.distanciaM)}.',
                icono: Icons.directions_bus_outlined,
              )
            else
              for (final ruta in resultado.rutas)
                FilaRuta(
                  ruta: ruta,
                  mostrarServicio: false,
                  onTap: () => context.push('/ruta/${ruta.id}'),
                ),
          ],
        );
    }
  }
}

class _Encabezado extends StatelessWidget {
  const _Encabezado(this.texto);

  final String texto;

  @override
  Widget build(BuildContext context) => Padding(
        padding: const EdgeInsets.fromLTRB(16, 12, 16, 4),
        child: Semantics(
          header: true,
          child: Text(texto, style: Theme.of(context).textTheme.titleMedium),
        ),
      );
}
