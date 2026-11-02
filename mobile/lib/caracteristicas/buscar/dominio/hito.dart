class Hito {
  const Hito({
    required this.id,
    required this.nombre,
    required this.tipo,
    required this.lat,
    required this.lng,
    this.alias = const [],
  });

  factory Hito.desdeJson(Map<String, dynamic> j) => Hito(
        id: j['id'] as String,
        nombre: j['nombre'] as String,
        tipo: j['tipo'] as String,
        lat: (j['lat'] as num).toDouble(),
        lng: (j['lng'] as num).toDouble(),
        alias: ((j['alias'] as List?) ?? const []).cast<String>(),
      );

  final String id;
  final String nombre;

  /// `hito` | `barrio` | `sector` | `universidad` | `hospital` | `terminal` | `otro`.
  final String tipo;
  final double lat;
  final double lng;
  final List<String> alias;
}
