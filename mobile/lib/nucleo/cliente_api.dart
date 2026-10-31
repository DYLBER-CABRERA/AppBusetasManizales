import 'package:dio/dio.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import 'auth.dart';
import 'configuracion.dart';
import 'errores.dart';

/// Cliente REST del backend. Todas las llamadas devuelven JSON decodificado o
/// lanzan [ErrorApi]. No registra tokens, cabeceras ni coordenadas.
class ClienteApi {
  ClienteApi({required String servidor, this.tokenActual, Dio? dio})
      : _dio = dio ??
            Dio(BaseOptions(
              baseUrl: '$servidor${Configuracion.prefijoApi}',
              connectTimeout: const Duration(seconds: 8),
              receiveTimeout: const Duration(seconds: 15),
              headers: {'Accept': 'application/json'},
            ));

  final Dio _dio;

  /// Token JWT de Supabase Auth, si hay sesión.
  final String? Function()? tokenActual;

  Future<Object?> get(String ruta, {Map<String, Object?>? consulta}) =>
      _enviar('GET', ruta, consulta: consulta);

  Future<Object?> post(String ruta, {Object? cuerpo, Map<String, Object?>? consulta}) =>
      _enviar('POST', ruta, cuerpo: cuerpo, consulta: consulta);

  Future<Object?> delete(String ruta, {Map<String, Object?>? consulta}) =>
      _enviar('DELETE', ruta, consulta: consulta);

  Future<Object?> _enviar(
    String metodo,
    String ruta, {
    Object? cuerpo,
    Map<String, Object?>? consulta,
  }) async {
    final token = tokenActual?.call();
    try {
      final respuesta = await _dio.request<Object?>(
        ruta,
        data: cuerpo,
        queryParameters: consulta == null
            ? null
            : {for (final e in consulta.entries) if (e.value != null) e.key: e.value},
        options: Options(
          method: metodo,
          headers: token == null ? null : {'Authorization': 'Bearer $token'},
        ),
      );
      return respuesta.data;
    } on DioException catch (e) {
      throw ErrorApi.desdeDio(e);
    }
  }

  /// `GET /salud`: `true` si el servidor responde `{estado: ok}`.
  Future<bool> salud() async {
    final datos = await get('/salud');
    return datos is Map && datos['estado'] == 'ok';
  }
}

final clienteApiProvider = Provider<ClienteApi>((ref) {
  final servidor = ref.watch(servidorProvider);
  // El token se lee en cada llamada: Supabase lo renueva solo y no hay que rehacer el cliente.
  return ClienteApi(servidor: servidor, tokenActual: () => ref.read(authProvider).token);
});
