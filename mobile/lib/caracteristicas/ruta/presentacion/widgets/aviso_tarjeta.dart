import 'package:flutter/material.dart';

/// Tarjeta de aviso (COM-15) con insignia de origen: Movilidad · Empresa · Aplicación.
class AvisoTarjeta extends StatelessWidget {
  const AvisoTarjeta({
    super.key,
    required this.origen,
    required this.titulo,
    required this.cuerpo,
    this.empresaNombre,
  });

  /// `empresa` | `movilidad` | `aplicativo`.
  final String origen;
  final String titulo;
  final String cuerpo;
  final String? empresaNombre;

  static String etiquetaOrigen(String origen, {String? empresaNombre}) => switch (origen) {
        'movilidad' => 'Movilidad',
        'empresa' => empresaNombre ?? 'Empresa',
        _ => 'Aplicación',
      };

  @override
  Widget build(BuildContext context) {
    final esquema = Theme.of(context).colorScheme;
    final texto = Theme.of(context).textTheme;
    return Card(
      margin: const EdgeInsets.symmetric(horizontal: 16, vertical: 6),
      elevation: 0,
      color: esquema.surface,
      shape: RoundedRectangleBorder(
        borderRadius: BorderRadius.circular(12),
        side: BorderSide(color: esquema.onSurface.withValues(alpha: 0.2)),
      ),
      child: Padding(
        padding: const EdgeInsets.all(12),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Container(
              padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 2),
              decoration: BoxDecoration(
                color: esquema.primary.withValues(alpha: 0.16),
                borderRadius: BorderRadius.circular(8),
              ),
              child: Text(etiquetaOrigen(origen, empresaNombre: empresaNombre),
                  style: texto.labelMedium),
            ),
            const SizedBox(height: 6),
            Text(titulo, style: texto.titleMedium),
            const SizedBox(height: 2),
            Text(cuerpo, style: texto.bodyMedium),
          ],
        ),
      ),
    );
  }
}
