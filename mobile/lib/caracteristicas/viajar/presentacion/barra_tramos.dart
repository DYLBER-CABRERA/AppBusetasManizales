import 'package:flutter/material.dart';

import '../dominio/viaje.dart';

/// Barra de tramos del viaje (COM-08): caminata · espera · buseta. Cada tramo lleva
/// ícono y minutos en la leyenda, así la información no depende solo del color.
class BarraTramos extends StatelessWidget {
  const BarraTramos({super.key, required this.opcion, required this.colorRuta});

  final OpcionViaje opcion;
  final Color colorRuta;

  static String _enteros(double min) => '${min.round()}';

  @override
  Widget build(BuildContext context) {
    final esquema = Theme.of(context).colorScheme;
    final texto = Theme.of(context).textTheme.bodySmall;
    final tramos = [
      (opcion.caminataMin, esquema.onSurface.withValues(alpha: 0.55)),
      (opcion.esperaMin, esquema.onSurface.withValues(alpha: 0.2)),
      (opcion.busMin, colorRuta),
    ];
    final etiqueta = '${_enteros(opcion.caminataMin)} min a pie, '
        '${_enteros(opcion.esperaMin)} min de espera, ${_enteros(opcion.busMin)} min en buseta';
    return Semantics(
      label: etiqueta,
      excludeSemantics: true,
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          ClipRRect(
            borderRadius: BorderRadius.circular(6),
            child: Row(
              children: [
                for (final (minutos, color) in tramos)
                  // Un tramo de 0 min no se dibuja; el resto conserva su proporción.
                  if (minutos > 0)
                    Expanded(
                      flex: (minutos * 10).round().clamp(1, 100000),
                      child: Container(height: 12, color: color),
                    ),
              ],
            ),
          ),
          const SizedBox(height: 6),
          Wrap(
            spacing: 12,
            runSpacing: 2,
            children: [
              _Leyenda(Icons.directions_walk, '${_enteros(opcion.caminataMin)} a pie', texto),
              _Leyenda(Icons.schedule, '${_enteros(opcion.esperaMin)} espera', texto),
              _Leyenda(Icons.directions_bus, '${_enteros(opcion.busMin)} bus', texto),
            ],
          ),
        ],
      ),
    );
  }
}

class _Leyenda extends StatelessWidget {
  const _Leyenda(this.icono, this.texto, this.estilo);

  final IconData icono;
  final String texto;
  final TextStyle? estilo;

  @override
  Widget build(BuildContext context) => Row(
        mainAxisSize: MainAxisSize.min,
        children: [Icon(icono, size: 16), const SizedBox(width: 4), Text(texto, style: estilo)],
      );
}
