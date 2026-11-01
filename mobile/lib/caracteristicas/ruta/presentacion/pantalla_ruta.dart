import 'package:flutter/material.dart';
import 'package:flutter_map/flutter_map.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';

import '../../../app/banner_ejemplo.dart';
import '../../../app/widgets/banner_error.dart';
import '../../../app/widgets/capas_osm.dart';
import '../../../app/widgets/esqueleto.dart';
import '../../../app/widgets/punto_usuario.dart';
import '../../../nucleo/errores.dart';
import '../../../nucleo/ubicacion.dart';
import '../../mapa/presentacion/mapa_providers.dart';
import '../../viajar/presentacion/capa_puntos_elegidos.dart';
import '../dominio/ruta.dart';
import '../dominio/seguimiento.dart';
import 'pestana_en_vivo.dart';
import 'pestanas_ruta.dart';
import 'seguimiento_provider.dart';
import 'widgets/banner_desactualizado.dart';
import 'widgets/boton_guardar_ruta.dart';
import 'widgets/marcadores_busetas.dart';
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
        actions: [if (detalle.hasValue) BotonGuardarRuta(rutaId: rutaId)],
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

class _FichaCompleta extends ConsumerWidget {
  const _FichaCompleta({required this.detalle, required this.color});

  final RutaDetalle detalle;
  final Color color;

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final texto = Theme.of(context).textTheme;
    // El socket vive solo mientras la ficha está a la vista: si otra pantalla se
    // apila encima (p. ej. el ETA) se deja de escuchar y el proveedor lo cierra.
    final visible = TickerMode.valuesOf(context).enabled;
    final seguimiento =
        visible ? ref.watch(seguimientoProvider(detalle.id)) : seguimientoEnPausa;
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
          if (seguimiento.desactualizado)
            BannerDesactualizado(
              segundos: seguimiento.segundosSinDatos,
              onActualizar: () => ref.read(seguimientoProvider(detalle.id).notifier).actualizar(),
            ),
          SizedBox(
            height: 170,
            child: _MiniMapa(detalle: detalle, color: color, busetas: seguimiento.busetas),
          ),
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
                PestanaRecorrido(
                  detalle: detalle,
                  color: color,
                  onParadero: (p) => context.push('/ruta/${detalle.id}/paradero/${p.paraderoId}'),
                ),
                PestanaHorarios(rutaId: detalle.id),
                PestanaFrecuencia(rutaId: detalle.id),
                PestanaEnVivo(rutaId: detalle.id, estado: seguimiento),
              ],
            ),
          ),
        ],
      ),
    );
  }
}

/// Con este zoom o más cerca, cada paradero muestra su nombre.
const _zoomEtiquetasParaderos = 15.5;

class _MiniMapa extends ConsumerStatefulWidget {
  const _MiniMapa({required this.detalle, required this.color, required this.busetas});

  final RutaDetalle detalle;
  final Color color;
  final List<BusetaEnVivo> busetas;

  @override
  ConsumerState<_MiniMapa> createState() => _MiniMapaState();
}

class _MiniMapaState extends ConsumerState<_MiniMapa> {
  bool _verNombres = false;

  void _alMover(MapCamera camara, bool _) {
    final ver = camara.zoom >= _zoomEtiquetasParaderos;
    if (ver != _verNombres) setState(() => _verNombres = ver);
  }

  @override
  Widget build(BuildContext context) {
    final detalle = widget.detalle;
    final color = widget.color;
    final puntos = detalle.trazado;
    final ubicacion = ref.watch(ubicacionProvider).value;
    return Semantics(
      label: 'Mapa del recorrido de ${detalle.nombre}',
      child: FlutterMap(
        options: MapOptions(
          initialCameraFit: puntos.length >= 2
              ? CameraFit.coordinates(coordinates: puntos, padding: const EdgeInsets.all(28))
              : null,
          onPositionChanged: _alMover,
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
                width: _verNombres ? 120 : 16,
                height: _verNombres ? 40 : 16,
                alignment: _verNombres ? Alignment.topCenter : Alignment.center,
                child: Semantics(
                  label: 'Paradero ${p.nombre}',
                  child: _MarcaParadero(nombre: p.nombre, color: color, verNombre: _verNombres),
                ),
              ),
          ]),
          const CapaPuntosElegidos(),
          CapaUbicacionUsuario(punto: ubicacion),
          MarcadoresBusetas(busetas: widget.busetas),
        ],
      ),
    );
  }
}

class _MarcaParadero extends StatelessWidget {
  const _MarcaParadero({required this.nombre, required this.color, required this.verNombre});

  final String nombre;
  final Color color;
  final bool verNombre;

  @override
  Widget build(BuildContext context) {
    final punto = Container(
      width: 16,
      height: 16,
      decoration: BoxDecoration(
        color: Colors.white,
        shape: BoxShape.circle,
        border: Border.all(color: color, width: 3),
      ),
    );
    if (!verNombre) return punto;
    return Column(
      mainAxisSize: MainAxisSize.min,
      children: [
        punto,
        const SizedBox(height: 2),
        Container(
          padding: const EdgeInsets.symmetric(horizontal: 4, vertical: 1),
          decoration: BoxDecoration(
            color: Colors.white.withValues(alpha: 0.9),
            borderRadius: BorderRadius.circular(4),
          ),
          child: Text(
            nombre,
            maxLines: 1,
            overflow: TextOverflow.ellipsis,
            style: const TextStyle(fontSize: 11, color: Color(0xFF13271E), fontWeight: FontWeight.w600),
          ),
        ),
      ],
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
