import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../../../nucleo/cliente_api.dart';
import '../../ruta/dominio/ruta.dart';
import '../dominio/hito.dart';

class BusquedaRepositorio {
  const BusquedaRepositorio(this._api);

  final ClienteApi _api;

  /// El texto no puede ir vacío (el backend responde 400).
  Future<List<RutaResumen>> rutas(String texto) async {
    final datos = await _api.get('/busqueda/rutas', consulta: {'q': texto}) as List;
    return datos.cast<Map<String, dynamic>>().map(RutaResumen.desdeJson).toList();
  }

  Future<List<Hito>> hitos(String texto) async {
    final datos = await _api.get('/busqueda/hitos', consulta: {'q': texto}) as List;
    return datos.cast<Map<String, dynamic>>().map(Hito.desdeJson).toList();
  }

  Future<ResultadoRutas> rutasDeHito(String hitoId) async => ResultadoRutas.desdeJson(
        await _api.get('/hitos/$hitoId/rutas') as Map<String, dynamic>,
      );
}

final busquedaRepositorioProvider =
    Provider<BusquedaRepositorio>((ref) => BusquedaRepositorio(ref.watch(clienteApiProvider)));
