import 'package:flutter/material.dart';
import 'package:flutter_map/flutter_map.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';

import '../../../app/banner_ejemplo.dart';
import '../../../app/widgets/banner_error.dart';
import '../../../app/widgets/capas_osm.dart';
import '../../../app/widgets/esqueleto.dart';
import '../../../nucleo/errores.dart';
import '../../mapa/presentacion/mapa_providers.dart';
import '../dominio/ruta.dart';
import 'pestanas_ruta.dart';
import 'ruta_providers.dart';
import 'widgets/fila_ruta.dart';
import 'widgets/sello_ruta.dart';

/// Ficha de ruta: cabecera, mini mapa y pestañas Recorrido · Horarios · Frecuencia · En vivo.
class PantallaRuta extends ConsumerWidget {
  const PantallaRuta({super.key, required this.rutaId});

  final String rutaId;

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final detalle = ref.watch(rutaDetalleProvider(rutaId));
    final color = colorDeRuta(ref, rutaId);
    return Scaffold(
      appBar: AppBar(
        title: Text(detalle.value?.nombre ?? 'Ruta'),
        leading: BackButton(
          onPressed: () => context.canPop() ? context.pop() : context.go('/mapa'),
        ),
      ),
      body: Column(
        children: [
          const BannerEjemplo(),
          Expanded(
            child: detalle.when(
              data: (d) => _FichaCompleta(detalle: d, color: color),
              loading: () => const SingleChildScrollView(child: EsqueletoLista(filas: 5)),
              error: (error, _) => error is ErrorApi && error.esNoEncontrado
                  ? const _RutaNoEncontrada()
                  : ListView(children: [
                      BannerError.desdeError(
                        error,
                        onReintentar: () => ref.invalidate(rutaDetalleProvider(rutaId)),
                      ),
                    ]),
            ),
          ),
        ],
      ),
    );
  }
}

class _FichaCompleta extends StatelessWidget {
  const _FichaCompleta({required this.detalle, required this.color});

  final RutaDetalle detalle;
  final Color color;

  @override
  Widget build(BuildContext context) {
    final texto = Theme.of(context).textTheme;
    return DefaultTabController(
      length: 4,
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.stretch,
        children: [
          Padding(
            padding: const EdgeInsets.fromLTRB(16, 12, 16, 8),
            child: Row(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                SelloRuta(codigo: detalle.codigoSello, color: color, tamano: 52),
                const SizedBox(width: 12),
                Expanded(
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      Text(detalle.nombre, style: texto.titleLarge),
                      const SizedBox(height: 4),
                      Wrap(
                        spacing: 6,
                        children: [
                          for (final s in detalle.servicios)
                            Chip(
                              label: Text(s.etiqueta),
                              visualDensity: VisualDensity.compact,
                            ),
                        ],
                      ),
                    ],
                  ),
                ),
              ],
            ),
          ),
          SizedBox(height: 170, child: _MiniMapa(detalle: detalle, color: color)),
          const TabBar(
            isScrollable: true,
            tabAlignment: TabAlignment.start,
            tabs: [
              Tab(text: 'Recorrido'),
              Tab(text: 'Horarios'),
              Tab(text: 'Frecuencia'),
              Tab(text: 'En vivo'),
            ],
          ),
          Expanded(
            child: TabBarView(
              children: [
                PestanaRecorrido(detalle: detalle, color: color),
                PestanaHorarios(rutaId: detalle.id),
                PestanaFrecuencia(rutaId: detalle.id),
                // PENDIENTE(M2): lista de busetas en vivo (WebSocket + respaldo REST).
                const Center(child: Text('Las busetas en vivo llegan en el bloque M2.')),
              ],
            ),
          ),
        ],
      ),
    );
  }
}

class _MiniMapa extends StatelessWidget {
  const _MiniMapa({required this.detalle, required this.color});

  final RutaDetalle detalle;
  final Color color;

  @override
  Widget build(BuildContext context) {
    final puntos = detalle.trazado;
    return Semantics(
      label: 'Mapa del recorrido de ${detalle.nombre}',
      child: FlutterMap(
        options: MapOptions(
          initialCameraFit: puntos.length >= 2
              ? CameraFit.coordinates(coordinates: puntos, padding: const EdgeInsets.all(28))
              : null,
          interactionOptions: const InteractionOptions(
            flags: InteractiveFlag.drag | InteractiveFlag.pinchZoom,
          ),
        ),
        children: [
          ...capasBaseOsm(),
          PolylineLayer(polylines: [Polyline(points: puntos, strokeWidth: 5, color: color)]),
          MarkerLayer(markers: [
            for (final p in detalle.paraderos)
              Marker(
                point: p.punto,
                width: 16,
                height: 16,
                child: Container(
                  decoration: BoxDecoration(
                    color: Colors.white,
                    shape: BoxShape.circle,
                    border: Border.all(color: color, width: 3),
                  ),
                ),
              ),
          ]),
        ],
      ),
    );
  }
}

/// HU-P02: la ruta no existe → rutas cercanas que podrían servir.
class _RutaNoEncontrada extends ConsumerWidget {
  const _RutaNoEncontrada();

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final cercanas = ref.watch(rutasCercanasProvider);
    return ListView(
      padding: const EdgeInsets.only(bottom: 24),
      children: [
        Padding(
          padding: const EdgeInsets.all(16),
          child: Text(
            'No encontramos esa ruta. Estas rutas cercanas podrían servirte:',
            style: Theme.of(context).textTheme.titleMedium,
          ),
        ),
        if (cercanas.isLoading && !cercanas.hasValue) const EsqueletoLista(),
        if (cercanas.hasError && !cercanas.hasValue)
          BannerError.desdeError(
            cercanas.error!,
            onReintentar: () => ref.invalidate(rutasCercanasProvider),
          ),
        for (final ruta in cercanas.value?.rutas ?? const <RutaResumen>[])
          FilaRuta(ruta: ruta, onTap: () => context.pushReplacement('/ruta/${ruta.id}')),
      ],
    );
  }
}
