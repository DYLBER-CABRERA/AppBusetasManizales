import 'package:latlong2/latlong.dart';

import 'package:busetas_app/nucleo/ubicacion.dart';

/// Pasajero que negó el permiso de ubicación (sin tocar el plugin del sistema).
class UbicacionNula extends UbicacionNotifier {
  @override
  Future<LatLng?> build() async => null;
}

/// Pasajero con el permiso concedido y una posición conocida.
class UbicacionFija extends UbicacionNotifier {
  UbicacionFija(this.punto);

  final LatLng punto;

  @override
  Future<LatLng?> build() async => punto;
}
