import 'package:flutter/material.dart';

import '../../nucleo/errores.dart';

/// Banner rojo con **Reintentar**. Se muestra sobre el contenido ya cargado.
class BannerError extends StatelessWidget {
  const BannerError({super.key, required this.mensaje, this.onReintentar});

  factory BannerError.desdeError(Object error, {VoidCallback? onReintentar}) => BannerError(
        mensaje: error is ErrorApi ? error.mensaje : 'Ocurrió un error inesperado.',
        onReintentar: onReintentar,
      );

  final String mensaje;
  final VoidCallback? onReintentar;

  @override
  Widget build(BuildContext context) {
    final esquema = Theme.of(context).colorScheme;
    return Semantics(
      liveRegion: true,
      container: true,
      child: Container(
        width: double.infinity,
        padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 8),
        decoration: BoxDecoration(
          color: esquema.error.withValues(alpha: 0.12),
          border: Border(left: BorderSide(color: esquema.error, width: 4)),
        ),
        child: Row(
          children: [
            Icon(Icons.error_outline, color: esquema.error),
            const SizedBox(width: 12),
            Expanded(child: Text(mensaje, style: TextStyle(color: esquema.onSurface))),
            if (onReintentar != null)
              TextButton(onPressed: onReintentar, child: const Text('Reintentar')),
          ],
        ),
      ),
    );
  }
}
