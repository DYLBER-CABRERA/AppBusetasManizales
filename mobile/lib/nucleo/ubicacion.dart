import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:geolocator/geolocator.dart';
import 'package:latlong2/latlong.dart';

/// Centro de Manizales: se usa cuando no hay permiso o no hay ubicación.
const centroManizales = LatLng(5.0689, -75.5174);

/// Ubicación del pasajero solo para "cerca de ti". Vive en memoria: no se guarda
/// ni se registra, y solo sale como parámetro de la consulta puntual.
/// El valor es `null` si se negó el permiso o no se pudo obtener.
class UbicacionNotifier extends AsyncNotifier<LatLng?> {
  @override
  Future<LatLng?> build() => _obtener();

  Future<void> actualizar() async {
    state = const AsyncLoading<LatLng?>();
    state = await AsyncValue.guard(_obtener);
  }

  Future<LatLng?> _obtener() async {
    try {
      if (!await Geolocator.isLocationServiceEnabled()) return null;
      var permiso = await Geolocator.checkPermission();
      if (permiso == LocationPermission.denied) {
        permiso = await Geolocator.requestPermission();
      }
      if (permiso == LocationPermission.denied || permiso == LocationPermission.deniedForever) {
        return null;
      }
      final posicion = await Geolocator.getCurrentPosition(
        locationSettings: const LocationSettings(
          accuracy: LocationAccuracy.medium,
          timeLimit: Duration(seconds: 10),
        ),
      );
      return LatLng(posicion.latitude, posicion.longitude);
    } catch (_) {
      return null;
    }
  }
}

final ubicacionProvider =
    AsyncNotifierProvider<UbicacionNotifier, LatLng?>(UbicacionNotifier.new);
