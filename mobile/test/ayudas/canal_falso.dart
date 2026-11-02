import 'dart:async';
import 'dart:convert';

import 'package:stream_channel/stream_channel.dart';
import 'package:web_socket_channel/web_socket_channel.dart';

/// Canal WebSocket de prueba: el «servidor» envía con [servidorEnvia] y se puede
/// cortar con [servidorCierra]. Con `falla: true` la conexión nunca se establece.
class CanalFalso extends StreamChannelMixin<dynamic> implements WebSocketChannel {
  CanalFalso({this.falla = false});

  final bool falla;
  final _entrada = StreamController<dynamic>();
  final enviados = <dynamic>[];
  bool cerrado = false;

  void servidorEnvia(Object json) => _entrada.add(jsonEncode(json));
  void servidorEnviaTexto(String texto) => _entrada.add(texto);
  void servidorCierra() => _entrada.close();

  @override
  Future<void> get ready => falla ? Future<void>.error(Exception('sin conexión')) : Future<void>.value();

  @override
  Stream<dynamic> get stream => _entrada.stream;

  @override
  WebSocketSink get sink => _SumideroFalso(this);

  @override
  String? get protocol => null;

  @override
  int? get closeCode => null;

  @override
  String? get closeReason => null;
}

class _SumideroFalso implements WebSocketSink {
  _SumideroFalso(this._canal);

  final CanalFalso _canal;

  @override
  void add(dynamic dato) => _canal.enviados.add(dato);

  @override
  void addError(Object error, [StackTrace? traza]) {}

  @override
  Future<dynamic> addStream(Stream<dynamic> flujo) => flujo.drain<void>();

  @override
  Future<dynamic> close([int? codigo, String? motivo]) {
    _canal.cerrado = true;
    return Future<void>.value();
  }

  @override
  Future<dynamic> get done => Future<void>.value();
}

/// Fábrica que entrega los canales en orden; cuando se acaban, canales que fallan.
class FabricaCanalesFalsa {
  FabricaCanalesFalsa([List<CanalFalso> canales = const []]) : _pendientes = [...canales];

  final List<CanalFalso> _pendientes;
  final urls = <Uri>[];
  final creados = <CanalFalso>[];

  WebSocketChannel crear(Uri url) {
    urls.add(url);
    final canal = _pendientes.isEmpty ? CanalFalso(falla: true) : _pendientes.removeAt(0);
    creados.add(canal);
    return canal;
  }
}
