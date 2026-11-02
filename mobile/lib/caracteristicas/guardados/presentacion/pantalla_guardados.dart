import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';

import '../../../app/widgets/async_vista.dart';
import '../../../app/widgets/vacio_con_accion.dart';
import '../../../nucleo/errores.dart';
import '../../../nucleo/sesion.dart';
import '../../eta/dominio/eta.dart';
import '../../ruta/presentacion/ruta_providers.dart';
import '../../sesion/presentacion/hoja_sesion.dart';
import '../dominio/guardados.dart';
import 'guardados_providers.dart';

class PantallaGuardados extends ConsumerWidget {
  const PantallaGuardados({super.key});

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final sesion = ref.watch(sesionProvider);
    if (!sesion.activa) {
      return ListView(children: [
        const SizedBox(height: 24),
        VacioConAccion(
          titulo: 'Inicia sesión para guardar.',
          causa: 'Con una cuenta guardas rutas y recibes avisos de llegada.',
          etiquetaAccion: 'Iniciar sesión',
          onAccion: () => asegurarSesion(context, ref),
          icono: Icons.bookmark_border,
        ),
      ]);
    }

    final favoritos = ref.watch(favoritosProvider);
    final alertas = ref.watch(alertasProvider);

    // Cuenta sin perfil de pasajero o token rechazado: la lista nunca va a cargar.
    final rechazada = [favoritos.error, alertas.error]
        .any((e) => e is ErrorApi && e.esNoAutenticado);
    if (rechazada) {
      return ListView(children: [
        const SizedBox(height: 24),
        VacioConAccion(
          titulo: 'No pudimos validar tu sesión.',
          causa: 'Cierra sesión y vuelve a entrar.',
          etiquetaAccion: 'Cerrar sesión',
          onAccion: () => ref.read(sesionProvider.notifier).cerrarSesion(),
          icono: Icons.lock_outline,
        ),
      ]);
    }

    return RefreshIndicator(
      onRefresh: () async {
        ref.invalidate(favoritosProvider);
        ref.invalidate(alertasProvider);
        await Future.wait([
          ref.read(favoritosProvider.future).catchError((_) => <Favorito>[]),
          ref.read(alertasProvider.future).catchError((_) => <AlertaLlegada>[]),
        ]);
      },
      child: ListView(
        physics: const AlwaysScrollableScrollPhysics(),
        padding: const EdgeInsets.only(bottom: 24),
        children: [
          _CabeceraCuenta(correo: sesion.correo!),
          const _Encabezado('Rutas guardadas'),
          AsyncVista<List<Favorito>>(
            valor: favoritos,
            onReintentar: () => ref.invalidate(favoritosProvider),
            datos: (lista) => lista.isEmpty
                ? const Padding(
                    padding: EdgeInsets.fromLTRB(16, 4, 16, 8),
                    child: Text(
                      'Todavía no guardas nada. Abre una ruta y toca el marcador para guardarla.',
                    ),
                  )
                : Column(children: [for (final f in lista) _FilaFavorito(favorito: f)]),
          ),
          const _Encabezado('Alertas de llegada'),
          AsyncVista<List<AlertaLlegada>>(
            valor: alertas,
            onReintentar: () => ref.invalidate(alertasProvider),
            datos: (lista) => lista.isEmpty
                ? const Padding(
                    padding: EdgeInsets.fromLTRB(16, 4, 16, 8),
                    child: Text(
                      'Sin alertas activas. En el ETA de un paradero toca «Avisarme» para crear una.',
                    ),
                  )
                : Column(children: [for (final a in lista) _FilaAlerta(alerta: a)]),
          ),
        ],
      ),
    );
  }
}

class _CabeceraCuenta extends ConsumerWidget {
  const _CabeceraCuenta({required this.correo});

  final String correo;

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    return Padding(
      padding: const EdgeInsets.fromLTRB(16, 8, 8, 0),
      child: Row(children: [
        const Icon(Icons.account_circle_outlined),
        const SizedBox(width: 8),
        Expanded(child: Text(correo, overflow: TextOverflow.ellipsis)),
        TextButton(
          onPressed: () => ref.read(sesionProvider.notifier).cerrarSesion(),
          child: const Text('Cerrar sesión'),
        ),
      ]),
    );
  }
}

