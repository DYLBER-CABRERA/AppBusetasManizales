import 'dart:async';

import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../../../nucleo/conexion_ws.dart';
import '../datos/eta_repositorio.dart';
import '../dominio/eta.dart';

typedef ParadaDeRuta = ({String rutaId, String paraderoId});

/// ETA de una parada. Se recalcula sola cada 2 intervalos de refresco (10 s) mientras
/// la pantalla está abierta; si un refresco falla se conserva el último resultado.
final etaProvider = FutureProvider.autoDispose.family<RespuestaEta, ParadaDeRuta>((ref, parada) {
  final cada = ref.read(tiemposTiempoRealProvider).intervaloRefresco * 2;
  final reloj = Timer.periodic(cada, (_) => ref.invalidateSelf());
  ref.onDispose(reloj.cancel);
  return ref
      .watch(etaRepositorioProvider)
      .eta(paraderoId: parada.paraderoId, rutaId: parada.rutaId);
});
