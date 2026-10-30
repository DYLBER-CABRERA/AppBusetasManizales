import 'dart:async';
import 'dart:convert';

import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:web_socket_channel/web_socket_channel.dart';

/// Abre el canal; se sustituye en las pruebas.
typedef FabricaCanal = WebSocketChannel Function(Uri url);

final fabricaCanalProvider = Provider<FabricaCanal>((ref) => WebSocketChannel.connect);

/// Tiempos del tiempo real. El parámetro `intervalo_refresco_cliente_s` (5) no es
/// legible por un pasajero, así que se usa su valor por defecto.
class TiemposTiempoReal {
  const TiemposTiempoReal({
    this.intervaloRefresco = const Duration(seconds: 5),
    this.esperasReconexion = const [
      Duration(seconds: 1),
      Duration(seconds: 2),
      Duration(seconds: 4),
      Duration(seconds: 8),
      Duration(seconds: 15),
    ],
    this.latido = const Duration(seconds: 25),
  });

  /// Cada cuánto se consulta REST mientras no hay WebSocket; 3 intervalos sin datos = desactualizado.
  final Duration intervaloRefresco;

  /// Espera creciente 1, 2, 4, 8 s con tope de 15 s (se repite el último valor).
  final List<Duration> esperasReconexion;
  final Duration latido;
}

final tiemposTiempoRealProvider = Provider<TiemposTiempoReal>((ref) => const TiemposTiempoReal());

/// `http://host:8000` → `ws://host:8000/ruta` (y `https` → `wss`).
Uri urlWebSocket(String servidor, String ruta, {Map<String, String>? consulta}) {
  final base = Uri.parse(servidor);
  return Uri(
    scheme: base.scheme == 'https' ? 'wss' : 'ws',
    host: base.host,
    port: base.hasPort ? base.port : null,
    path: ruta,
    queryParameters: consulta,
  );
}

enum EstadoWs { conectando, conectado, desconectado }

/// WebSocket con reconexión de espera creciente. Entrega los mensajes JSON como
/// `Map`; `"pong"` se ignora. No registra la URL (puede llevar un token).
class ConexionWs {
  ConexionWs({
    required this.url,
    required this.fabrica,
    required this.alMensaje,
    required this.alCambiarEstado,
    this.tiempos = const TiemposTiempoReal(),
  });

  final Uri url;
  final FabricaCanal fabrica;
  final void Function(Map<String, dynamic> mensaje) alMensaje;
  final void Function(EstadoWs estado) alCambiarEstado;
  final TiemposTiempoReal tiempos;

  WebSocketChannel? _canal;
  StreamSubscription<dynamic>? _suscripcion;
  Timer? _espera;
  Timer? _latido;
  int _fallos = 0;
  bool _cerrada = true;

  bool get abierta => !_cerrada;

  void iniciar() {
    if (!_cerrada) return;
    _cerrada = false;
    _conectar();
  }

  /// Corta la conexión actual y vuelve a intentar enseguida (p. ej. al volver a primer plano).
  void reconectar() {
    if (_cerrada) return;
    _soltar();
    _fallos = 0;
    _conectar();
  }

  void cerrar() {
    _cerrada = true;
    _soltar();
  }

  void _soltar() {
    _espera?.cancel();
    _latido?.cancel();
    _suscripcion?.cancel();
    _suscripcion = null;
    final canal = _canal;
    _canal = null;
    if (canal != null) {
      // Un fallo al cerrar no importa: ya no escuchamos este canal.
      unawaited(canal.sink.close().catchError((Object _) {}));
    }
  }

  Future<void> _conectar() async {
    if (_cerrada) return;
    alCambiarEstado(EstadoWs.conectando);
    final WebSocketChannel canal;
    try {
      canal = fabrica(url);
      _canal = canal;
      await canal.ready;
    } catch (_) {
      if (!_cerrada) _perdida();
      return;
    }
    if (_cerrada || !identical(_canal, canal)) return;

    _fallos = 0;
    alCambiarEstado(EstadoWs.conectado);
    _latido = Timer.periodic(tiempos.latido, (_) {
      try {
        canal.sink.add('ping');
      } catch (_) {
        // Si falla el envío, el stream avisará del cierre.
      }
    });
    _suscripcion = canal.stream.listen(
      (dato) {
        if (dato is! String || dato == 'pong') return;
        try {
          final json = jsonDecode(dato);
          if (json is Map<String, dynamic>) alMensaje(json);
        } on FormatException {
          // Mensaje que no es JSON: se ignora.
        }
      },
      onError: (Object _) => _perdida(),
      onDone: _perdida,
      cancelOnError: true,
    );
  }

  void _perdida() {
    if (_cerrada) return;
    _soltar();
    alCambiarEstado(EstadoWs.desconectado);
    final esperas = tiempos.esperasReconexion;
    final espera = esperas[_fallos < esperas.length ? _fallos : esperas.length - 1];
    _fallos++;
    _espera = Timer(espera, _conectar);
  }
}
