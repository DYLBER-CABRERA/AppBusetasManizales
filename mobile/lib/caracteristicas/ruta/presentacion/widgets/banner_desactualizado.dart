import 'package:flutter/material.dart';

/// Datos desactualizados: «Última actualización hace N s» + **Actualizar**.
/// Tono de aviso (ámbar) con ícono y texto: no depende solo del color.
class BannerDesactualizado extends StatelessWidget {
  const BannerDesactualizado({super.key, required this.segundos, required this.onActualizar});

  final int segundos;
  final VoidCallback onActualizar;

  static const fondo = Color(0xFFFFF1C2);
  static const borde = Color(0xFF8A6A00);
  static const tinta = Color(0xFF13271E);

  @override
  Widget build(BuildContext context) {
    return Semantics(
      liveRegion: true,
      container: true,
      child: Container(
        width: double.infinity,
        padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 8),
        decoration: const BoxDecoration(
          color: fondo,
          border: Border(left: BorderSide(color: borde, width: 4)),
        ),
        child: Row(
          children: [
            const Icon(Icons.schedule, color: borde),
            const SizedBox(width: 12),
            Expanded(
              child: Text(
                'Última actualización hace $segundos s',
                style: const TextStyle(color: tinta),
              ),
            ),
            TextButton(
              style: TextButton.styleFrom(foregroundColor: tinta),
              onPressed: onActualizar,
              child: const Text('Actualizar'),
            ),
          ],
        ),
      ),
    );
  }
}
