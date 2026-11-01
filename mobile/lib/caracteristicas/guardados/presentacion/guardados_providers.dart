import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../../../nucleo/sesion.dart';
import '../datos/guardados_repositorio.dart';
import '../dominio/guardados.dart';

/// Favoritos del pasajero. Sin sesión no se consulta (devolvería 401) y la lista queda
/// vacía; al iniciar o cerrar sesión se vuelve a calcular.
final favoritosProvider = FutureProvider.autoDispose<List<Favorito>>((ref) async {
  if (!ref.watch(sesionProvider).activa) return const [];
  return ref.watch(guardadosRepositorioProvider).favoritos();
});

/// Alertas de llegada no desactivadas del pasajero.
final alertasProvider = FutureProvider.autoDispose<List<AlertaLlegada>>((ref) async {
  if (!ref.watch(sesionProvider).activa) return const [];
  return ref.watch(guardadosRepositorioProvider).alertas();
});

/// Acciones sobre favoritos y alertas; cada una refresca su lista al terminar.
class AccionesGuardados {
  const AccionesGuardados(this._ref);

  final Ref _ref;

  GuardadosRepositorio get _repo => _ref.read(guardadosRepositorioProvider);

  Future<void> guardarRuta(String rutaId) async {
    await _repo.guardarRuta(rutaId);
    _ref.invalidate(favoritosProvider);
  }

  Future<void> quitarFavorito(String id) async {
    await _repo.quitarFavorito(id);
    _ref.invalidate(favoritosProvider);
  }

  Future<void> crearAlerta({required String rutaId, required String paraderoId}) async {
    await _repo.crearAlerta(rutaId: rutaId, paraderoId: paraderoId);
    _ref.invalidate(alertasProvider);
  }

  Future<void> quitarAlerta(String id) async {
    await _repo.quitarAlerta(id);
    _ref.invalidate(alertasProvider);
  }
}

final accionesGuardadosProvider = Provider<AccionesGuardados>(AccionesGuardados.new);
