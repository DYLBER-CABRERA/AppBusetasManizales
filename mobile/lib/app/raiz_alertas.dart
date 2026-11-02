import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../caracteristicas/guardados/presentacion/notificaciones_provider.dart';

/// Envuelve toda la app: mantiene viva la conexión de notificaciones (si hay sesión) y
/// pinta encima de cualquier pantalla el banner de la alerta entrante.
class RaizAlertas extends ConsumerWidget {
  const RaizAlertas({super.key, required this.child});

  final Widget child;

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final alerta = ref.watch(notificacionesProvider);
    return Stack(
      children: [
        child,
        if (alerta != null)
          Positioned(
            top: 0,
            left: 0,
            right: 0,
            child: SafeArea(
              child: Padding(
                padding: const EdgeInsets.all(8),
                // Este contexto queda sobre el Navigator: sin tooltips ni rutas.
                child: Material(
                  elevation: 6,
                  borderRadius: BorderRadius.circular(12),
                  color: alerta.esDesvio ? const Color(0xFFFFF1C2) : Theme.of(context).colorScheme.surface,
                  child: Semantics(
                    liveRegion: true,
                    container: true,
                    child: Padding(
                      padding: const EdgeInsets.fromLTRB(12, 8, 4, 8),
                      child: Row(
                        children: [
                          Icon(
                            alerta.esDesvio ? Icons.warning_amber_rounded : Icons.directions_bus,
                            color: const Color(0xFF13271E),
                          ),
                          const SizedBox(width: 12),
                          Expanded(
                            child: Column(
                              crossAxisAlignment: CrossAxisAlignment.start,
                              children: [
                                Text(
                                  alerta.titulo,
                                  style: const TextStyle(
                                    fontWeight: FontWeight.w700,
                                    color: Color(0xFF13271E),
                                  ),
                                ),
                                Text(
                                  alerta.mensaje,
                                  style: const TextStyle(color: Color(0xFF13271E)),
                                ),
                              ],
                            ),
                          ),
                          TextButton(
                            style: TextButton.styleFrom(foregroundColor: const Color(0xFF13271E)),
                            onPressed: () => ref.read(notificacionesProvider.notifier).descartar(),
                            child: const Text('Cerrar'),
                          ),
                        ],
                      ),
                    ),
                  ),
                ),
              ),
            ),
          ),
      ],
    );
  }
}
