import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../../../nucleo/cliente_api.dart';
import '../dominio/aviso.dart';

class AvisosRepositorio {
  const AvisosRepositorio(this._api);

  final ClienteApi _api;

  Future<List<Aviso>> vigentes() async {
    final datos = await _api.get('/avisos') as List;
    return datos.cast<Map<String, dynamic>>().map(Aviso.desdeJson).toList();
  }
}

final avisosRepositorioProvider =
    Provider<AvisosRepositorio>((ref) => AvisosRepositorio(ref.watch(clienteApiProvider)));
