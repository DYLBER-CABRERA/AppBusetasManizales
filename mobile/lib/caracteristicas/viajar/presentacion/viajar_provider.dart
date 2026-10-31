import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:latlong2/latlong.dart';

import '../../../nucleo/errores.dart';
import '../../ruta/datos/rutas_repositorio.dart';
import '../datos/viajes_repositorio.dart';
import '../dominio/viaje.dart';

class EstadoViajar {
  const EstadoViajar({
    this.origen,
    this.destino,
    this.resultado,
    this.buscando = false,
    this.error,
    this.cercanasAlOrigen = const [],
  });

  final LugarViaje? origen;
  final LugarViaje? destino;

  /// Última planificación; `null` si todavía no se ha buscado con estos lugares.
  final RespuestaPlanificacion? resultado;
  final bool buscando;
  final ErrorApi? error;

  /// Rutas que pasan cerca del origen cuando no hubo viaje directo (puede estar vacía).
  final List<RutaCercanaAlOrigen> cercanasAlOrigen;

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
    List<RutaCercanaAlOrigen>? cercanasAlOrigen,
  }) =>
      EstadoViajar(
        origen: origen ?? this.origen,
        destino: destino ?? this.destino,
        resultado: borrarResultado ? null : (resultado ?? this.resultado),
        buscando: buscando ?? this.buscando,
        error: borrarError ? null : (error ?? this.error),
        cercanasAlOrigen: borrarResultado ? const [] : (cercanasAlOrigen ?? this.cercanasAlOrigen),
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

  /// Sugerencia opcional: si falla, simplemente no se muestra (la respuesta principal ya está).
  Future<List<RutaCercanaAlOrigen>> _rutasCercanas(LatLng punto) async {
    try {
      final rutas = ref.read(rutasRepositorioProvider);
      final viajes = ref.read(viajesRepositorioProvider);
      final cercanas = (await rutas.cercanas(punto.latitude, punto.longitude)).rutas.take(3);
      return [
        for (final ruta in cercanas)
          RutaCercanaAlOrigen(
            ruta: ruta,
            paradero: (await viajes.paraderosDeRutaCerca(punto, ruta.id)).firstOrNull,
          ),
      ];
    } on ErrorApi {
      return const [];
    }
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
      if (resultado.opciones.isEmpty && origen.coordenadas != null) {
        final cercanas = await _rutasCercanas(origen.coordenadas!);
        if (ticket == _ticket) state = state.copiar(cercanasAlOrigen: cercanas);
      }
    } on ErrorApi catch (e) {
      if (ticket != _ticket) return;
      state = state.copiar(buscando: false, error: e);
    }
  }
}

final viajarProvider = NotifierProvider<ViajarNotifier, EstadoViajar>(ViajarNotifier.new);