class _Encabezado extends StatelessWidget {
  const _Encabezado(this.texto);

  final String texto;

  @override
  Widget build(BuildContext context) => Padding(
        padding: const EdgeInsets.fromLTRB(16, 16, 16, 4),
        child: Semantics(
          header: true,
          child: Text(texto, style: Theme.of(context).textTheme.titleMedium),
        ),
      );
}

void _avisarError(BuildContext context, Object error) {
  final mensaje = error is ErrorApi ? error.mensaje : 'Ocurrió un error inesperado.';
  ScaffoldMessenger.of(context).showSnackBar(SnackBar(content: Text(mensaje)));
}

class _FilaFavorito extends ConsumerWidget {
  const _FilaFavorito({required this.favorito});

  final Favorito favorito;

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final texto = Theme.of(context).textTheme;
    final nombre = favorito.nombre ?? (favorito.esRuta ? 'Ruta' : 'Paradero');
    final disponible = favorito.disponible;
    return Semantics(
      label: '${favorito.esRuta ? 'Ruta' : 'Paradero'} guardado: $nombre'
          '${disponible ? '' : '. Ya no disponible'}',
      excludeSemantics: true,
      child: ListTile(
        minTileHeight: 56,
        enabled: disponible,
        leading: Icon(favorito.esRuta ? Icons.route : Icons.place_outlined),
        title: Text(nombre),
        subtitle: disponible ? null : Text('Ya no disponible', style: texto.bodyMedium),
        onTap: disponible && favorito.esRuta && favorito.rutaId != null
            ? () => context.push('/ruta/${favorito.rutaId}')
            : null,
        trailing: IconButton(
          tooltip: 'Quitar de guardados',
          constraints: const BoxConstraints(minWidth: 48, minHeight: 48),
          icon: const Icon(Icons.delete_outline),
          onPressed: () async {
            try {
              await ref.read(accionesGuardadosProvider).quitarFavorito(favorito.id);
              if (context.mounted) {
                ScaffoldMessenger.of(context).showSnackBar(const SnackBar(content: Text('Quitado')));
              }
            } on ErrorApi catch (e) {
              if (context.mounted) _avisarError(context, e);
            }
          },
        ),
      ),
    );
  }
}

class _FilaAlerta extends ConsumerWidget {
  const _FilaAlerta({required this.alerta});

  final AlertaLlegada alerta;

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final ruta = ref
        .watch(todasLasRutasProvider)
        .value
        ?.where((r) => r.id == alerta.rutaId)
        .firstOrNull
        ?.nombre;
    final paradero = ref
        .watch(rutaDetalleProvider(alerta.rutaId))
        .value
        ?.paraderos
        .where((p) => p.paraderoId == alerta.paraderoId)
        .firstOrNull
        ?.nombre;
    final titulo = [ruta ?? 'Ruta', tituloParadero(paradero)].join(' · ');
    final detalle = alerta.estado == 'notificada'
        ? 'Ya te avisamos · vuelve a avisar a ${alerta.distanciaAvisoM} m'
        : 'Te avisamos cuando esté a ${alerta.distanciaAvisoM} m';
    return Semantics(
      label: 'Alerta de llegada. $titulo. $detalle',
      excludeSemantics: true,
      child: ListTile(
        minTileHeight: 56,
        leading: const Icon(Icons.notifications_active_outlined),
        title: Text(titulo),
        subtitle: Text(detalle),
        onTap: () => context.push('/ruta/${alerta.rutaId}/paradero/${alerta.paraderoId}'),
        trailing: IconButton(
          tooltip: 'Quitar alerta',
          constraints: const BoxConstraints(minWidth: 48, minHeight: 48),
          icon: const Icon(Icons.delete_outline),
          onPressed: () async {
            try {
              await ref.read(accionesGuardadosProvider).quitarAlerta(alerta.id);
              if (context.mounted) {
                ScaffoldMessenger.of(context)
                    .showSnackBar(const SnackBar(content: Text('Alerta quitada')));
              }
            } on ErrorApi catch (e) {
              if (context.mounted) _avisarError(context, e);
            }
          },
        ),
      ),
    );
  }
}
