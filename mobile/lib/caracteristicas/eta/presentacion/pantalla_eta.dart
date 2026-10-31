import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';

import '../../../app/banner_ejemplo.dart';
import '../../../app/widgets/async_vista.dart';
import '../../../app/widgets/vacio_con_accion.dart';
import '../../ruta/presentacion/ruta_providers.dart';
import '../../ruta/presentacion/widgets/banner_desactualizado.dart';
import '../../ruta/presentacion/widgets/sello_ruta.dart';
import '../dominio/eta.dart';
import 'boton_avisarme.dart';
import 'eta_provider.dart';

/// ETA de una parada: una tarjeta por servicio, con su fuente (GPS, horario o sin datos).
class PantallaEta extends ConsumerWidget {
  const PantallaEta({super.key, required this.rutaId, required this.paraderoId});

  final String rutaId;
  final String paraderoId;

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final parada = (rutaId: rutaId, paraderoId: paraderoId);
    final eta = ref.watch(etaProvider(parada));
    final nombre = ref
        .watch(rutaDetalleProvider(rutaId))
        .value
        ?.paraderos
        .where((p) => p.paraderoId == paraderoId)
        .firstOrNull
        ?.nombre;

    return Scaffold(
      appBar: AppBar(
        title: Text(tituloParadero(nombre)),
        leading: BackButton(
          onPressed: () => context.canPop() ? context.pop() : context.go('/ruta/$rutaId'),
        ),
        actions: [
          IconButton(
            tooltip: 'Actualizar',
            icon: const Icon(Icons.refresh),
            constraints: const BoxConstraints(minWidth: 48, minHeight: 48),
            onPressed: () => ref.invalidate(etaProvider(parada)),
          ),
        ],
      ),
      body: Column(
        children: [
          const BannerEjemplo(),
          Expanded(
            child: ListView(
              padding: const EdgeInsets.only(bottom: 24),
              children: [
                AsyncVista<RespuestaEta>(
                  valor: eta,
                  onReintentar: () => ref.invalidate(etaProvider(parada)),
                  datos: (respuesta) => _Resultados(rutaId: rutaId, respuesta: respuesta),
                ),
                BotonAvisarme(rutaId: rutaId, paraderoId: paraderoId),
              ],
            ),
          ),
        ],
      ),
    );
  }
}

class _Resultados extends ConsumerWidget {
  const _Resultados({required this.rutaId, required this.respuesta});

  final String rutaId;
  final RespuestaEta respuesta;

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    if (respuesta.resultados.isEmpty) {
      return const VacioConAccion(
        titulo: 'No hay servicios para esta parada.',
        causa: 'Revisa el horario de la ruta.',
        icono: Icons.directions_bus_outlined,
      );
    }
    final color = colorDeRuta(ref, rutaId);
    return Column(
      crossAxisAlignment: CrossAxisAlignment.stretch,
      children: [
        for (final resultado in respuesta.resultados) TarjetaEta(resultado: resultado, color: color),
      ],
    );
  }
}

/// Tarjeta de ETA (COM-09): GPS (minutos) · horario (rango + aviso) · sin datos.
class TarjetaEta extends StatelessWidget {
  const TarjetaEta({super.key, required this.resultado, required this.color});

  final ResultadoEta resultado;
  final Color color;

  @override
  Widget build(BuildContext context) {
    final texto = Theme.of(context).textTheme;
    final esquema = Theme.of(context).colorScheme;
    final r = resultado;
    final principal = r.principal;

    final semantica = [
      r.titulo,
      if (principal != null) principal else r.mensaje ?? 'Sin estimación',
      if (r.fuente == FuenteEta.gps && r.busetaNumeroLateral != null)
        'Buseta ${r.busetaNumeroLateral} viene hacia aquí',
      r.lineaFuente,
    ].join('. ');

    return Semantics(
      container: true,
      label: semantica,
      child: ExcludeSemantics(
        child: Card(
          margin: const EdgeInsets.fromLTRB(16, 12, 16, 0),
          elevation: 0,
          color: esquema.surface,
          shape: RoundedRectangleBorder(
            borderRadius: BorderRadius.circular(16),
            side: BorderSide(color: esquema.onSurface.withValues(alpha: 0.2)),
          ),
          child: Padding(
            padding: const EdgeInsets.all(16),
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Row(children: [
                  SelloRuta(
                    codigo: r.codigoPublico ?? String.fromCharCode(r.empresa.runes.first),
                    color: color,
                    tamano: 40,
                  ),
                  const SizedBox(width: 12),
                  Expanded(child: Text(r.titulo, style: texto.titleMedium)),
                ]),
                const SizedBox(height: 12),
                if (principal != null)
                  Text(principal, style: texto.headlineMedium?.copyWith(fontWeight: FontWeight.w800))
                else
                  Text(r.mensaje ?? 'Sin estimación por ahora.', style: texto.titleMedium),
                if (r.fuente == FuenteEta.gps && r.busetaNumeroLateral != null) ...[
                  const SizedBox(height: 4),
                  Text('Buseta ${r.busetaNumeroLateral} viene hacia aquí', style: texto.bodyLarge),
                ],
                const SizedBox(height: 4),
                Text(r.lineaFuente, style: texto.bodyMedium),
                if (r.fuente == FuenteEta.horario && r.mensaje != null) ...[
                  const SizedBox(height: 12),
                  _AvisoHorario(mensaje: r.mensaje!),
                ],
              ],
            ),
          ),
        ),
      ),
    );
  }
}

class _AvisoHorario extends StatelessWidget {
  const _AvisoHorario({required this.mensaje});

  final String mensaje;

  @override
  Widget build(BuildContext context) {
    return Container(
      padding: const EdgeInsets.all(12),
      decoration: BoxDecoration(
        color: BannerDesactualizado.fondo,
        borderRadius: BorderRadius.circular(12),
        border: Border.all(color: BannerDesactualizado.borde),
      ),
      child: Row(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          const Icon(Icons.info_outline, color: BannerDesactualizado.borde),
          const SizedBox(width: 8),
          Expanded(
            child: Text(mensaje, style: const TextStyle(color: BannerDesactualizado.tinta)),
          ),
        ],
      ),
    );
  }
}
