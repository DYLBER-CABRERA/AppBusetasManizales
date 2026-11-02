import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../../../nucleo/cliente_api.dart';
import '../../../nucleo/errores.dart';

sealed class EstadoPrueba {
  const EstadoPrueba();
}

class PruebaInactiva extends EstadoPrueba {
  const PruebaInactiva();
}

class PruebaEnCurso extends EstadoPrueba {
  const PruebaEnCurso();
}

class PruebaExitosa extends EstadoPrueba {
  const PruebaExitosa(this.milisegundos);
  final int milisegundos;
}

class PruebaFallida extends EstadoPrueba {
  const PruebaFallida(this.mensaje);
  final String mensaje;
}

/// "Probar conexión": llama a `GET /salud` con la dirección vigente.
class ProbarConexionNotifier extends Notifier<EstadoPrueba> {
  @override
  EstadoPrueba build() => const PruebaInactiva();

  Future<void> probar() async {
    state = const PruebaEnCurso();
    final reloj = Stopwatch()..start();
    try {
      final ok = await ref.read(clienteApiProvider).salud();
      state = ok
          ? PruebaExitosa(reloj.elapsedMilliseconds)
          : const PruebaFallida('El servidor respondió, pero no indicó que esté listo.');
    } on ErrorApi catch (e) {
      state = PruebaFallida(e.mensaje);
    }
  }

  void reiniciar() => state = const PruebaInactiva();
}

final probarConexionProvider =
    NotifierProvider<ProbarConexionNotifier, EstadoPrueba>(ProbarConexionNotifier.new);
