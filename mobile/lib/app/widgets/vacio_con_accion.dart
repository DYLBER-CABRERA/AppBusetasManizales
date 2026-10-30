import 'package:flutter/material.dart';

/// Estado vacío: título + causa + siguiente paso (COM-11).
class VacioConAccion extends StatelessWidget {
  const VacioConAccion({
    super.key,
    required this.titulo,
    this.causa,
    this.etiquetaAccion,
    this.onAccion,
    this.icono = Icons.info_outline,
  });

  final String titulo;
  final String? causa;
  final String? etiquetaAccion;
  final VoidCallback? onAccion;
  final IconData icono;

  @override
  Widget build(BuildContext context) {
    final texto = Theme.of(context).textTheme;
    return Padding(
      padding: const EdgeInsets.all(24),
      child: Column(
        mainAxisSize: MainAxisSize.min,
        children: [
          Icon(icono, size: 36, color: Theme.of(context).colorScheme.primary),
          const SizedBox(height: 12),
          Text(titulo, style: texto.titleMedium, textAlign: TextAlign.center),
          if (causa != null) ...[
            const SizedBox(height: 6),
            Text(causa!, style: texto.bodyMedium, textAlign: TextAlign.center),
          ],
          if (etiquetaAccion != null && onAccion != null) ...[
            const SizedBox(height: 12),
            OutlinedButton(onPressed: onAccion, child: Text(etiquetaAccion!)),
          ],
        ],
      ),
    );
  }
}
