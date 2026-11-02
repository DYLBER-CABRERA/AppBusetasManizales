import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../../../nucleo/cliente_api.dart';
import '../dominio/horarios.dart';
import '../dominio/ruta.dart';
import '../dominio/seguimiento.dart';

/// Llamadas de consulta pública sobre rutas (BR-01: sin sesión).
class RutasRepositorio {
  const RutasRepositorio(this._api);

  final ClienteApi _api;

  Map<String, dynamic> _mapa(Object? datos) => datos as Map<String, dynamic>;

  Future<ResultadoRutas> cercanas(double lat, double lng, {int? radioM}) async {
    final datos = await _api.get('/rutas/cercanas', consulta: {
      'lat': lat,
      'lng': lng,
      'radioM': radioM,
    });
    return ResultadoRutas.desdeJson(_mapa(datos));
  }

  Future<List<RutaResumen>> todas() async {
    final datos = await _api.get('/rutas') as List;
    return datos.cast<Map<String, dynamic>>().map(RutaResumen.desdeJson).toList();
  }

  Future<RutaDetalle> detalle(String rutaId) async =>
      RutaDetalle.desdeJson(_mapa(await _api.get('/rutas/$rutaId')));

  Future<HorariosRuta> horarios(String rutaId) async =>
      HorariosRuta.desdeJson(_mapa(await _api.get('/rutas/$rutaId/horarios')));

  Future<FrecuenciasRuta> frecuencias(String rutaId) async =>
      FrecuenciasRuta.desdeJson(_mapa(await _api.get('/rutas/$rutaId/frecuencias')));

  Future<BusetasEnVivo> busetas(String rutaId) async =>
      BusetasEnVivo.desdeJson(_mapa(await _api.get('/rutas/$rutaId/busetas')));
}

final rutasRepositorioProvider =
    Provider<RutasRepositorio>((ref) => RutasRepositorio(ref.watch(clienteApiProvider)));
