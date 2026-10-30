import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../../../app/widgets/async_vista.dart';
import '../dominio/horarios.dart';
import '../dominio/ruta.dart';
import 'ruta_providers.dart';
import 'widgets/aviso_tarjeta.dart';

const textoPendiente = 'Información pendiente de actualización';

/// Pestaña **Recorrido**: avisos vigentes y paraderos en orden.
class PestanaRecorrido extends StatelessWidget {
  const PestanaRecorrido({super.key, required this.detalle, required this.color});

  final RutaDetalle detalle;
  final Color color;

  @override
  Widget build(BuildContext context) {
    final texto = Theme.of(context).textTheme;
    final paraderos = detalle.paraderos;
    return ListView(
      padding: const EdgeInsets.only(bottom: 24),
      children: [
        for (final aviso in detalle.avisos)
          AvisoTarjeta(
            origen: aviso.origen,
            titulo: aviso.titulo,
            cuerpo: aviso.cuerpo,
            empresaNombre: aviso.empresaNombre,
          ),
        if (detalle.descripcion != null)
          Padding(
            padding: const EdgeInsets.fromLTRB(16, 8, 16, 0),
            child: Text(detalle.descripcion!, style: texto.bodyMedium),
          ),
        const SizedBox(height: 8),
        if (paraderos.isEmpty)
          const Padding(
            padding: EdgeInsets.all(16),
            child: Text('Esta ruta todavía no tiene paraderos registrados.'),
          ),
        for (var i = 0; i < paraderos.length; i++)
          _FilaParadero(
            parada: paraderos[i],
            color: color,
            primera: i == 0,
            ultima: i == paraderos.length - 1,
          ),
      ],
    );
  }
}

class _FilaParadero extends StatelessWidget {
  const _FilaParadero({
    required this.parada,
    required this.color,
    required this.primera,
    required this.ultima,
  });

  final ParadaEnRuta parada;
  final Color color;
  final bool primera;
  final bool ultima;

  @override
  Widget build(BuildContext context) {
    return Semantics(
      label: 'Paradero ${parada.orden}: ${parada.nombre}',
      excludeSemantics: true,
      child: IntrinsicHeight(
        child: Row(
          crossAxisAlignment: CrossAxisAlignment.stretch,
          children: [
            SizedBox(
              width: 56,
              child: Column(
                children: [
                  Expanded(
                    child: Container(width: 3, color: primera ? Colors.transparent : color),
                  ),
                  Container(
                    width: 16,
                    height: 16,
                    decoration: BoxDecoration(
                      color: Theme.of(context).colorScheme.surface,
                      shape: BoxShape.circle,
                      border: Border.all(color: color, width: 4),
                    ),
                  ),
                  Expanded(
                    child: Container(width: 3, color: ultima ? Colors.transparent : color),
                  ),
                ],
              ),
            ),
            Expanded(
              child: Padding(
                padding: const EdgeInsets.symmetric(vertical: 14),
                child: Text(parada.nombre, style: Theme.of(context).textTheme.bodyLarge),
              ),
            ),
          ],
        ),
      ),
    );
  }
}

/// Pestaña **Horarios**: por empresa, una fila por tipo de día; hoy resaltado.
class PestanaHorarios extends ConsumerWidget {
  const PestanaHorarios({super.key, required this.rutaId});

  final String rutaId;

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final valor = ref.watch(horariosRutaProvider(rutaId));
    return ListView(
      padding: const EdgeInsets.only(bottom: 24),
      children: [
        AsyncVista<HorariosRuta>(
          valor: valor,
          onReintentar: () => ref.invalidate(horariosRutaProvider(rutaId)),
          datos: (horarios) => Column(
            crossAxisAlignment: CrossAxisAlignment.stretch,
            children: [
              for (final servicio in horarios.servicios)
                _TablaHorarios(servicio: servicio, hoy: horarios.tipoDiaHoy),
              if (horarios.servicios.isEmpty)
                const Padding(padding: EdgeInsets.all(16), child: Text(textoPendiente)),
            ],
          ),
        ),
      ],
    );
  }
}

class _TablaHorarios extends StatelessWidget {
  const _TablaHorarios({required this.servicio, required this.hoy});

  final HorariosDeServicio servicio;
  final TipoDia hoy;

