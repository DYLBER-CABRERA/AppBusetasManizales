import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:intl/intl.dart';

import '../../../app/widgets/async_vista.dart';
import '../../../app/widgets/vacio_con_accion.dart';
import '../../ruta/presentacion/widgets/aviso_tarjeta.dart';
import '../datos/avisos_repositorio.dart';
import '../dominio/aviso.dart';

/// Avisos vigentes. Se vuelven a pedir al deslizar hacia abajo o con **Actualizar**.
final avisosProvider = FutureProvider.autoDispose<List<Aviso>>(
  (ref) => ref.watch(avisosRepositorioProvider).vigentes(),
);

class PantallaAvisos extends ConsumerWidget {
  const PantallaAvisos({super.key});

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final avisos = ref.watch(avisosProvider);
    return RefreshIndicator(
      onRefresh: () async {
        ref.invalidate(avisosProvider);
        await ref.read(avisosProvider.future).catchError((_) => <Aviso>[]);
      },
      child: ListView(
        physics: const AlwaysScrollableScrollPhysics(),
        padding: const EdgeInsets.only(top: 8, bottom: 24),
        children: [
          AsyncVista<List<Aviso>>(
            valor: avisos,
            onReintentar: () => ref.invalidate(avisosProvider),
            datos: (lista) => lista.isEmpty
                ? VacioConAccion(
                    titulo: 'No hay avisos vigentes.',
                    causa: 'Cuando una empresa o Movilidad publique un cambio, lo verás aquí.',
                    etiquetaAccion: 'Actualizar',
                    onAccion: () => ref.invalidate(avisosProvider),
                    icono: Icons.notifications_none,
                  )
                : Column(children: [for (final aviso in lista) _TarjetaDeAviso(aviso: aviso)]),
          ),
        ],
      ),
    );
  }
}

class _TarjetaDeAviso extends StatelessWidget {
  const _TarjetaDeAviso({required this.aviso});

  final Aviso aviso;

  @override
  Widget build(BuildContext context) {
    final formato = DateFormat('d MMM', 'es');
    final vigencia = aviso.hasta == null ? null : 'Hasta el ${formato.format(aviso.hasta!.toLocal())}';
    return AvisoTarjeta(
      origen: aviso.origen,
      titulo: aviso.titulo,
      cuerpo: aviso.cuerpo,
      empresaNombre: aviso.empresaNombre,
      etiquetaExtra: aviso.etiquetaCambio,
      pie: vigencia,
    );
  }
}
