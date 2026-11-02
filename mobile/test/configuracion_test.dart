import 'package:dio/dio.dart';
import 'package:flutter_test/flutter_test.dart';

import 'package:busetas_app/nucleo/configuracion.dart';
import 'package:busetas_app/nucleo/errores.dart';

void main() {
  group('normalizarServidor', () {
    test('agrega http y quita barra final', () {
      expect(normalizarServidor('192.168.0.10:8000/'), 'http://192.168.0.10:8000');
    });

    test('quita el prefijo de la API', () {
      expect(normalizarServidor('http://10.0.2.2:8000/api/v1'), 'http://10.0.2.2:8000');
    });

    test('respeta https y sin puerto', () {
      expect(normalizarServidor(' https://demo.example.com '), 'https://demo.example.com');
    });

    test('rechaza vacío y esquemas no http', () {
      expect(normalizarServidor('   '), isNull);
      expect(normalizarServidor('ftp://servidor'), isNull);
    });
  });

  group('ErrorApi.desdeDio', () {
    DioException conRespuesta(int estado, Object? datos) {
      final peticion = RequestOptions(path: '/x');
      return DioException(
        requestOptions: peticion,
        response: Response(requestOptions: peticion, statusCode: estado, data: datos),
      );
    }

    test('lee el formato de error del contrato', () {
      final e = ErrorApi.desdeDio(conRespuesta(401, {
        'error': {
          'codigo': 'NO_AUTENTICADO',
          'mensaje': 'Inicia sesión para guardar.',
          'reintentable': false,
          'detalles': null,
        },
      }));
      expect(e.codigo, 'NO_AUTENTICADO');
      expect(e.esNoAutenticado, isTrue);
      expect(e.mensaje, 'Inicia sesión para guardar.');
      expect(e.estado, 401);
    });

    test('sin respuesta es error de conexión reintentable', () {
      final e = ErrorApi.desdeDio(DioException(requestOptions: RequestOptions(path: '/x')));
      expect(e.esSinConexion, isTrue);
      expect(e.reintentable, isTrue);
      expect(e.mensaje, mensajeSinConexion);
    });

    test('503 del servidor cuenta como sin conexión', () {
      final e = ErrorApi.desdeDio(conRespuesta(503, {
        'error': {
          'codigo': 'SERVICIO_EXTERNO_NO_DISPONIBLE',
          'mensaje': 'Base de datos no disponible.',
          'reintentable': true,
        },
      }));
      expect(e.esSinConexion, isTrue);
    });

    test('cuerpo no estándar da ERROR_INTERNO', () {
      final e = ErrorApi.desdeDio(conRespuesta(500, 'boom'));
      expect(e.codigo, 'ERROR_INTERNO');
    });
  });
}
