/// Aviso vigente (`GET /avisos`): de empresa, de Movilidad o de la aplicación.
class Aviso {
  const Aviso({
    required this.id,
    required this.origen,
    required this.titulo,
    required this.cuerpo,
    required this.desde,
    this.hasta,
    this.empresaNombre,
    this.tipoCambio,
  });

  factory Aviso.desdeJson(Map<String, dynamic> j) => Aviso(
        id: j['id'] as String,
        origen: j['origen'] as String,
        titulo: j['titulo'] as String,
        cuerpo: j['cuerpo'] as String,
        desde: DateTime.parse(j['desde'] as String),
        hasta: j['hasta'] == null ? null : DateTime.parse(j['hasta'] as String),
        empresaNombre: j['empresaNombre'] as String?,
        tipoCambio: j['tipoCambio'] as String?,
      );

  final String id;

  /// `empresa` | `movilidad` | `aplicativo`.
  final String origen;
  final String titulo;
  final String cuerpo;
  final DateTime desde;
  final DateTime? hasta;
  final String? empresaNombre;

  /// `cierre` | `desvio` | `obra` | `condicion` (solo avisos de Movilidad).
  final String? tipoCambio;

  /// «Cierre», «Desvío», «Obra», «Condición» para la insignia de tipo de cambio.
  String? get etiquetaCambio => switch (tipoCambio) {
        'cierre' => 'Cierre',
        'desvio' => 'Desvío',
        'obra' => 'Obra',
        'condicion' => 'Condición',
        _ => null,
      };
}
