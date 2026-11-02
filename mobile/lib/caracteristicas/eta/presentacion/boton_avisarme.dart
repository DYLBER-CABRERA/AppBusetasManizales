import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../../../nucleo/errores.dart';
import '../../guardados/dominio/guardados.dart';
import '../../guardados/presentacion/guardados_providers.dart';
import '../../sesion/presentacion/hoja_sesion.dart';

/// «Avisarme cuando esté a 300 m» (HU-P11). Exige sesión (BR-02): sin ella abre la hoja
/// de inicio de sesión y, al entrar, crea la alerta. Si ya existe, permite quitarla.
class BotonAvisarme extends ConsumerWidget {
  const BotonAvisarme({super.key, required this.rutaId, required this.paraderoId});

  final String rutaId;
  final String paraderoId;

  /// Distancia por defecto del parámetro `distancia_aviso_llegada_m`.
  static const distanciaPorDefectoM = 300;

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final texto = Theme.of(context).textTheme;
    final esquema = Theme.of(context).colorScheme;
    final alerta = ref
        .watch(alertasProvider)
        .value
        ?.where((a) => a.coincideCon(rutaId, paraderoId) && a.estado != 'desactivada')
        .firstOrNull;

    return Padding(
      padding: const EdgeInsets.fromLTRB(16, 16, 16, 0),
      child: alerta == null
          ? Column(
              crossAxisAlignment: CrossAxisAlignment.stretch,
              children: [
                FilledButton.icon(
                  icon: const Icon(Icons.notifications_active_outlined),
                  label: const Text('Avisarme cuando esté a $distanciaPorDefectoM m'),
                  onPressed: () => _crear(context, ref),
                ),
                const SizedBox(height: 8),
                Text(
                  'Las alertas necesitan una cuenta. Recibirás el aviso con la app abierta.',
                  style: texto.bodySmall,
                ),
              ],
            )
          : _AlertaActiva(
              alerta: alerta,
              color: esquema.primary,
              onQuitar: () => _quitar(context, ref, alerta),
            ),
    );
  }

  Future<void> _crear(BuildContext context, WidgetRef ref) async {
    final mensajes = ScaffoldMessenger.of(context);
    final acciones = ref.read(accionesGuardadosProvider);
    if (!await asegurarSesion(context, ref)) return;
    try {
      await acciones.crearAlerta(rutaId: rutaId, paraderoId: paraderoId);
      mensajes.showSnackBar(const SnackBar(content: Text('Alerta activada')));
    } on ErrorApi catch (e) {
      if (e.codigo == 'CONFLICTO_NEGOCIO') {
        ref.invalidate(alertasProvider);
        mensajes.showSnackBar(
          const SnackBar(content: Text('Ya tenías una alerta activa para este paradero.')),
        );
      } else {
        mensajes.showSnackBar(SnackBar(content: Text(e.mensaje)));
      }
    }
  }

  Future<void> _quitar(BuildContext context, WidgetRef ref, AlertaLlegada alerta) async {
    final mensajes = ScaffoldMessenger.of(context);
    try {
      await ref.read(accionesGuardadosProvider).quitarAlerta(alerta.id);
      mensajes.showSnackBar(const SnackBar(content: Text('Alerta quitada')));
    } on ErrorApi catch (e) {
      mensajes.showSnackBar(SnackBar(content: Text(e.mensaje)));
    }
  }
}

class _AlertaActiva extends StatelessWidget {
  const _AlertaActiva({required this.alerta, required this.color, required this.onQuitar});

  final AlertaLlegada alerta;
  final Color color;
  final VoidCallback onQuitar;

  @override
  Widget build(BuildContext context) {
    final texto = Theme.of(context).textTheme;
    return Container(
      padding: const EdgeInsets.all(12),
      decoration: BoxDecoration(
        color: color.withValues(alpha: 0.12),
        borderRadius: BorderRadius.circular(12),
        border: Border.all(color: color, width: 1.5),
      ),
      child: Row(
        children: [
          Icon(Icons.notifications_active, color: color),
          const SizedBox(width: 12),
          Expanded(
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Text('Alerta activa', style: texto.titleMedium),
                Text('Te avisamos cuando la buseta esté a ${alerta.distanciaAvisoM} m.'),
              ],
            ),
          ),
          TextButton(onPressed: onQuitar, child: const Text('Quitar alerta')),
        ],
      ),
    );
  }
}
