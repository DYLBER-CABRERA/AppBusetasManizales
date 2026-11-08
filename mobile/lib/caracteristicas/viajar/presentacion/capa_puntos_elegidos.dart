import 'package:flutter/material.dart';
import 'package:flutter_map/flutter_map.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:latlong2/latlong.dart';

import '../../buscar/presentacion/buscar_provider.dart';
import '../dominio/viaje.dart';
import 'viajar_provider.dart';

/// Marca en un `FlutterMap` los puntos que el pasajero eligió a mano en Viajar como origen
/// o destino. Es otro marcador (pin con etiqueta), distinto del punto azul de «tu ubicación».
class CapaPuntosElegidos extends ConsumerWidget {
  const CapaPuntosElegidos({super.key});

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final estado = ref.watch(viajarProvider);
    final busqueda = ref.watch(busquedaProvider);
    final hitoBuscado = busqueda is BusquedaDeHito ? busqueda.hito : null;
    return MarkerLayer(markers: [
      // Lugar elegido en Buscar: bandera verde con su nombre.
      if (hitoBuscado != null)
        Marker(
          point: LatLng(hitoBuscado.lat, hitoBuscado.lng),
          width: 150,
          height: 72,
          alignment: Alignment.topCenter,
          child: Semantics(
            label: 'Lugar buscado: ${hitoBuscado.nombre}',
            child: _PinElegido(
              etiqueta: hitoBuscado.nombre,
              color: Theme.of(context).colorScheme.primary,
              esHito: true,
            ),
          ),
        ),
      for (final (etiqueta, lugar) in [('Origen', estado.origen), ('Destino', estado.destino)])
        if (lugar != null && lugar.tipo != TipoLugar.ubicacion && lugar.punto != null)
          Marker(
            point: lugar.punto!,
            width: lugar.tipo == TipoLugar.hito ? 150 : 72,
            height: 72,
            alignment: Alignment.topCenter,
            child: Semantics(
              label: lugar.tipo == TipoLugar.hito
                  ? '$etiqueta: ${lugar.nombre}'
                  : '$etiqueta elegido en el mapa',
              child: _PinElegido(
                etiqueta: lugar.tipo == TipoLugar.hito ? '$etiqueta · ${lugar.nombre}' : etiqueta,
                color: etiqueta == 'Origen' ? _colorOrigen : _colorDestino,
                esHito: lugar.tipo == TipoLugar.hito,
              ),
            ),
          ),
    ]);
  }
}

/// Origen morado y destino rojo, ambos con contraste suficiente para el texto blanco.
const _colorOrigen = Color(0xFF6A1B9A);
const _colorDestino = Color(0xFFC62828);

class _PinElegido extends StatelessWidget {
  const _PinElegido({required this.etiqueta, required this.color, required this.esHito});

  final String etiqueta;
  final Color color;
  final bool esHito;

  @override
  Widget build(BuildContext context) {
    final tinta = color;
    return Column(
      mainAxisSize: MainAxisSize.min,
      children: [
        Container(
          padding: const EdgeInsets.symmetric(horizontal: 6, vertical: 1),
          decoration: BoxDecoration(color: tinta, borderRadius: BorderRadius.circular(8)),
          child: Text(
            etiqueta,
            maxLines: 1,
            overflow: TextOverflow.ellipsis,
            style: const TextStyle(color: Colors.white, fontSize: 11, fontWeight: FontWeight.w700),
          ),
        ),
        // Hito conocido: bandera; punto libre del mapa: pin.
        Icon(
          esHito ? Icons.flag : Icons.location_on,
          size: 38,
          color: tinta,
          shadows: const [Shadow(blurRadius: 4, color: Colors.black38)],
        ),
      ],
    );
  }
}
