import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:latlong2/latlong.dart';

import '../../../nucleo/cliente_api.dart';
import '../../ruta/dominio/ruta.dart';
import '../dominio/viaje.dart';

class ViajesRepositorio {
  const ViajesRepositorio(this._api);

  final ClienteApi _api;

  Future<RespuestaPlanificacion> planificar(LugarViaje origen, LugarViaje destino) async =>
      RespuestaPlanificacion.desdeJson(
        await _api.post(
          '/viajes/planificar',
          cuerpo: {'origen': origen.aJson(), 'destino': destino.aJson()},
        ) as Map<String, dynamic>,
      );

  /// `GET /paraderos/cercanos` de una ruta, del más cercano al más lejano.
  Future<List<ParaderoCercano>> paraderosDeRutaCerca(LatLng punto, String rutaId, {int radioM = 5000}) async {
    final datos = await _api.get('/paraderos/cercanos', consulta: {
      'lat': punto.latitude,
      'lng': punto.longitude,
      'radioM': radioM,
      'rutaId': rutaId,
    }) as List;
    return datos.cast<Map<String, dynamic>>().map(ParaderoCercano.desdeJson).toList();
  }
}

final viajesRepositorioProvider =
    Provider<ViajesRepositorio>((ref) => ViajesRepositorio(ref.watch(clienteApiProvider)));
