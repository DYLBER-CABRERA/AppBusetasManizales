import 'dart:async';

import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../../../nucleo/errores.dart';
import '../../ruta/dominio/ruta.dart';
import '../datos/busqueda_repositorio.dart';
import '../dominio/hito.dart';

/// Atajos de la pantalla Buscar (hitos de los documentos de campo).
const hitosAtajo = ['Catedral', 'El Cable', 'Carrera 23', 'Fundadores', 'Terminal'];

const _esperaEscritura = Duration(milliseconds: 350);

sealed class EstadoBusqueda {
  const EstadoBusqueda();
}

class BusquedaInactiva extends EstadoBusqueda {
  const BusquedaInactiva();
}

class BusquedaCargando extends EstadoBusqueda {
  const BusquedaCargando();
}

class BusquedaConResultados extends EstadoBusqueda {
  const BusquedaConResultados({required this.texto, required this.rutas, required this.hitos});
  final String texto;
  final List<RutaResumen> rutas;
  final List<Hito> hitos;

  bool get vacia => rutas.isEmpty && hitos.isEmpty;
}

class BusquedaDeHito extends EstadoBusqueda {
  const BusquedaDeHito({required this.hito, required this.resultado});
  final Hito hito;
  final ResultadoRutas resultado;
}

class BusquedaFallida extends EstadoBusqueda {
  const BusquedaFallida(this.mensaje);
  final String mensaje;
}

/// Texto y hitos → rutas. La respuesta de una búsqueda vieja se descarta si ya
/// hay una más reciente.
class BusquedaNotifier extends Notifier<EstadoBusqueda> {
  Timer? _espera;
  int _ticket = 0;
  Future<void> Function()? _ultimaAccion;

  @override
  EstadoBusqueda build() {
    ref.onDispose(() => _espera?.cancel());
    return const BusquedaInactiva();
  }

  BusquedaRepositorio get _repo => ref.read(busquedaRepositorioProvider);

  /// Se llama en cada cambio del campo de texto.
  void escribir(String texto) {
    _espera?.cancel();
    final limpio = texto.trim();
    if (limpio.isEmpty) {
      _ticket++;
      _ultimaAccion = null;
      state = const BusquedaInactiva();
      return;
    }
    state = const BusquedaCargando();
    _espera = Timer(_esperaEscritura, () => buscarTexto(limpio));
  }

  Future<void> buscarTexto(String texto) {
    _ultimaAccion = () => buscarTexto(texto);
    return _ejecutar(() async {
      final resultados = await Future.wait<Object>([_repo.rutas(texto), _repo.hitos(texto)]);
      return BusquedaConResultados(
        texto: texto,
        rutas: resultados[0] as List<RutaResumen>,
        hitos: resultados[1] as List<Hito>,
      );
    });
  }

  Future<void> elegirHito(Hito hito) {
    _espera?.cancel();
    _ultimaAccion = () => elegirHito(hito);
    return _ejecutar(
      () async => BusquedaDeHito(hito: hito, resultado: await _repo.rutasDeHito(hito.id)),
    );
  }

  /// Chip de atajo: busca el hito por nombre y lista sus rutas.
  Future<void> elegirAtajo(String nombre) {
    _espera?.cancel();
    _ultimaAccion = () => elegirAtajo(nombre);
    return _ejecutar(() async {
      final hitos = await _repo.hitos(nombre);
      if (hitos.isEmpty) return BusquedaConResultados(texto: nombre, rutas: const [], hitos: const []);
      final exacto = hitos.where((h) => h.nombre.toLowerCase() == nombre.toLowerCase());
      final hito = exacto.isNotEmpty ? exacto.first : hitos.first;
      return BusquedaDeHito(hito: hito, resultado: await _repo.rutasDeHito(hito.id));
    });
  }

  Future<void> reintentar() => _ultimaAccion?.call() ?? Future.value();

  void limpiar() {
    _espera?.cancel();
    _ticket++;
    _ultimaAccion = null;
    state = const BusquedaInactiva();
  }

  Future<void> _ejecutar(Future<EstadoBusqueda> Function() accion) async {
    final ticket = ++_ticket;
    state = const BusquedaCargando();
    try {
      final resultado = await accion();
      if (ticket == _ticket) state = resultado;
    } on ErrorApi catch (e) {
      if (ticket == _ticket) state = BusquedaFallida(e.mensaje);
    }
  }
}

final busquedaProvider =
    NotifierProvider.autoDispose<BusquedaNotifier, EstadoBusqueda>(BusquedaNotifier.new);
