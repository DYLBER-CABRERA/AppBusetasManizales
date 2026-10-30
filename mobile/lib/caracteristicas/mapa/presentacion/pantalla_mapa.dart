import 'package:flutter/material.dart';
import 'package:flutter_map/flutter_map.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';
import 'package:latlong2/latlong.dart';

import '../../../app/widgets/async_vista.dart';
import '../../../app/widgets/capas_osm.dart';
import '../../../app/widgets/vacio_con_accion.dart';
import '../../../nucleo/formato.dart';
import '../../../nucleo/ubicacion.dart';
import '../../ruta/dominio/ruta.dart';
import '../../ruta/presentacion/ruta_providers.dart';
import '../../ruta/dominio/seguimiento.dart';
import '../../ruta/presentacion/seguimiento_provider.dart';
import '../../ruta/presentacion/widgets/fila_ruta.dart';
import '../../ruta/presentacion/widgets/marcadores_busetas.dart';
import 'mapa_providers.dart';

class PantallaMapa extends ConsumerStatefulWidget {
  const PantallaMapa({super.key});

  @override
  ConsumerState<PantallaMapa> createState() => _PantallaMapaState();
}

class _PantallaMapaState extends ConsumerState<PantallaMapa> {
  final _controlador = MapController();
  bool _mapaListo = false;

  void _centrarEn(LatLng? punto) {
    if (punto == null || !_mapaListo) return;
    _controlador.move(punto, 15);
  }

  @override
  Widget build(BuildContext context) {
    final ubicacion = ref.watch(ubicacionProvider);
    final cercanas = ref.watch(rutasCercanasProvider);
    final todas = ref.watch(todasLasRutasProvider);
    final idsCercanas = {for (final r in cercanas.value?.rutas ?? const <RutaResumen>[]) r.id};

    ref.listen(ubicacionProvider, (_, siguiente) => _centrarEn(siguiente.value));

    // Trazados de todas las rutas activas; los de las cercanas van más gruesos.
    final polilineas = <Polyline>[];
    for (final ruta in todas.value ?? const <RutaResumen>[]) {
      final detalle = ref.watch(rutaDetalleProvider(ruta.id)).value;
      if (detalle == null) continue;
      final color = colorDeRuta(ref, ruta.id);
      final cerca = idsCercanas.contains(ruta.id);
      polilineas.add(Polyline(
        points: detalle.trazado,
        strokeWidth: cerca ? 5 : 3,
        color: cerca ? color : color.withValues(alpha: 0.55),
      ));
    }

    // Busetas de las rutas cercanas en tiempo real; con el mapa fuera de vista (otra
    // pestaña o pantalla encima) no se escucha y se cierran los sockets.
    final visible = TickerMode.valuesOf(context).enabled;
    final busetas = <BusetaEnVivo>[];
    final unidades = <String, int>{};
    if (visible) {
      for (final id in idsCercanas) {
        final seguimiento = ref.watch(seguimientoProvider(id));
        busetas.addAll(seguimiento.busetas);
        if (seguimiento.unidadesEnServicio != null) unidades[id] = seguimiento.unidadesEnServicio!;
      }
    }

    final punto = ubicacion.value;
    final paradero = cercanas.value?.paraderoMasCercano;
    final sinRutas = cercanas.hasValue && cercanas.requireValue.rutas.isEmpty;

    return Stack(
      children: [
        Semantics(
          label: 'Mapa de rutas de Manizales',
          child: FlutterMap(
            mapController: _controlador,
            options: MapOptions(
              initialCenter: punto ?? centroManizales,
              initialZoom: 14,
              onMapReady: () {
                _mapaListo = true;
                _centrarEn(ref.read(ubicacionProvider).value);
              },
            ),
            children: [
              ...capasBaseOsm(),
              PolylineLayer(polylines: polilineas),
              MarcadoresBusetas(busetas: busetas),
              MarkerLayer(markers: [
                if (sinRutas && paradero != null)
                  Marker(
                    point: LatLng(paradero.lat, paradero.lng),
                    width: 44,
                    height: 44,
                    child: Semantics(
                      label: 'Paradero más cercano: ${paradero.nombre}',
                      child: Icon(Icons.place, size: 36, color: Theme.of(context).colorScheme.primary),
                    ),
                  ),
                if (punto != null)
                  Marker(
                    point: punto,
                    width: 28,
                    height: 28,
                    child: Semantics(label: 'Tu ubicación', child: const _PuntoUsuario()),
                  ),
              ]),
            ],
          ),
        ),
        Positioned(
          top: 12,
          left: 16,
          right: 16,
          child: _BarraBusqueda(onTap: () => context.go('/buscar')),
        ),
        Positioned(
          top: 76,
          right: 16,
          child: FloatingActionButton.small(
            heroTag: 'mi_ubicacion',
            tooltip: 'Usar mi ubicación',
            onPressed: () => ref.read(ubicacionProvider.notifier).actualizar(),
            child: ubicacion.isLoading
                ? const SizedBox(width: 20, height: 20, child: CircularProgressIndicator(strokeWidth: 2.5))
                : const Icon(Icons.my_location),
          ),
        ),
        DraggableScrollableSheet(
          initialChildSize: 0.4,
          minChildSize: 0.14,
          maxChildSize: 0.85,
          builder: (context, scroll) => _HojaRutas(
            controlador: scroll,
            cercanas: cercanas,
            unidades: unidades,
            sinUbicacion: !ubicacion.isLoading && punto == null,
            onReintentar: () => ref.invalidate(rutasCercanasProvider),
          ),
        ),
      ],
    );
  }
}

