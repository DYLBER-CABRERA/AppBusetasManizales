import 'package:flutter/material.dart';

/// Sello de ruta (COM-03): color de la ruta + código público (o la inicial).
class SelloRuta extends StatelessWidget {
  const SelloRuta({super.key, required this.codigo, required this.color, this.tamano = 44});

  final String codigo;
  final Color color;
  final double tamano;

  @override
  Widget build(BuildContext context) {
    return ExcludeSemantics(
      child: Container(
        width: tamano,
        height: tamano,
        alignment: Alignment.center,
        decoration: BoxDecoration(color: color, borderRadius: BorderRadius.circular(12)),
        child: Text(
          codigo,
          maxLines: 1,
          style: Theme.of(context).textTheme.titleMedium?.copyWith(
                color: Colors.white,
                fontWeight: FontWeight.w800,
              ),
        ),
      ),
    );
  }
}
