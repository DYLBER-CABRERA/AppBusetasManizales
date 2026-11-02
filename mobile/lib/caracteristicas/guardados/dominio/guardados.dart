/// Favoritos y alertas de llegada del pasajero con sesión (BR-02).
library;

class Favorito {
  const Favorito({
    required this.id,
    required this.tipo,
    required this.disponible,
    this.nombre,
    this.rutaId,
    this.paraderoId,
  });

  factory Favorito.desdeJson(Map<String, dynamic> j) => Favorito(
        id: j['id'] as String,
        tipo: j['tipo'] as String,
        disponible: j['disponible'] as bool? ?? true,
        nombre: j['nombre'] as String?,
        rutaId: j['rutaId'] as String?,
        paraderoId: j['paraderoId'] as String?,
      );

  final String id;

  /// `ruta` | `paradero`.
  final String tipo;

  /// `false` si la ruta o el paradero se dieron de baja después de guardarlos.
  final bool disponible;
  final String? nombre;
  final String? rutaId;
  final String? paraderoId;

  bool get esRuta => tipo == 'ruta';
}

class AlertaLlegada {
  const AlertaLlegada({
    required this.id,
    required this.rutaId,
    required this.paraderoId,
    required this.distanciaAvisoM,
    required this.estado,
  });

  factory AlertaLlegada.desdeJson(Map<String, dynamic> j) => AlertaLlegada(
        id: j['id'] as String,
        rutaId: j['rutaId'] as String,
        paraderoId: j['paraderoId'] as String,
        distanciaAvisoM: j['distanciaAvisoM'] as int,
        estado: j['estado'] as String,
      );

  final String id;
  final String rutaId;
  final String paraderoId;
  final int distanciaAvisoM;

  /// `activa` | `notificada` | `desactivada`.
  final String estado;

  bool coincideCon(String ruta, String paradero) => rutaId == ruta && paraderoId == paradero;
}
