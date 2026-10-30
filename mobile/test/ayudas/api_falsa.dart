import 'dart:async';
import 'dart:convert';
import 'dart:typed_data';

import 'package:dio/dio.dart';

import 'package:busetas_app/nucleo/cliente_api.dart';

/// Respuesta de prueba: cuerpo JSON y código HTTP.
class RespuestaFalsa {
  const RespuestaFalsa(this.cuerpo, [this.estado = 200]);

  final Object? cuerpo;
  final int estado;
}

RespuestaFalsa errorFalso(int estado, String codigo, String mensaje) => RespuestaFalsa({
      'error': {'codigo': codigo, 'mensaje': mensaje, 'reintentable': estado == 503, 'detalles': null},
    }, estado);

/// Sustituye a la red: busca la ruta relativa (sin `/api/v1` ni consulta) en [respuestas].
class AdaptadorFalso implements HttpClientAdapter {
  AdaptadorFalso(this.respuestas);

  final Map<String, RespuestaFalsa> respuestas;
  final peticiones = <Uri>[];

  @override
  Future<ResponseBody> fetch(
    RequestOptions opciones,
    Stream<Uint8List>? cuerpo,
    Future<void>? cancelar,
  ) async {
    peticiones.add(opciones.uri);
    final respuesta = respuestas[opciones.path] ??
        errorFalso(404, 'NO_ENCONTRADO', 'No encontrado: ${opciones.path}');
    return ResponseBody.fromString(
      jsonEncode(respuesta.cuerpo),
      respuesta.estado,
      headers: {
        Headers.contentTypeHeader: ['application/json'],
      },
    );
  }

  @override
  void close({bool force = false}) {}
}

ClienteApi crearApiFalsa(AdaptadorFalso adaptador) {
  final dio = Dio(BaseOptions(baseUrl: 'http://servidor.prueba/api/v1'))
    ..httpClientAdapter = adaptador;
  return ClienteApi(servidor: 'http://servidor.prueba', dio: dio);
}
