import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../../../app/widgets/banner_error.dart';
import '../../../app/widgets/esqueleto.dart';
import '../../../app/widgets/vacio_con_accion.dart';
import '../../../nucleo/conexion_ws.dart';
import '../../../nucleo/reloj.dart';
import '../dominio/seguimiento.dart';
import '../dominio/servicio_hoy.dart';
import 'ruta_providers.dart';
import 'seguimiento_provider.dart';
import 'widgets/banner_desactualizado.dart';
import 'widgets/marcadores_busetas.dart';

/// Pestaña **En vivo**: lista de busetas con su estado. Recibe el estado ya
/// escuchado por la ficha (que es quien abre y cierra el socket).
class PestanaEnVivo extends ConsumerWidget {
  const PestanaEnVivo({super.key, required this.rutaId, required this.estado});

  final String rutaId;
  final EstadoSeguimiento estado;

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final notificador = ref.read(seguimientoProvider(rutaId).notifier);
    final horarios = ref.watch(horariosRutaProvider(rutaId)).value;
    final ahora = ref.watch(relojProvider)();

    final avisos = <Widget>[
      if (estado.error != null)
        BannerError(mensaje: estado.error!.mensaje, onReintentar: notificador.actualizar),
      if (estado.desactualizado)
        BannerDesactualizado(
          segundos: estado.segundosSinDatos,
          onActualizar: notificador.actualizar,
        ),
      if (estado.estadoWs != EstadoWs.conectado && estado.tieneDatos && estado.error == null)
        const _AvisoReconectando(),
    ];

    if (!estado.tieneDatos) {
      return ListView(children: [
        ...avisos,
        if (estado.error == null) const EsqueletoLista(),
      ]);
    }

    if (estado.busetas.isEmpty) {
      final hoy = horarios == null ? null : servicioHoy(horarios, horaBogota(ahora));
      final sinDatosGps = estado.unidadesEnServicio! > 0;
      return ListView(children: [
        ...avisos,
        VacioConAccion(
          titulo: sinDatosGps
              ? 'Esta ruta no tiene ubicación de busetas en este momento.'
              : 'No hay busetas en servicio en esta ruta en este momento.',
          causa: sinDatosGps
              ? 'Hay ${estado.unidadesEnServicio} en servicio, pero sin GPS. Consulta el horario y la frecuencia.'
              : hoy?.detalle ?? 'Revisa el horario de la ruta.',
          icono: Icons.directions_bus_outlined,
          etiquetaAccion: 'Actualizar',
          onAccion: notificador.actualizar,
        ),
      ]);
    }

    return ListView(
      padding: const EdgeInsets.only(bottom: 24),
      children: [
        ...avisos,
        Padding(
          padding: const EdgeInsets.fromLTRB(16, 12, 16, 4),
          child: Text(
            estado.unidadesEnServicio == estado.busetas.length
                ? '${estado.busetas.length} en servicio'
                : '${estado.busetas.length} con ubicación · ${estado.unidadesEnServicio} en servicio',
            style: Theme.of(context).textTheme.titleMedium,
          ),
        ),
        for (final b in estado.busetas) _FilaBuseta(buseta: b, ahora: ahora),
      ],
    );
  }
}

class _AvisoReconectando extends StatelessWidget {
  const _AvisoReconectando();

  @override
  Widget build(BuildContext context) => const Padding(
        padding: EdgeInsets.fromLTRB(16, 8, 16, 0),
        child: Row(children: [
          SizedBox(width: 16, height: 16, child: CircularProgressIndicator(strokeWidth: 2)),
          SizedBox(width: 12),
          Expanded(child: Text('Reconectando… mientras tanto actualizamos cada pocos segundos.')),
        ]),
      );
}

class _FilaBuseta extends StatelessWidget {
  const _FilaBuseta({required this.buseta, required this.ahora});

  final BusetaEnVivo buseta;
  final DateTime ahora;

  @override
  Widget build(BuildContext context) {
    final texto = Theme.of(context).textTheme;
    final esquema = Theme.of(context).colorScheme;
    final segundos = ahora.difference(buseta.reportadaEn).inSeconds;
    final detalle = buseta.sinSenal
        ? (buseta.mensaje ?? 'Ubicación no disponible. Última señal hace más de 60 s.')
        : 'Reportó hace ${segundos < 0 ? 0 : segundos} s'
            '${buseta.velocidadKmh == null ? '' : ' · ${buseta.velocidadKmh!.round()} km/h'}';
    return Semantics(
      label: 'Buseta ${buseta.numeroLateral}, ${buseta.empresa}. '
          '${buseta.sinSenal ? 'Sin señal' : 'En ruta'}. $detalle',
      excludeSemantics: true,
      child: ConstrainedBox(
        constraints: const BoxConstraints(minHeight: 56),
        child: Padding(
          padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 8),
          child: Row(
            children: [
              SizedBox(width: anchoMarcaBuseta, height: 34, child: MarcaBuseta(buseta: buseta)),
              const SizedBox(width: 12),
              Expanded(
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Text('${buseta.empresa} · ${buseta.sinSenal ? 'Sin señal' : 'En ruta'}',
                        style: texto.titleMedium),
                    Text(detalle,
                        style: texto.bodyMedium?.copyWith(
                          color: buseta.sinSenal ? esquema.error : null,
                        )),
                  ],
                ),
              ),
            ],
          ),
        ),
      ),
    );
  }
}
