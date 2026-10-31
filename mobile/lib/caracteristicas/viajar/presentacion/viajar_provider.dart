import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../../../nucleo/errores.dart';
import '../datos/viajes_repositorio.dart';
import '../dominio/viaje.dart';

class EstadoViajar {
  const EstadoViajar({this.origen, this.destino, this.resultado, this.buscando = false, this.error});

  final LugarViaje? origen;
  final LugarViaje? destino;

  /// Última planificación; `null` si todavía no se ha buscado con estos lugares.
  final RespuestaPlanificacion? resultado;
  final bool buscando;
  final ErrorApi? error;

  bool get mismoLugar => origen != null && destino != null && origen!.mismoQue(destino!);
  bool get puedeBuscar => origen != null && destino != null && !mismoLugar && !buscando;

  EstadoViajar copiar({
    LugarViaje? origen,
    LugarViaje? destino,
    bool borrarResultado = false,
    RespuestaPlanificacion? resultado,
    bool? buscando,
    ErrorApi? error,
    bool borrarError = false,
  }) =>
      EstadoViajar(
        origen: origen ?? this.origen,
        destino: destino ?? this.destino,
        resultado: borrarResultado ? null : (resultado ?? this.resultado),
        buscando: buscando ?? this.buscando,
        error: borrarError ? null : (error ?? this.error),
      );
}

/// Origen, destino y resultado de «Viajar». Vive mientras la app, para no perder la
/// consulta al cambiar de pestaña.
class ViajarNotifier extends Notifier<EstadoViajar> {
  int _ticket = 0;

  @override
  EstadoViajar build() => const EstadoViajar();

  /// Cambiar un lugar invalida el resultado anterior.
  void elegirOrigen(LugarViaje lugar) => state = state.copiar(
      origen: lugar, borrarResultado: true, borrarError: true);

  void elegirDestino(LugarViaje lugar) => state = state.copiar(
      destino: lugar, borrarResultado: true, borrarError: true);

  void intercambiar() {
    final o = state.origen;
    final d = state.destino;
    _ticket++;
    state = EstadoViajar(origen: d, destino: o);
  }

  Future<void> buscar() async {
    final origen = state.origen;
    final destino = state.destino;
    if (origen == null || destino == null || !state.puedeBuscar) return;
    final ticket = ++_ticket;
    state = state.copiar(buscando: true, borrarResultado: true, borrarError: true);
    try {
      final resultado = await ref.read(viajesRepositorioProvider).planificar(origen, destino);
      if (ticket != _ticket) return;
      state = state.copiar(buscando: false, resultado: resultado);
    } on ErrorApi catch (e) {
      if (ticket != _ticket) return;
      state = state.copiar(buscando: false, error: e);
    }
  }
}

final viajarProvider = NotifierProvider<ViajarNotifier, EstadoViajar>(ViajarNotifier.new);
