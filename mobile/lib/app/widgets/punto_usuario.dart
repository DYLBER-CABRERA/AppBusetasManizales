import 'package:flutter/material.dart';
import 'package:flutter_map/flutter_map.dart';
import 'package:latlong2/latlong.dart';

/// Punto azul de «tu ubicación», el mismo en el mapa principal y en la ficha de ruta.
class PuntoUsuario extends StatelessWidget {
  const PuntoUsuario({super.key});

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

/// Marcador de la ubicación del pasajero para un `FlutterMap`; no dibuja nada si [punto] es `null`
/// (permiso negado o sin señal). La ubicación no se guarda: solo se pinta.
class CapaUbicacionUsuario extends StatelessWidget {
  const CapaUbicacionUsuario({super.key, required this.punto});

  final LatLng? punto;

  @override
  Widget build(BuildContext context) => MarkerLayer(markers: [
        if (punto != null)
          Marker(
            point: punto!,
            width: 28,
            height: 28,
            child: Semantics(label: 'Tu ubicación', child: const PuntoUsuario()),
          ),
      ]);
}
