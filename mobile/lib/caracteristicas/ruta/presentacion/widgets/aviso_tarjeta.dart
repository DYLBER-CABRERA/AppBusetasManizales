import 'package:flutter/material.dart';

/// Tarjeta de aviso (COM-15) con insignia de origen: Movilidad · Empresa · Aplicación.
class AvisoTarjeta extends StatelessWidget {
  const AvisoTarjeta({
    super.key,
    required this.origen,
    required this.titulo,
    required this.cuerpo,
    this.empresaNombre,
    this.etiquetaExtra,
    this.pie,
  });

  /// `empresa` | `movilidad` | `aplicativo`.
  final String origen;
  final String titulo;
  final String cuerpo;
  final String? empresaNombre;

  /// Segunda insignia (p. ej. el tipo de cambio de Movilidad: «Cierre», «Obra»).
  final String? etiquetaExtra;

  /// Línea pequeña al final (p. ej. «Hasta el 5 nov»).
  final String? pie;

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
            Wrap(
              spacing: 6,
              runSpacing: 4,
              children: [
                _Insignia(
                  etiquetaOrigen(origen, empresaNombre: empresaNombre),
                  esquema.primary.withValues(alpha: 0.16),
                ),
                if (etiquetaExtra != null)
                  _Insignia(etiquetaExtra!, esquema.onSurface.withValues(alpha: 0.1)),
              ],
            ),
            const SizedBox(height: 6),
            Text(titulo, style: texto.titleMedium),
            const SizedBox(height: 2),
            Text(cuerpo, style: texto.bodyMedium),
            if (pie != null) ...[
              const SizedBox(height: 6),
              Text(pie!, style: texto.bodySmall),
            ],
          ],
        ),
      ),
    );
  }
}

class _Insignia extends StatelessWidget {
  const _Insignia(this.texto, this.fondo);

  final String texto;
  final Color fondo;

  @override
  Widget build(BuildContext context) => Container(
        padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 2),
        decoration: BoxDecoration(color: fondo, borderRadius: BorderRadius.circular(8)),
        child: Text(texto, style: Theme.of(context).textTheme.labelMedium),
      );
}
