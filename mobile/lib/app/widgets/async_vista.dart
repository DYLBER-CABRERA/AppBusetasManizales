import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import 'banner_error.dart';
import 'esqueleto.dart';

/// Pinta un [AsyncValue] con los estados de la matriz de la Actividad 4:
/// cargando (esqueleto), error de conexión (banner con **Reintentar** que conserva
/// lo ya cargado) y datos. No hace scroll: va dentro de un `ListView` o similar,
/// y `datos` devuelve un widget que se ajusta a su contenido.
class AsyncVista<T> extends StatelessWidget {
  const AsyncVista({
    super.key,
    required this.valor,
    required this.datos,
    required this.onReintentar,
    this.cargando,
  });

  final AsyncValue<T> valor;
  final Widget Function(T datos) datos;
  final VoidCallback onReintentar;
  final Widget? cargando;

  @override
  Widget build(BuildContext context) {
    if (valor.hasValue) {
      final contenido = datos(valor.requireValue);
      if (!valor.hasError) return contenido;
      return Column(
        mainAxisSize: MainAxisSize.min,
        crossAxisAlignment: CrossAxisAlignment.stretch,
        children: [
          BannerError.desdeError(valor.error!, onReintentar: onReintentar),
          contenido,
        ],
      );
    }
    if (valor.hasError) {
      return Column(
        mainAxisSize: MainAxisSize.min,
        crossAxisAlignment: CrossAxisAlignment.stretch,
        children: [BannerError.desdeError(valor.error!, onReintentar: onReintentar)],
      );
    }
    return cargando ?? const EsqueletoLista();
  }
}
