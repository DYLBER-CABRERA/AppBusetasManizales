/// Mensaje de `/ws/notificaciones`: `alerta_llegada` o `alerta_desvio` (D-P14).
class AlertaEntrante {
  const AlertaEntrante({
    required this.esDesvio,
    required this.mensaje,
    this.rutaId,
    this.paraderoId,
  });

  /// Devuelve `null` si el mensaje no es una alerta (el contrato puede sumar tipos).
  static AlertaEntrante? desdeMensaje(Map<String, dynamic> j) {
    final tipo = j['tipo'];
    if (tipo != 'alerta_llegada' && tipo != 'alerta_desvio') return null;
    final mensaje = j['mensaje'];
    if (mensaje is! String || mensaje.isEmpty) return null;
    return AlertaEntrante(
      esDesvio: tipo == 'alerta_desvio',
      mensaje: mensaje,
      rutaId: j['rutaId'] as String?,
      paraderoId: j['paraderoId'] as String?,
    );
  }

  final bool esDesvio;
  final String mensaje;
  final String? rutaId;
  final String? paraderoId;

  String get titulo => esDesvio ? 'La buseta se desvió' : 'Tu buseta está cerca';
}
