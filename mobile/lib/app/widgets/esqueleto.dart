import 'package:flutter/material.dart';

/// Filas de 56 px con relieve suave; se detienen si el sistema pide menos movimiento.
class EsqueletoLista extends StatefulWidget {
  const EsqueletoLista({super.key, this.filas = 4});

  final int filas;

  @override
  State<EsqueletoLista> createState() => _EsqueletoListaState();
}

class _EsqueletoListaState extends State<EsqueletoLista> with SingleTickerProviderStateMixin {
  late final AnimationController _controlador =
      AnimationController(vsync: this, duration: const Duration(milliseconds: 1100));

  @override
  void didChangeDependencies() {
    super.didChangeDependencies();
    if (MediaQuery.disableAnimationsOf(context)) {
      _controlador.stop();
    } else if (!_controlador.isAnimating) {
      _controlador.repeat(reverse: true);
    }
  }

  @override
  void dispose() {
    _controlador.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    final base = Theme.of(context).colorScheme.onSurface;
    return Semantics(
      label: 'Cargando',
      child: ExcludeSemantics(
        child: AnimatedBuilder(
          animation: _controlador,
          builder: (context, _) {
            final alfa = 0.06 + 0.06 * _controlador.value;
            return Column(
              children: [
                for (var i = 0; i < widget.filas; i++)
                  Container(
                    height: 56,
                    margin: const EdgeInsets.symmetric(horizontal: 16, vertical: 6),
                    decoration: BoxDecoration(
                      color: base.withValues(alpha: alfa),
                      borderRadius: BorderRadius.circular(12),
                    ),
                  ),
              ],
            );
          },
        ),
      ),
    );
  }
}
