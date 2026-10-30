import 'package:flutter_test/flutter_test.dart';
import 'package:latlong2/latlong.dart';

import 'package:busetas_app/caracteristicas/ruta/dominio/horarios.dart';
import 'package:busetas_app/caracteristicas/ruta/dominio/ruta.dart';
import 'package:busetas_app/caracteristicas/ruta/dominio/seguimiento.dart';
import 'package:busetas_app/nucleo/formato.dart';
import 'package:intl/date_symbol_data_local.dart';

import 'ayudas/datos_ejemplo.dart';

void main() {
  setUpAll(() => initializeDateFormatting('es'));

  group('RutaResumen / ResultadoRutas', () {
    test('lee servicios y arma el sello con el primer código', () {
      final ruta = RutaResumen.desdeJson(resumenEnea);
      expect(ruta.codigoSello, '18');
      expect(ruta.servicios.map((s) => s.etiqueta), ['Socobuses · 18', 'Serviturismo · sin código']);
      expect(ruta.empresas, 'Socobuses · Serviturismo');
    });

    test('sin ningún código el sello es la inicial del nombre', () {
      final ruta = RutaResumen.desdeJson(
        rutaResumen('x', 'villamaría', [servicio('Serviturismo', null)]),
      );
      expect(ruta.codigoSello, 'V');
    });

    test('cercanas sin rutas trae el paradero más cercano y cobertura=false', () {
      final resultado = ResultadoRutas.desdeJson({
        'rutas': <Object>[],
        'paraderoMasCercano': {
          'paraderoId': 'p9',
          'nombre': 'Fundadores',
          'lat': 5.07,
          'lng': -75.5,
          'distanciaM': 1234.0,
        },
      });
      expect(resultado.rutas, isEmpty);
      expect(resultado.cobertura, isFalse);
      expect(resultado.paraderoMasCercano?.nombre, 'Fundadores');
    });

    test('hitos/{id}/rutas respeta el campo cobertura', () {
      final resultado = ResultadoRutas.desdeJson({
        'cobertura': true,
        'rutas': [resumenCable],
      });
      expect(resultado.cobertura, isTrue);
      expect(resultado.rutas.single.distanciaM, 220);
    });
  });

  group('RutaDetalle', () {
    final detalle = RutaDetalle.desdeJson(detalleCable());

    test('el GeoJSON [lng, lat] se invierte a LatLng(lat, lng)', () {
      expect(detalle.trazado.first, const LatLng(5.0495, -75.506));
    });

    test('ordena los paraderos por orden', () {
      expect(detalle.paraderos.map((p) => p.nombre), ['Terminal', 'Carrera 23']);
    });

    test('lee los avisos vigentes', () {
      expect(detalle.avisos.single.origen, 'movilidad');
    });
  });

  group('Horarios y frecuencias', () {
    test('una fila por tipo de día y null donde falta el dato', () {
      final horarios = HorariosRuta.desdeJson(horariosCable());
      final filas = horarios.servicios.single.filas;
      expect(horarios.tipoDiaHoy, TipoDia.lunVie);
      expect(filas.map((f) => f.$1), TipoDia.values);
      expect(filas[0].$2?.primeraSalida, '04:45');
      expect(filas[1].$2, isNull, reason: 'el sábado de Sideral está pendiente');
      expect(filas[2].$2?.ultimaSalida, '21:00');
    });

    test('hhmm recorta segundos y respeta 24:00', () {
      expect(hhmm('04:45:00'), '04:45');
      expect(hhmm('24:00'), '24:00');
    });

    test('texto de la frecuencia: rango o valor único', () {
      final frecuencias = FrecuenciasRuta.desdeJson(frecuenciasCable());
      final f = frecuencias.servicios.single.frecuencias.single;
      expect(f.texto, 'De 8 a 10 min');
      expect(
        Frecuencia.desdeJson({
          'tipoDia': 'lun_vie',
          'franjaInicio': '05:30',
          'franjaFin': '22:00',
          'minutosMin': 6,
          'minutosMax': 6,
        }).texto,
        'Cada 6 min',
      );
      expect(frecuencias.servicios.single.deTipoDia(TipoDia.sabado), isEmpty);
    });
  });

  test('BusetasEnVivo lee las unidades en servicio', () {
    final busetas = BusetasEnVivo.desdeJson(busetasVacio());
    expect(busetas.unidadesEnServicio, 0);
    expect(busetas.seguimientoDisponible, isFalse);
  });

  group('formatearDistancia', () {
    test('metros por debajo de 1 km', () => expect(formatearDistancia(219.6), '220 m'));
    test('kilómetros con coma decimal', () => expect(formatearDistancia(1234), '1,2 km'));
  });
}
