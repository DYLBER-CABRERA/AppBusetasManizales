/// Busetas de una ruta (`GET /rutas/{id}/busetas`). M1 solo usa `unidadesEnServicio`;
/// la lista completa la usa el bloque M2 (En vivo).
library;

class BusetaEnVivo {
  const BusetaEnVivo({
    required this.busetaId,
    required this.numeroLateral,
    required this.empresa,
    required this.servicioId,
    required this.estado,
    required this.lat,
    required this.lng,
    required this.reportadaEn,
    this.velocidadKmh,
    this.rumbo,
    this.mensaje,
  });

  factory BusetaEnVivo.desdeJson(Map<String, dynamic> j) => BusetaEnVivo(
        busetaId: j['busetaId'] as String,
        numeroLateral: j['numeroLateral'] as String,
        empresa: j['empresa'] as String,
        servicioId: j['servicioId'] as String,
        estado: j['estado'] as String,
        lat: (j['lat'] as num).toDouble(),
        lng: (j['lng'] as num).toDouble(),
        reportadaEn: DateTime.parse(j['reportadaEn'] as String),
        velocidadKmh: (j['velocidadKmh'] as num?)?.toDouble(),
        rumbo: (j['rumbo'] as num?)?.toDouble(),
        mensaje: j['mensaje'] as String?,
      );

  final String busetaId;
  final String numeroLateral;
  final String empresa;
  final String servicioId;

  /// `activa` | `sin_senal`.
  final String estado;
  final double lat;
  final double lng;
  final DateTime reportadaEn;
  final double? velocidadKmh;
  final double? rumbo;
  final String? mensaje;

  bool get sinSenal => estado == 'sin_senal';

  /// Para el mensaje `senal_perdida` del WebSocket (el contrato lo declara aunque el
  /// backend hoy no lo emite; lo normal es recibir `estado: sin_senal` por REST).
  BusetaEnVivo conSenalPerdida() => BusetaEnVivo(
        busetaId: busetaId,
        numeroLateral: numeroLateral,
        empresa: empresa,
        servicioId: servicioId,
        estado: 'sin_senal',
        lat: lat,
        lng: lng,
        reportadaEn: reportadaEn,
        velocidadKmh: velocidadKmh,
        rumbo: rumbo,
        mensaje: 'Ubicación no disponible. Última señal hace más de 60 s.',
      );
}

class BusetasEnVivo {
  const BusetasEnVivo({
    required this.seguimientoDisponible,
    required this.unidadesEnServicio,
    required this.calculadoEn,
    required this.busetas,
  });

  factory BusetasEnVivo.desdeJson(Map<String, dynamic> j) => BusetasEnVivo(
        seguimientoDisponible: j['seguimientoDisponible'] as bool,
        unidadesEnServicio: j['unidadesEnServicio'] as int,
        calculadoEn: DateTime.parse(j['calculadoEn'] as String),
        busetas: ((j['busetas'] as List?) ?? const [])
            .cast<Map<String, dynamic>>()
            .map(BusetaEnVivo.desdeJson)
            .toList(),
      );

  final bool seguimientoDisponible;
  final int unidadesEnServicio;
  final DateTime calculadoEn;
  final List<BusetaEnVivo> busetas;
}
