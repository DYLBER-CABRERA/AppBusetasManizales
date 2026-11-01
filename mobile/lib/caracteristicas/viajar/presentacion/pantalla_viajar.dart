import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';

import '../../../app/widgets/banner_error.dart';
import '../../../app/widgets/vacio_con_accion.dart';
import '../../../nucleo/formato.dart';
import '../../ruta/dominio/ruta.dart';
import '../../ruta/presentacion/ruta_providers.dart';
import '../../ruta/presentacion/widgets/sello_ruta.dart';
import '../dominio/viaje.dart';
import 'barra_tramos.dart';
import 'selector_lugar.dart';
import 'viajar_provider.dart';

class PantallaViajar extends ConsumerWidget {
  const PantallaViajar({super.key});

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final estado = ref.watch(viajarProvider);
    final notificador = ref.read(viajarProvider.notifier);
    final texto = Theme.of(context).textTheme;
    final resultado = estado.resultado;

    return ListView(
      padding: const EdgeInsets.fromLTRB(16, 16, 16, 24),
      children: [
        Text('Planifica tu viaje', style: texto.titleLarge),
        const SizedBox(height: 12),
        Row(
          crossAxisAlignment: CrossAxisAlignment.center,
          children: [
            Expanded(
              child: Column(
                children: [
                  _CampoLugar(
                    etiqueta: 'Origen',
                    lugar: estado.origen,
                    pista: 'Elige el origen',
                    onTap: () async {
                      final lugar = await elegirLugar(context, titulo: 'Origen');
                      if (lugar != null) notificador.elegirOrigen(lugar);
                    },
                  ),
                  const SizedBox(height: 8),
                  _CampoLugar(
                    etiqueta: 'Destino',
                    lugar: estado.destino,
                    pista: 'Elige el destino',
                    onTap: () async {
                      final lugar = await elegirLugar(context, titulo: 'Destino');
                      if (lugar != null) notificador.elegirDestino(lugar);
                    },
                  ),
                ],
              ),
            ),
            IconButton(
              tooltip: 'Intercambiar origen y destino',
              icon: const Icon(Icons.swap_vert),
              constraints: const BoxConstraints(minWidth: 48, minHeight: 48),
              onPressed: estado.origen == null && estado.destino == null ? null : notificador.intercambiar,
            ),
          ],
        ),
        if (estado.mismoLugar) ...[
          const SizedBox(height: 8),
          Semantics(
            liveRegion: true,
            child: Text(
              'El origen y el destino son el mismo lugar. Elige uno distinto.',
              style: TextStyle(color: Theme.of(context).colorScheme.error),
            ),
          ),
        ],
        const SizedBox(height: 12),
        FilledButton(
          onPressed: estado.puedeBuscar ? notificador.buscar : null,
          child: estado.buscando
              ? const SizedBox(width: 20, height: 20, child: CircularProgressIndicator(strokeWidth: 2.5))
              : const Text('Buscar rutas'),
        ),
        if (estado.origen == null || estado.destino == null)
          Padding(
            padding: const EdgeInsets.only(top: 8),
            child: Text(
              'Elige de dónde sales y a dónde vas: tu ubicación, un lugar conocido o un punto del mapa. '
              'Solo mostramos rutas directas, sin transbordos.',
              style: texto.bodySmall,
            ),
          ),
        if (estado.error != null) ...[
          const SizedBox(height: 16),
          BannerError(mensaje: estado.error!.mensaje, onReintentar: notificador.buscar),
        ],
        if (resultado != null) ...[
          const SizedBox(height: 16),
          if (resultado.opciones.isEmpty)
            _SinOpciones(respuesta: resultado, hayCercanas: estado.cercanasAlOrigen.isNotEmpty)
          else
            for (final opcion in resultado.opciones) _TarjetaOpcion(opcion: opcion),
          if (resultado.opciones.isEmpty && estado.cercanasAlOrigen.isNotEmpty)
            _CercanasAlOrigen(rutas: estado.cercanasAlOrigen),
        ],
      ],
    );
  }
}

class _CampoLugar extends StatelessWidget {
  const _CampoLugar({
    required this.etiqueta,
    required this.lugar,
    required this.pista,
    required this.onTap,
  });

  final String etiqueta;
  final LugarViaje? lugar;
  final String pista;
  final VoidCallback onTap;

  @override
  Widget build(BuildContext context) {
    final esquema = Theme.of(context).colorScheme;
    final icono = switch (lugar?.tipo) {
      TipoLugar.ubicacion => Icons.my_location,
      TipoLugar.mapa => Icons.place_outlined,
      _ => Icons.location_on_outlined,
    };
    return Semantics(
      button: true,
      label: '$etiqueta: ${lugar?.nombre ?? 'sin elegir'}',
      excludeSemantics: true,
      child: InkWell(
        borderRadius: BorderRadius.circular(12),
        onTap: onTap,
        child: InputDecorator(
          decoration: InputDecoration(labelText: etiqueta, prefixIcon: Icon(icono)),
          child: ConstrainedBox(
            constraints: const BoxConstraints(minHeight: 24),
            child: Text(
              lugar?.nombre ?? pista,
              maxLines: 1,
              overflow: TextOverflow.ellipsis,
              style: lugar == null
                  ? TextStyle(color: esquema.onSurface.withValues(alpha: 0.7))
                  : null,
            ),
          ),
        ),
      ),
    );
  }
}

class _TarjetaOpcion extends ConsumerWidget {
  const _TarjetaOpcion({required this.opcion});

