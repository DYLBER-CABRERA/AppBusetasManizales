import 'dart:async';

import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../../../nucleo/auth.dart';
import '../../../nucleo/conexion_ws.dart';
import '../../../nucleo/configuracion.dart';
import '../../../nucleo/notificacion_local.dart';
import '../../../nucleo/sesion.dart';
import '../dominio/alerta_entrante.dart';

const _tiempoEnPantalla = Duration(seconds: 8);

/// Escucha `/ws/notificaciones?token=` mientras haya sesión. Cada `alerta_llegada` o
/// `alerta_desvio` se muestra como banner dentro de la app (el estado es la alerta
/// visible) y como notificación del sistema. Sin push remoto (D-P09): solo funciona
/// con la app abierta o en segundo plano reciente. El token no se registra.
class NotificacionesNotifier extends Notifier<AlertaEntrante?> {
  ConexionWs? _ws;
  Timer? _ocultar;
  int _siguienteId = 0;
  bool _cerrado = false;

  @override
  AlertaEntrante? build() {
    _cerrado = false;
    final sesion = ref.watch(sesionProvider);
    ref.onDispose(() {
      _cerrado = true;
      _ws?.cerrar();
      _ocultar?.cancel();
    });
    if (!sesion.activa) return null;

    final servidor = ref.watch(servidorProvider);
    final auth = ref.read(authProvider);
    final ws = ConexionWs(
      // El token se lee en cada intento: al reconectar se usa el renovado.
      construirUrl: () =>
          urlWebSocket(servidor, '/ws/notificaciones', consulta: {'token': auth.token ?? ''}),
      fabrica: ref.read(fabricaCanalProvider),
      alMensaje: _alMensaje,
      alCambiarEstado: (_) {},
      tiempos: ref.read(tiemposTiempoRealProvider),
    );
    _ws = ws;
    // `build` debe terminar antes de que la conexión escriba el estado.
    scheduleMicrotask(() {
      if (_cerrado) return;
      ws.iniciar();
      unawaited(ref.read(notificacionLocalProvider).pedirPermiso());
    });
    return null;
  }

  void _alMensaje(Map<String, dynamic> mensaje) {
    if (_cerrado) return;
    final alerta = AlertaEntrante.desdeMensaje(mensaje);
    if (alerta == null) return;
    state = alerta;
    unawaited(ref.read(notificacionLocalProvider).mostrar(
          id: ++_siguienteId,
          titulo: alerta.titulo,
          cuerpo: alerta.mensaje,
        ));
    _ocultar?.cancel();
    _ocultar = Timer(_tiempoEnPantalla, () {
      if (!_cerrado && identical(state, alerta)) state = null;
    });
  }

  void descartar() {
    _ocultar?.cancel();
    state = null;
  }
}

final notificacionesProvider =
    NotifierProvider<NotificacionesNotifier, AlertaEntrante?>(NotificacionesNotifier.new);
