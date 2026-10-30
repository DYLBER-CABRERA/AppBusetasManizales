/// ETA de una parada (`GET /paraderos/{id}/eta?rutaId=…`), un resultado por servicio.
library;

enum FuenteEta {
  gps('gps', 'GPS'),
  horario('horario', 'horario'),
  noDisponible('no_disponible', 'sin datos');

  const FuenteEta(this.valor, this.etiqueta);

  final String valor;
  final String etiqueta;

  static FuenteEta desdeValor(String valor) =>
      FuenteEta.values.firstWhere((f) => f.valor == valor, orElse: () => FuenteEta.noDisponible);
}

/// «4 min» o «Menos de 1 min».
String textoMinutos(int segundos) =>
    segundos < 60 ? 'Menos de 1 min' : '${(segundos / 60).round()} min';

class ResultadoEta {
  const ResultadoEta({
    required this.servicioId,
    required this.empresa,
    required this.fuente,
    this.codigoPublico,
    this.etaSegundos,
    this.maxSegundos,
    this.busetaNumeroLateral,
    this.ultimaSenalHaceS,
    this.mensaje,
  });

  factory ResultadoEta.desdeJson(Map<String, dynamic> j) {
    final rango = j['rango'] as Map<String, dynamic>?;
    return ResultadoEta(
      servicioId: j['servicioId'] as String,
      empresa: j['empresa'] as String,
      codigoPublico: j['codigoPublico'] as String?,
      fuente: FuenteEta.desdeValor(j['fuente'] as String),
      etaSegundos: j['etaSegundos'] as int?,
      maxSegundos: rango?['maxSegundos'] as int?,
      busetaNumeroLateral: j['busetaNumeroLateral'] as String?,
      ultimaSenalHaceS: j['ultimaSenalHaceS'] as int?,
      mensaje: j['mensaje'] as String?,
    );
  }

  final String servicioId;
  final String empresa;
  final String? codigoPublico;
  final FuenteEta fuente;
  final int? etaSegundos;

  /// Tope del rango por horario (`rango.maxSegundos`).
  final int? maxSegundos;
  final String? busetaNumeroLateral;
  final int? ultimaSenalHaceS;
  final String? mensaje;

  String get titulo => '$empresa · ${codigoPublico ?? 'sin código'}';

  /// Cifra grande de la tarjeta: «4 min» (GPS) o «Hasta 15 min» (horario).
  String? get principal => switch (fuente) {
        FuenteEta.gps when etaSegundos != null => textoMinutos(etaSegundos!),
        FuenteEta.horario when maxSegundos != null => 'Hasta ${(maxSegundos! / 60).ceil()} min',
        _ => null,
      };

  /// «Fuente: GPS · hace 3 s» · «Fuente: horario».
  String get lineaFuente {
    final base = 'Fuente: ${fuente.etiqueta}';
    return fuente == FuenteEta.gps && ultimaSenalHaceS != null
        ? '$base · hace $ultimaSenalHaceS s'
        : base;
  }
}

class RespuestaEta {
  const RespuestaEta({
    required this.paraderoId,
    required this.rutaId,
    required this.calculadoEn,
    required this.resultados,
  });

  factory RespuestaEta.desdeJson(Map<String, dynamic> j) => RespuestaEta(
        paraderoId: j['paraderoId'] as String,
        rutaId: j['rutaId'] as String,
        calculadoEn: DateTime.parse(j['calculadoEn'] as String),
        resultados: ((j['resultados'] as List?) ?? const [])
            .cast<Map<String, dynamic>>()
            .map(ResultadoEta.desdeJson)
            .toList(),
      );

  final String paraderoId;
  final String rutaId;
  final DateTime calculadoEn;
  final List<ResultadoEta> resultados;
}
