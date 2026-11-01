import 'package:dio/dio.dart';

const mensajeSinConexion =
    'No se pudo conectar con el servidor. Mostramos lo último que cargó. Revisa tu conexión.';

/// Error de la API ya traducido: `{ "error": { codigo, mensaje, reintentable, detalles } }`.
class ErrorApi implements Exception {
  const ErrorApi({
    required this.codigo,
    required this.mensaje,
    this.reintentable = false,
    this.detalles,
    this.estado,
  });

  /// Sin respuesta del servidor (WiFi apagado, dirección incorrecta, tiempo agotado).
  const ErrorApi.sinConexion()
      : codigo = 'SIN_CONEXION',
        mensaje = mensajeSinConexion,
        reintentable = true,
        detalles = null,
        estado = null;

  final String codigo;
  final String mensaje;
  final bool reintentable;
  final Object? detalles;
  final int? estado;

  bool get esSinConexion => codigo == 'SIN_CONEXION' || codigo == 'SERVICIO_EXTERNO_NO_DISPONIBLE';
  bool get esNoAutenticado => codigo == 'NO_AUTENTICADO';
  bool get esNoEncontrado => codigo == 'NO_ENCONTRADO';

  factory ErrorApi.desdeDio(DioException e) {
    final respuesta = e.response;
    if (respuesta == null) return const ErrorApi.sinConexion();
    final cuerpo = respuesta.data;
    if (cuerpo is Map && cuerpo['error'] is Map) {
      final error = cuerpo['error'] as Map;
      return ErrorApi(
        codigo: (error['codigo'] ?? 'ERROR_INTERNO').toString(),
        mensaje: (error['mensaje'] ?? 'Ocurrió un error inesperado.').toString(),
        reintentable: error['reintentable'] == true,
        detalles: error['detalles'],
        estado: respuesta.statusCode,
      );
    }
    return ErrorApi(
      codigo: 'ERROR_INTERNO',
      mensaje: 'El servidor respondió con un error inesperado (${respuesta.statusCode}).',
      reintentable: true,
      estado: respuesta.statusCode,
    );
  }

  @override
  String toString() => 'ErrorApi($codigo: $mensaje)';
}
