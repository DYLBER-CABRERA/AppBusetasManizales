import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../../../../nucleo/formato.dart';
import '../../dominio/ruta.dart';
import '../ruta_providers.dart';
import 'sello_ruta.dart';

/// Fila de lista de ruta (COM-04): sello, nombre, empresas, distancia y, si se conoce,
/// «N en servicio» ([unidades] viene del seguimiento en vivo; `null` = no se muestra).
class FilaRuta extends ConsumerWidget {
  const FilaRuta({super.key, required this.ruta, required this.onTap, this.unidades});

  final RutaResumen ruta;
  final VoidCallback onTap;
  final int? unidades;

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final color = colorDeRuta(ref, ruta.id);
    final texto = Theme.of(context).textTheme;

    final detalles = <String>[
      ruta.empresas,
      if (ruta.distanciaM != null) 'a ${formatearDistancia(ruta.distanciaM!)}',
    ].where((t) => t.isNotEmpty).join(' · ');
    final servicio = unidades == null
        ? null
        : unidades == 0
            ? 'Sin busetas en servicio ahora'
            : '$unidades en servicio';

    return Semantics(
      button: true,
      label: 'Ruta ${ruta.codigoSello} ${ruta.nombre}. $detalles${servicio == null ? '' : '. $servicio'}',
      excludeSemantics: true,
      child: InkWell(
        onTap: onTap,
        child: ConstrainedBox(
          constraints: const BoxConstraints(minHeight: 56),
          child: Padding(
            padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 8),
            child: Row(
              children: [
                SelloRuta(codigo: ruta.codigoSello, color: color),
                const SizedBox(width: 12),
                Expanded(
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      Text(ruta.nombre, style: texto.titleMedium),
                      if (detalles.isNotEmpty) Text(detalles, style: texto.bodyMedium),
                      if (servicio != null) Text(servicio, style: texto.bodySmall),
                    ],
                  ),
                ),
                const Icon(Icons.chevron_right),
              ],
            ),
          ),
        ),
      ),
    );
  }
}
