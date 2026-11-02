import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../../../nucleo/cliente_api.dart';
import '../dominio/guardados.dart';

/// `/favoritos` y `/alertas-llegada`: requieren sesión de pasajero (sin token → 401).
class GuardadosRepositorio {
  const GuardadosRepositorio(this._api);

  final ClienteApi _api;

  Future<List<Favorito>> favoritos() async {
    final datos = await _api.get('/favoritos') as List;
    return datos.cast<Map<String, dynamic>>().map(Favorito.desdeJson).toList();
  }

  /// Si la ruta ya estaba guardada el backend responde 200 con el existente.
  Future<Favorito> guardarRuta(String rutaId) async => Favorito.desdeJson(
        await _api.post('/favoritos', cuerpo: {'tipo': 'ruta', 'rutaId': rutaId})
            as Map<String, dynamic>,
      );

  Future<void> quitarFavorito(String id) async {
    await _api.delete('/favoritos/$id');
  }

  Future<List<AlertaLlegada>> alertas() async {
    final datos = await _api.get('/alertas-llegada') as List;
    return datos.cast<Map<String, dynamic>>().map(AlertaLlegada.desdeJson).toList();
  }

  /// La distancia de aviso es la del parámetro `distancia_aviso_llegada_m` (300 m).
  /// Repetida → 409 `CONFLICTO_NEGOCIO`.
  Future<AlertaLlegada> crearAlerta({required String rutaId, required String paraderoId}) async =>
      AlertaLlegada.desdeJson(
        await _api.post('/alertas-llegada', cuerpo: {'rutaId': rutaId, 'paraderoId': paraderoId})
            as Map<String, dynamic>,
      );

  Future<void> quitarAlerta(String id) async {
    await _api.delete('/alertas-llegada/$id');
  }
}

final guardadosRepositorioProvider =
    Provider<GuardadosRepositorio>((ref) => GuardadosRepositorio(ref.watch(clienteApiProvider)));
