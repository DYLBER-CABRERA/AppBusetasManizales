/// Modelos de rutas según `contrato/openapi.json` (RutaResumen, RutaDetalle…).
library;

import 'package:latlong2/latlong.dart';

List<Map<String, dynamic>> _lista(Object? valor) =>
    ((valor as List?) ?? const []).cast<Map<String, dynamic>>();

class ServicioResumen {
  const ServicioResumen({
    required this.servicioId,
    required this.empresaId,
    required this.empresaNombre,
    this.codigoPublico,
  });

  factory ServicioResumen.desdeJson(Map<String, dynamic> j) => ServicioResumen(
        servicioId: j['servicioId'] as String,
        empresaId: j['empresaId'] as String,
        empresaNombre: j['empresaNombre'] as String,
        codigoPublico: j['codigoPublico'] as String?,
      );

  final String servicioId;
  final String empresaId;
  final String empresaNombre;
  final String? codigoPublico;

  /// «Socobuses · 18» o «Serviturismo · sin código».
  String get etiqueta => '$empresaNombre · ${codigoPublico ?? 'sin código'}';
}

class ParaderoCercano {
  const ParaderoCercano({
    required this.paraderoId,
    required this.nombre,
    required this.lat,
    required this.lng,
    required this.distanciaM,
  });

  factory ParaderoCercano.desdeJson(Map<String, dynamic> j) => ParaderoCercano(
        paraderoId: j['paraderoId'] as String,
        nombre: j['nombre'] as String,
        lat: (j['lat'] as num).toDouble(),
        lng: (j['lng'] as num).toDouble(),
        distanciaM: (j['distanciaM'] as num).toDouble(),
      );

  final String paraderoId;
  final String nombre;
  final double lat;
  final double lng;
  final double distanciaM;
}

class RutaResumen {
  const RutaResumen({
    required this.id,
    required this.nombre,
    required this.servicios,
    this.tipoRecorrido,
    this.esVariante = false,
    this.distanciaM,
  });

  factory RutaResumen.desdeJson(Map<String, dynamic> j) => RutaResumen(
        id: j['id'] as String,
        nombre: j['nombre'] as String,
        tipoRecorrido: j['tipoRecorrido'] as String?,
        esVariante: j['esVariante'] as bool? ?? false,
        distanciaM: (j['distanciaM'] as num?)?.toDouble(),
        servicios: _lista(j['servicios']).map(ServicioResumen.desdeJson).toList(),
      );

  final String id;
  final String nombre;
  final String? tipoRecorrido;
  final bool esVariante;
  final double? distanciaM;
  final List<ServicioResumen> servicios;

  /// Código que va en el sello: el primero que exista; si no, la inicial del nombre.
  String get codigoSello => codigoDeSello(nombre, servicios);

  String get empresas => servicios.map((s) => s.empresaNombre).join(' · ');
}

String codigoDeSello(String nombre, List<ServicioResumen> servicios) {
  for (final s in servicios) {
    if (s.codigoPublico != null && s.codigoPublico!.isNotEmpty) return s.codigoPublico!;
  }
  final limpio = nombre.trim();
  return limpio.isEmpty ? '?' : String.fromCharCode(limpio.runes.first).toUpperCase();
}

/// Respuesta de `/rutas/cercanas` y de `/hitos/{id}/rutas`.
class ResultadoRutas {
  const ResultadoRutas({required this.rutas, this.paraderoMasCercano, this.cobertura = true});

  /// `cobertura` solo viene en `/hitos/{id}/rutas`; en `/rutas/cercanas` se deduce de la lista.
  factory ResultadoRutas.desdeJson(Map<String, dynamic> j) {
    final rutas = _lista(j['rutas']).map(RutaResumen.desdeJson).toList();
    final paradero = j['paraderoMasCercano'];
    return ResultadoRutas(
      rutas: rutas,
      paraderoMasCercano:
          paradero is Map<String, dynamic> ? ParaderoCercano.desdeJson(paradero) : null,
      cobertura: j['cobertura'] as bool? ?? rutas.isNotEmpty,
    );
  }

  final List<RutaResumen> rutas;
  final ParaderoCercano? paraderoMasCercano;
  final bool cobertura;
}

class ParadaEnRuta {
  const ParadaEnRuta({
    required this.orden,
    required this.paraderoId,
    required this.nombre,
    required this.lat,
    required this.lng,
  });

  factory ParadaEnRuta.desdeJson(Map<String, dynamic> j) => ParadaEnRuta(
        orden: j['orden'] as int,
        paraderoId: j['paraderoId'] as String,
        nombre: j['nombre'] as String,
        lat: (j['lat'] as num).toDouble(),
        lng: (j['lng'] as num).toDouble(),
      );

  final int orden;
  final String paraderoId;
  final String nombre;
  final double lat;
  final double lng;

  LatLng get punto => LatLng(lat, lng);
}

class AvisoVigente {
  const AvisoVigente({
    required this.id,
    required this.origen,
    required this.titulo,
    required this.cuerpo,
    this.empresaNombre,
  });

  factory AvisoVigente.desdeJson(Map<String, dynamic> j) => AvisoVigente(
        id: j['id'] as String,
        origen: j['origen'] as String,
        titulo: j['titulo'] as String,
        cuerpo: j['cuerpo'] as String,
        empresaNombre: j['empresaNombre'] as String?,
      );

  final String id;

  /// `empresa` | `movilidad` | `aplicativo`.
  final String origen;
  final String titulo;
  final String cuerpo;
  final String? empresaNombre;
}

class RutaDetalle {
  const RutaDetalle({
    required this.id,
    required this.nombre,
    required this.servicios,
    required this.trazado,
    required this.paraderos,
    required this.avisos,
    this.descripcion,
    this.longitudM,
  });

  factory RutaDetalle.desdeJson(Map<String, dynamic> j) {
    final coordenadas = ((j['trazado'] as Map<String, dynamic>)['coordinates'] as List)
        .map((c) => LatLng((c[1] as num).toDouble(), (c[0] as num).toDouble())) // GeoJSON: [lng, lat]
        .toList();
    return RutaDetalle(
      id: j['id'] as String,
      nombre: j['nombre'] as String,
      descripcion: j['descripcion'] as String?,
      longitudM: (j['longitudM'] as num?)?.toDouble(),
      servicios: _lista(j['servicios']).map(ServicioResumen.desdeJson).toList(),
      trazado: coordenadas,
      paraderos: (_lista(j['paraderos']).map(ParadaEnRuta.desdeJson).toList()
        ..sort((a, b) => a.orden.compareTo(b.orden))),
      avisos: _lista(j['avisos']).map(AvisoVigente.desdeJson).toList(),
    );
  }

  final String id;
  final String nombre;
  final String? descripcion;
  final double? longitudM;
  final List<ServicioResumen> servicios;
  final List<LatLng> trazado;
  final List<ParadaEnRuta> paraderos;
  final List<AvisoVigente> avisos;

  String get codigoSello => codigoDeSello(nombre, servicios);
}
