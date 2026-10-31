import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../../../nucleo/cliente_api.dart';
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
}

final viajesRepositorioProvider =
    Provider<ViajesRepositorio>((ref) => ViajesRepositorio(ref.watch(clienteApiProvider)));
