import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../../../../nucleo/errores.dart';
import '../../../guardados/presentacion/guardados_providers.dart';
import '../../../sesion/presentacion/hoja_sesion.dart';

/// Marcador de la ficha: guarda o quita la ruta de favoritos. Sin sesión abre la hoja
/// «Inicia sesión para guardar» y, al entrar, guarda la ruta (la acción que se pidió).
class BotonGuardarRuta extends ConsumerWidget {
  const BotonGuardarRuta({super.key, required this.rutaId});

  final String rutaId;

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final favorito = ref
        .watch(favoritosProvider)
        .value
        ?.where((f) => f.esRuta && f.rutaId == rutaId)
        .firstOrNull;
    final guardada = favorito != null;

    return IconButton(
      tooltip: guardada ? 'Quitar de guardados' : 'Guardar ruta',
      isSelected: guardada,
      constraints: const BoxConstraints(minWidth: 48, minHeight: 48),
      icon: const Icon(Icons.bookmark_border),
      selectedIcon: const Icon(Icons.bookmark),
      onPressed: () async {
        final mensajes = ScaffoldMessenger.of(context);
        final acciones = ref.read(accionesGuardadosProvider);
        // Con un favorito cargado ya hay sesión; si no, se pide (y se guarda al entrar).
        if (favorito == null && !await asegurarSesion(context, ref)) return;
        try {
          if (favorito != null) {
            await acciones.quitarFavorito(favorito.id);
            mensajes.showSnackBar(const SnackBar(content: Text('Quitado')));
          } else {
            await acciones.guardarRuta(rutaId);
            mensajes.showSnackBar(const SnackBar(content: Text('Guardado')));
          }
        } on ErrorApi catch (e) {
          mensajes.showSnackBar(SnackBar(content: Text(e.mensaje)));
        }
      },
    );
  }
}