  final OpcionViaje opcion;

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final texto = Theme.of(context).textTheme;
    final rutas = ref.watch(todasLasRutasProvider).value ?? const <RutaResumen>[];
    final ruta = rutas.where((r) => r.id == opcion.rutaId).firstOrNull;
    final servicio = ruta?.servicios.where((s) => s.servicioId == opcion.servicioId).firstOrNull;
    final color = colorDeRuta(ref, opcion.rutaId);
    final nombre = ruta?.nombre ?? 'Ruta';

    return Card(
      margin: const EdgeInsets.only(bottom: 12),
      child: Padding(
        padding: const EdgeInsets.all(12),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.stretch,
          children: [
            Row(
              children: [
                SelloRuta(
                  codigo: servicio?.codigoPublico ?? (ruta?.codigoSello ?? nombre.characters.first),
                  color: color,
                ),
                const SizedBox(width: 12),
                Expanded(
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      Text('Directa · $nombre', style: texto.titleMedium),
                      if (servicio != null) Text(servicio.etiqueta, style: texto.bodySmall),
                    ],
                  ),
                ),
                Text(minutosViaje(opcion.totalMin), style: texto.titleLarge),
              ],
            ),
            const SizedBox(height: 12),
            BarraTramos(opcion: opcion, colorRuta: color),
            const SizedBox(height: 12),
            _Paso(
              icono: Icons.directions_walk,
              texto: 'Camina ${formatearDistancia(opcion.paraderoOrigen.distanciaM)} hasta '
                  '${opcion.paraderoOrigen.nombre}',
            ),
            _Paso(
              icono: Icons.directions_bus,
              texto: 'Toma ${servicio?.empresaNombre ?? 'la buseta'} y baja en ${opcion.paraderoDestino.nombre}',
            ),
            _Paso(
              icono: Icons.directions_walk,
              texto: 'Camina ${formatearDistancia(opcion.paraderoDestino.distanciaM)} hasta tu destino',
            ),
            const SizedBox(height: 8),
            Wrap(
              spacing: 8,
              children: [
                OutlinedButton(
                  onPressed: () => context.push('/ruta/${opcion.rutaId}'),
                  child: const Text('Ver ruta'),
                ),
                OutlinedButton(
                  onPressed: () =>
                      context.push('/ruta/${opcion.rutaId}/paradero/${opcion.paraderoOrigen.paraderoId}'),
                  child: const Text('¿Cuándo llega?'),
                ),
              ],
            ),
          ],
        ),
      ),
    );
  }
}

class _Paso extends StatelessWidget {
  const _Paso({required this.icono, required this.texto});

  final IconData icono;
  final String texto;

  @override
  Widget build(BuildContext context) => Padding(
        padding: const EdgeInsets.symmetric(vertical: 2),
        child: Row(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Icon(icono, size: 18),
            const SizedBox(width: 8),
            Expanded(child: Text(texto)),
          ],
        ),
      );
}

class _SinOpciones extends StatelessWidget {
  const _SinOpciones({required this.respuesta, required this.hayCercanas});

  final RespuestaPlanificacion respuesta;
  final bool hayCercanas;

  @override
  Widget build(BuildContext context) {
    final cercano = respuesta.paraderoMasCercano;
    return VacioConAccion(
      icono: Icons.directions_bus_outlined,
      titulo: 'No encontramos una ruta directa',
      causa: [
        respuesta.motivo ?? 'No hay una ruta directa entre esos lugares.',
        if (cercano != null)
          'El paradero más cercano es ${cercano.nombre}, a ${formatearDistancia(cercano.distanciaM)}.',
        if (hayCercanas)
          'Planificamos de paradero a paradero: solo se sube y se baja en paraderos.',
      ].join(' '),
    );
  }
}

/// Rutas que pasan junto al origen aunque su paradero quede lejos (la planificación
/// solo ofrece paraderos a la distancia de caminata).
class _CercanasAlOrigen extends ConsumerWidget {
  const _CercanasAlOrigen({required this.rutas});

  final List<RutaCercanaAlOrigen> rutas;

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final texto = Theme.of(context).textTheme;
    return Column(
      crossAxisAlignment: CrossAxisAlignment.stretch,
      children: [
        Text('Rutas que pasan cerca de tu origen', style: texto.titleMedium),
        const SizedBox(height: 8),
        for (final cercana in rutas)
          Card(
            margin: const EdgeInsets.only(bottom: 8),
            child: Padding(
              padding: const EdgeInsets.all(12),
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.stretch,
                children: [
                  Row(
                    children: [
                      SelloRuta(codigo: cercana.ruta.codigoSello, color: colorDeRuta(ref, cercana.ruta.id)),
                      const SizedBox(width: 12),
                      Expanded(
                        child: Column(
                          crossAxisAlignment: CrossAxisAlignment.start,
                          children: [
                            Text(cercana.ruta.nombre, style: texto.titleMedium),
                            Text(
                              [
                                if (cercana.ruta.distanciaM != null)
                                  'Pasa a ${formatearDistancia(cercana.ruta.distanciaM!)} de ti.',
                                if (cercana.paradero != null)
                                  'Su paradero más cercano es ${cercana.paradero!.nombre}, '
                                      'a ${formatearDistancia(cercana.paradero!.distanciaM)}.',
                              ].join(' '),
                            ),
                          ],
                        ),
                      ),
                    ],
                  ),
                  const SizedBox(height: 8),
                  Wrap(
                    spacing: 8,
                    children: [
                      OutlinedButton(
                        onPressed: () => context.push('/ruta/${cercana.ruta.id}'),
                        child: const Text('Ver ruta'),
                      ),
                      if (cercana.paradero != null)
                        OutlinedButton(
                          onPressed: () => context
                              .push('/ruta/${cercana.ruta.id}/paradero/${cercana.paradero!.paraderoId}'),
                          child: const Text('¿Cuándo llega?'),
                        ),
                    ],
                  ),
                ],
              ),
            ),
          ),
      ],
    );
  }
}