  @override
  Widget build(BuildContext context) {
    final texto = Theme.of(context).textTheme;
    final estilo = texto.labelMedium?.copyWith(fontWeight: FontWeight.w700);
    return Padding(
      padding: const EdgeInsets.fromLTRB(16, 12, 16, 4),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Semantics(header: true, child: Text(servicio.titulo, style: texto.titleMedium)),
          const SizedBox(height: 8),
          Row(children: [
            Expanded(flex: 4, child: Text('Día', style: estilo)),
            Expanded(flex: 2, child: Text('Primera', style: estilo)),
            Expanded(flex: 2, child: Text('Última', style: estilo)),
            Expanded(flex: 2, child: Text('Cierre', style: estilo)),
          ]),
          for (final (tipo, horario) in servicio.filas)
            _FilaHorario(tipo: tipo, horario: horario, esHoy: tipo == hoy),
        ],
      ),
    );
  }
}

class _FilaHorario extends StatelessWidget {
  const _FilaHorario({required this.tipo, required this.horario, required this.esHoy});

  final TipoDia tipo;
  final Horario? horario;
  final bool esHoy;

  @override
  Widget build(BuildContext context) {
    final esquema = Theme.of(context).colorScheme;
    final etiqueta = esHoy ? '${tipo.etiqueta} (hoy)' : tipo.etiqueta;
    final celdas = horario == null
        ? [Expanded(flex: 6, child: Text(textoPendiente))]
        : [
            Expanded(flex: 2, child: Text(horario!.primeraSalida)),
            Expanded(flex: 2, child: Text(horario!.ultimaSalida)),
            Expanded(flex: 2, child: Text(horario!.cierre ?? '—')),
          ];
    return Container(
      constraints: const BoxConstraints(minHeight: 44),
      margin: const EdgeInsets.only(top: 4),
      padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 8),
      decoration: BoxDecoration(
        color: esHoy ? esquema.primary.withValues(alpha: 0.14) : null,
        borderRadius: BorderRadius.circular(8),
        border: esHoy ? Border.all(color: esquema.primary, width: 1.5) : null,
      ),
      child: Row(
        children: [
          Expanded(
            flex: 4,
            child: Text(etiqueta, style: TextStyle(fontWeight: esHoy ? FontWeight.w700 : null)),
          ),
          ...celdas,
        ],
      ),
    );
  }
}

/// Pestaña **Frecuencia**: franjas por tipo de día, con rango «De 10 a 15 min».
class PestanaFrecuencia extends ConsumerWidget {
  const PestanaFrecuencia({super.key, required this.rutaId});

  final String rutaId;

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final valor = ref.watch(frecuenciasRutaProvider(rutaId));
    final hoy = ref.watch(horariosRutaProvider(rutaId)).value?.tipoDiaHoy;
    return ListView(
      padding: const EdgeInsets.only(bottom: 24),
      children: [
        AsyncVista<FrecuenciasRuta>(
          valor: valor,
          onReintentar: () => ref.invalidate(frecuenciasRutaProvider(rutaId)),
          datos: (frecuencias) => Column(
            crossAxisAlignment: CrossAxisAlignment.stretch,
            children: [
              for (final servicio in frecuencias.servicios)
                _FrecuenciasServicio(servicio: servicio, hoy: hoy),
              if (frecuencias.servicios.isEmpty)
                const Padding(padding: EdgeInsets.all(16), child: Text(textoPendiente)),
            ],
          ),
        ),
      ],
    );
  }
}

class _FrecuenciasServicio extends StatelessWidget {
  const _FrecuenciasServicio({required this.servicio, required this.hoy});

  final FrecuenciasDeServicio servicio;
  final TipoDia? hoy;

  @override
  Widget build(BuildContext context) {
    final texto = Theme.of(context).textTheme;
    final esquema = Theme.of(context).colorScheme;
    return Padding(
      padding: const EdgeInsets.fromLTRB(16, 12, 16, 4),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Semantics(header: true, child: Text(servicio.empresaNombre, style: texto.titleMedium)),
          for (final tipo in TipoDia.values) ...[
            const SizedBox(height: 10),
            Text(
              hoy == tipo ? '${tipo.etiqueta} (hoy)' : tipo.etiqueta,
              style: texto.labelLarge?.copyWith(
                fontWeight: FontWeight.w700,
                color: hoy == tipo ? esquema.primary : null,
              ),
            ),
            if (servicio.deTipoDia(tipo).isEmpty)
              const Padding(padding: EdgeInsets.only(top: 4), child: Text(textoPendiente))
            else
              for (final f in servicio.deTipoDia(tipo))
                Padding(
                  padding: const EdgeInsets.only(top: 4),
                  child: Row(children: [
                    SizedBox(width: 110, child: Text('${f.franjaInicio}–${f.franjaFin}')),
                    Expanded(child: Text(f.texto + (f.nota == null ? '' : ' · ${f.nota}'))),
                  ]),
                ),
          ],
        ],
      ),
    );
  }
}
