import 'package:flutter/material.dart';

/// Marcador de las pantallas que llegan en un bloque posterior (M1 a M4).
class PantallaPendiente extends StatelessWidget {
  const PantallaPendiente({super.key, required this.titulo, required this.bloque});

  final String titulo;
  final String bloque;

  @override
  Widget build(BuildContext context) {
    return Center(
      child: Padding(
        padding: const EdgeInsets.all(24),
        child: Text(
          '$titulo\nLlega en el bloque $bloque.',
          textAlign: TextAlign.center,
          style: Theme.of(context).textTheme.titleMedium,
        ),
      ),
    );
  }
}
