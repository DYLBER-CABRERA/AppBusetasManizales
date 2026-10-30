import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../../../nucleo/ubicacion.dart';
import '../../ruta/datos/rutas_repositorio.dart';
import '../../ruta/dominio/ruta.dart';

/// Radio por defecto del parámetro `radio_busqueda_m`. El backend no lo expone a
/// los pasajeros; solo se usa para redactar el texto cuando no hay rutas cerca.
const radioBusquedaPorDefectoM = 800;

/// Rutas cerca del pasajero (o del centro de Manizales si no hay ubicación).
final rutasCercanasProvider = FutureProvider<ResultadoRutas>((ref) async {
  final ubicacion = await ref.watch(ubicacionProvider.future);
  final centro = ubicacion ?? centroManizales;
  return ref.watch(rutasRepositorioProvider).cercanas(centro.latitude, centro.longitude);
});
