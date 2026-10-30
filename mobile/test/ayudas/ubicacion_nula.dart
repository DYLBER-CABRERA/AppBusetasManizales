import 'package:latlong2/latlong.dart';

import 'package:busetas_app/nucleo/ubicacion.dart';

/// Pasajero que negó el permiso de ubicación (sin tocar el plugin del sistema).
class UbicacionNula extends UbicacionNotifier {
  @override
  Future<LatLng?> build() async => null;
}
