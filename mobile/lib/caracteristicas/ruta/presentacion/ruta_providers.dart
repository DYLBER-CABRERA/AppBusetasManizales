import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../datos/rutas_repositorio.dart';
import '../dominio/horarios.dart';
import '../dominio/ruta.dart';

/// Todas las rutas activas (resumen con servicios).
final todasLasRutasProvider = FutureProvider<List<RutaResumen>>(
  (ref) => ref.watch(rutasRepositorioProvider).todas(),
);

/// Detalle con trazado y paraderos. Se conserva en caché mientras la app vive
/// porque el mapa y la ficha lo comparten.
final rutaDetalleProvider = FutureProvider.family<RutaDetalle, String>(
  (ref, rutaId) => ref.watch(rutasRepositorioProvider).detalle(rutaId),
);

final horariosRutaProvider = FutureProvider.autoDispose.family<HorariosRuta, String>(
  (ref, rutaId) => ref.watch(rutasRepositorioProvider).horarios(rutaId),
);

final frecuenciasRutaProvider = FutureProvider.autoDispose.family<FrecuenciasRuta, String>(
  (ref, rutaId) => ref.watch(rutasRepositorioProvider).frecuencias(rutaId),
);

/// Busetas con turno vigente en la ruta (para «N en servicio»).
final unidadesEnServicioProvider = FutureProvider.autoDispose.family<int, String>(
  (ref, rutaId) async =>
      (await ref.watch(rutasRepositorioProvider).busetas(rutaId)).unidadesEnServicio,
);

/// Colores de ruta con buen contraste con texto blanco. El amarillo se reserva
/// para las busetas y el rojo ladrillo para los errores.
const paletaRutas = [
  Color(0xFF0E7C66),
  Color(0xFF1F5FA8),
  Color(0xFF8E3B9E),
  Color(0xFF0F6F8C),
  Color(0xFFA23B5B),
  Color(0xFF5B6B12),
];

/// El backend no define color de ruta: se reparte la paleta por orden alfabético
/// de nombre para que dos rutas distintas no repitan color.
final coloresRutasProvider = Provider<Map<String, Color>>((ref) {
  final rutas = ref.watch(todasLasRutasProvider).value ?? const <RutaResumen>[];
  final ordenadas = [...rutas]..sort((a, b) => a.nombre.compareTo(b.nombre));
  return {
    for (var i = 0; i < ordenadas.length; i++) ordenadas[i].id: paletaRutas[i % paletaRutas.length],
  };
});

Color colorDeRuta(WidgetRef ref, String rutaId) =>
    ref.watch(coloresRutasProvider)[rutaId] ?? paletaRutas[rutaId.hashCode.abs() % paletaRutas.length];
