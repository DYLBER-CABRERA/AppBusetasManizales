import 'package:flutter/material.dart';

import '../nucleo/configuracion.dart';

/// Banner permanente bajo la barra superior (CLAUDE.md §6).
class BannerEjemplo extends StatelessWidget {
  const BannerEjemplo({super.key});

  @override
  Widget build(BuildContext context) {
    final esquema = Theme.of(context).colorScheme;
    return Semantics(
      container: true,
      child: Container(
        width: double.infinity,
        color: esquema.primary.withValues(alpha: 0.14),
        padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 6),
        child: Row(
          children: [
            Icon(Icons.info_outline, size: 16, color: esquema.onSurface),
            const SizedBox(width: 8),
            Expanded(
              child: Text(
                Configuracion.textoBanner,
                style: Theme.of(context).textTheme.labelMedium?.copyWith(color: esquema.onSurface),
              ),
            ),
          ],
        ),
      ),
    );
  }
}
