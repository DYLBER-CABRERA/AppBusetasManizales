import 'package:flutter/material.dart';
import 'package:flutter_map/flutter_map.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../dominio/viaje.dart';
import 'viajar_provider.dart';

/// Marca en un `FlutterMap` los puntos que el pasajero eligió a mano en Viajar como origen
/// o destino. Es otro marcador (pin con etiqueta), distinto del punto azul de «tu ubicación».
class CapaPuntosElegidos extends ConsumerWidget {
  const CapaPuntosElegidos({super.key});

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final estado = ref.watch(viajarProvider);
    return MarkerLayer(markers: [
      for (final (etiqueta, lugar) in [('Origen', estado.origen), ('Destino', estado.destino)])
        if (lugar != null && lugar.tipo == TipoLugar.mapa && lugar.punto != null)
          Marker(
            point: lugar.punto!,
            width: 72,
            height: 72,
            alignment: Alignment.topCenter,
            child: Semantics(
              label: '$etiqueta elegido en el mapa',
              child: _PinElegido(etiqueta: etiqueta),
            ),
          ),
    ]);
  }
}

/// Origen morado y destino rojo, ambos con contraste suficiente para el texto blanco.
const _colorOrigen = Color(0xFF6A1B9A);
const _colorDestino = Color(0xFFC62828);

class _PinElegido extends StatelessWidget {
  const _PinElegido({required this.etiqueta});

  final String etiqueta;

  @override
  Widget build(BuildContext context) {
    final tinta = etiqueta == 'Origen' ? _colorOrigen : _colorDestino;
    return Column(
      mainAxisSize: MainAxisSize.min,
      children: [
        Container(
          padding: const EdgeInsets.symmetric(horizontal: 6, vertical: 1),
          decoration: BoxDecoration(color: tinta, borderRadius: BorderRadius.circular(8)),
          child: Text(
            etiqueta,
            style: const TextStyle(color: Colors.white, fontSize: 11, fontWeight: FontWeight.w700),
          ),
        ),
        Icon(Icons.location_on, size: 38, color: tinta, shadows: const [Shadow(blurRadius: 4, color: Colors.black38)]),
      ],
    );
  }
}
