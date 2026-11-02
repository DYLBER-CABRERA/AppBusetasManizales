import 'package:flutter/material.dart';
import 'package:flutter_map/flutter_map.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:latlong2/latlong.dart';

import '../../../app/widgets/capas_osm.dart';
import '../../../nucleo/ubicacion.dart';

/// Pantalla completa para elegir un punto tocando el mapa. Devuelve el [LatLng].
class SelectorPuntoMapa extends ConsumerStatefulWidget {
  const SelectorPuntoMapa({super.key, required this.titulo});

  final String titulo;

  @override
  ConsumerState<SelectorPuntoMapa> createState() => _SelectorPuntoMapaState();
}

class _SelectorPuntoMapaState extends ConsumerState<SelectorPuntoMapa> {
  LatLng? _punto;

  @override
  Widget build(BuildContext context) {
    final centro = ref.watch(ubicacionProvider).value ?? centroManizales;
    final esquema = Theme.of(context).colorScheme;
    return Scaffold(
      appBar: AppBar(title: Text(widget.titulo)),
      body: Stack(
        children: [
          Semantics(
            label: 'Mapa: toca para elegir un punto',
            child: FlutterMap(
              options: MapOptions(
                initialCenter: centro,
                initialZoom: 15,
                onTap: (_, punto) => setState(() => _punto = punto),
              ),
              children: [
                ...capasBaseOsm(),
                if (_punto != null)
                  MarkerLayer(markers: [
                    Marker(
                      point: _punto!,
                      width: 48,
                      height: 48,
                      alignment: Alignment.topCenter,
                      child: Icon(Icons.place, size: 44, color: esquema.primary),
                    ),
                  ]),
              ],
            ),
          ),
          Positioned(
            left: 16,
            right: 16,
            bottom: 16,
            child: SafeArea(
              child: Card(
                child: Padding(
                  padding: const EdgeInsets.all(12),
                  child: Column(
                    mainAxisSize: MainAxisSize.min,
                    crossAxisAlignment: CrossAxisAlignment.stretch,
                    children: [
                      Text(
                        _punto == null ? 'Toca el mapa para marcar el punto.' : 'Punto marcado.',
                        textAlign: TextAlign.center,
                      ),
                      const SizedBox(height: 8),
                      FilledButton(
                        onPressed: _punto == null ? null : () => Navigator.of(context).pop(_punto),
                        child: const Text('Usar este punto'),
                      ),
                    ],
                  ),
                ),
              ),
            ),
          ),
        ],
      ),
    );
  }
}
