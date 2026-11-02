import 'package:latlong2/latlong.dart';

/// Punto intermedio entre [desde] y [hasta] para `t` de 0 a 1 (los tramos entre dos
/// posiciones son de pocos metros, así que la interpolación lineal basta).
LatLng interpolar(LatLng desde, LatLng hasta, double t) {
  final f = t.clamp(0.0, 1.0);
  return LatLng(
    desde.latitude + (hasta.latitude - desde.latitude) * f,
    desde.longitude + (hasta.longitude - desde.longitude) * f,
  );
}
