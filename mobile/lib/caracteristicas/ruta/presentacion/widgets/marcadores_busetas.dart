import 'package:flutter/foundation.dart';
import 'package:flutter/material.dart';
import 'package:flutter_map/flutter_map.dart';
import 'package:latlong2/latlong.dart';

import '../../../../app/tema.dart';
import '../../dominio/interpolacion.dart';
import '../../dominio/seguimiento.dart';

/// Ancho de la píldora de una buseta (cabe el ícono de «sin señal» y 4 dígitos).
const anchoMarcaBuseta = 76.0;

/// Busetas sobre el mapa: amarillas con el número lateral; sin señal en gris con
/// ícono. Entre dos mensajes la posición se interpola (~1 s) para que la buseta se
/// deslice; con «reducir movimiento» del sistema salta directo.
class MarcadoresBusetas extends StatefulWidget {
  const MarcadoresBusetas({super.key, required this.busetas});

  final List<BusetaEnVivo> busetas;

  @override
  State<MarcadoresBusetas> createState() => _MarcadoresBusetasState();
}

class _MarcadoresBusetasState extends State<MarcadoresBusetas>
    with SingleTickerProviderStateMixin {
  static const _duracion = Duration(milliseconds: 1000);

  late final AnimationController _controlador = AnimationController(vsync: this, duration: _duracion);
  Map<String, LatLng> _desde = {};
  Map<String, LatLng> _hasta = {};

  @override
  void initState() {
    super.initState();
    _hasta = _posiciones(widget.busetas);
    _desde = _hasta;
  }

  Map<String, LatLng> _posiciones(List<BusetaEnVivo> busetas) =>
      {for (final b in busetas) b.busetaId: LatLng(b.lat, b.lng)};

  Map<String, LatLng> _actuales() => {
        for (final e in _hasta.entries)
          e.key: interpolar(_desde[e.key] ?? e.value, e.value, _controlador.value),
      };

  @override
  void didUpdateWidget(MarcadoresBusetas anterior) {
    super.didUpdateWidget(anterior);
    final nuevas = _posiciones(widget.busetas);
    // Una reconstrucción sin posiciones nuevas no debe reiniciar la animación.
    if (mapEquals(nuevas, _hasta)) return;
    if (MediaQuery.disableAnimationsOf(context)) {
      _desde = nuevas;
      _hasta = nuevas;
      _controlador.value = 1;
      return;
    }
    // Arranca desde donde se veía cada buseta, no desde su último destino.
    _desde = _actuales();
    _hasta = nuevas;
    _controlador.forward(from: 0);
  }

  @override
  void dispose() {
    _controlador.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    return AnimatedBuilder(
      animation: _controlador,
      builder: (context, _) {
        final actuales = _actuales();
        return MarkerLayer(markers: [
          for (final b in widget.busetas)
            Marker(
              point: actuales[b.busetaId] ?? LatLng(b.lat, b.lng),
              width: anchoMarcaBuseta,
              height: 34,
              child: MarcaBuseta(buseta: b),
            ),
        ]);
      },
    );
  }
}

class MarcaBuseta extends StatelessWidget {
  const MarcaBuseta({super.key, required this.buseta});

  final BusetaEnVivo buseta;

  @override
  Widget build(BuildContext context) {
    final sinSenal = buseta.sinSenal;
    return Semantics(
      label: sinSenal
          ? 'Buseta ${buseta.numeroLateral} de ${buseta.empresa}, ubicación no disponible'
          : 'Buseta ${buseta.numeroLateral} de ${buseta.empresa}',
      child: ExcludeSemantics(
        child: Container(
          alignment: Alignment.center,
          decoration: BoxDecoration(
            color: sinSenal ? const Color(0xFFB9C2BD) : Colores.amarillo,
            borderRadius: BorderRadius.circular(17),
            border: Border.all(color: Colores.tinta, width: 2),
            boxShadow: const [BoxShadow(blurRadius: 3, color: Colors.black38)],
          ),
          child: FittedBox(
            fit: BoxFit.scaleDown,
            child: Padding(
              padding: const EdgeInsets.symmetric(horizontal: 6),
              child: Row(
                mainAxisSize: MainAxisSize.min,
                children: [
                  if (sinSenal) ...[
                    const Icon(Icons.signal_wifi_off, size: 14, color: Colores.tinta),
                    const SizedBox(width: 3),
                  ],
                  Text(
                    buseta.numeroLateral,
                    style: const TextStyle(
                      color: Colores.tinta,
                      fontWeight: FontWeight.w800,
                      fontSize: 13,
                    ),
                  ),
                ],
              ),
            ),
          ),
        ),
      ),
    );
  }
}