class _BarraBusqueda extends StatelessWidget {
  const _BarraBusqueda({required this.onTap});

  final VoidCallback onTap;

  @override
  Widget build(BuildContext context) {
    final esquema = Theme.of(context).colorScheme;
    return Semantics(
      button: true,
      label: 'Buscar ruta, barrio o lugar',
      excludeSemantics: true,
      child: Material(
        color: esquema.surface,
        elevation: 3,
        borderRadius: BorderRadius.circular(28),
        child: InkWell(
          borderRadius: BorderRadius.circular(28),
          onTap: onTap,
          child: ConstrainedBox(
            constraints: const BoxConstraints(minHeight: 48),
            child: Padding(
              padding: const EdgeInsets.symmetric(horizontal: 16),
              child: Row(
                children: [
                  Icon(Icons.search, color: esquema.onSurface),
                  const SizedBox(width: 12),
                  Text('¿A dónde vas?', style: Theme.of(context).textTheme.bodyLarge),
                ],
              ),
            ),
          ),
        ),
      ),
    );
  }
}

class _PuntoUsuario extends StatelessWidget {
  const _PuntoUsuario();

  @override
  Widget build(BuildContext context) => Container(
        decoration: BoxDecoration(
          color: const Color(0xFF1F5FA8),
          shape: BoxShape.circle,
          border: Border.all(color: Colors.white, width: 3),
          boxShadow: const [BoxShadow(blurRadius: 4, color: Colors.black38)],
        ),
      );
}

class _HojaRutas extends ConsumerWidget {
  const _HojaRutas({
    required this.controlador,
    required this.cercanas,
    required this.unidades,
    required this.sinUbicacion,
    required this.onReintentar,
  });

  final ScrollController controlador;
  final AsyncValue<ResultadoRutas> cercanas;
  final Map<String, int> unidades;
  final bool sinUbicacion;
  final VoidCallback onReintentar;

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final esquema = Theme.of(context).colorScheme;
    return Material(
      color: esquema.surface,
      elevation: 8,
      borderRadius: const BorderRadius.vertical(top: Radius.circular(20)),
      clipBehavior: Clip.antiAlias,
      child: ListView(
        controller: controlador,
        padding: const EdgeInsets.only(bottom: 16),
        children: [
          Center(
            child: Container(
              width: 40,
              height: 4,
              margin: const EdgeInsets.symmetric(vertical: 10),
              decoration: BoxDecoration(
                color: esquema.onSurface.withValues(alpha: 0.3),
                borderRadius: BorderRadius.circular(2),
              ),
            ),
          ),
          Padding(
            padding: const EdgeInsets.fromLTRB(16, 0, 16, 8),
            child: Text('Rutas cerca de ti', style: Theme.of(context).textTheme.titleLarge),
          ),
          if (sinUbicacion)
            Padding(
              padding: const EdgeInsets.fromLTRB(16, 0, 16, 8),
              child: Row(
                children: [
                  const Expanded(
                    child: Text('Sin tu ubicación: mostramos el centro de Manizales.'),
                  ),
                  TextButton(
                    onPressed: () => ref.read(ubicacionProvider.notifier).actualizar(),
                    child: const Text('Usar mi ubicación'),
                  ),
                ],
              ),
            ),
          AsyncVista<ResultadoRutas>(
            valor: cercanas,
            onReintentar: onReintentar,
            datos: (resultado) => resultado.rutas.isEmpty
                ? _SinRutasCerca(paradero: resultado.paraderoMasCercano)
                : Column(
                    children: [
                      for (final ruta in resultado.rutas)
                        FilaRuta(
                          ruta: ruta,
                          unidades: unidades[ruta.id],
                          onTap: () => context.push('/ruta/${ruta.id}'),
                        ),
                    ],
                  ),
          ),
        ],
      ),
    );
  }
}

class _SinRutasCerca extends StatelessWidget {
  const _SinRutasCerca({this.paradero});

  final ParaderoCercano? paradero;

  @override
  Widget build(BuildContext context) {
    final causa = paradero == null
        ? null
        : 'El paradero más cercano está en ${paradero!.nombre}, a ${formatearDistancia(paradero!.distanciaM)}.';
    return VacioConAccion(
      titulo: 'No hay rutas a menos de $radioBusquedaPorDefectoM m.',
      causa: causa,
      icono: Icons.directions_bus_outlined,
    );
  }
}
