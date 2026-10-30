import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../../../nucleo/cliente_api.dart';
import '../dominio/eta.dart';

class EtaRepositorio {
  const EtaRepositorio(this._api);

  final ClienteApi _api;

  Future<RespuestaEta> eta({required String paraderoId, required String rutaId}) async {
    final datos = await _api.get('/paraderos/$paraderoId/eta', consulta: {'rutaId': rutaId});
    return RespuestaEta.desdeJson(datos as Map<String, dynamic>);
  }
}

final etaRepositorioProvider =
    Provider<EtaRepositorio>((ref) => EtaRepositorio(ref.watch(clienteApiProvider)));
