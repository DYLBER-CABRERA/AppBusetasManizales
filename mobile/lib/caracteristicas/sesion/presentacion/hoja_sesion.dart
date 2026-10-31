import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../../../nucleo/auth.dart';
import '../../../nucleo/sesion.dart';

const textoSinSesion = 'Inicia sesión para guardar. Con una cuenta guardas rutas y recibes avisos de llegada.';

/// Pide la sesión si hace falta (BR-02). Devuelve `true` si ya había sesión o si el
/// pasajero acaba de entrar; así la acción que la pidió puede continuar.
Future<bool> asegurarSesion(BuildContext context, WidgetRef ref) async {
  if (ref.read(sesionProvider).activa) return true;
  final entro = await showModalBottomSheet<bool>(
    context: context,
    isScrollControlled: true,
    showDragHandle: true,
    builder: (_) => const HojaSesion(),
  );
  return entro == true;
}

/// Hoja modal de inicio de sesión. En el prototipo no hay registro propio: el backend
/// crea los perfiles desde el panel de administración.
class HojaSesion extends ConsumerStatefulWidget {
  const HojaSesion({super.key});

  @override
  ConsumerState<HojaSesion> createState() => _HojaSesionState();
}

class _HojaSesionState extends ConsumerState<HojaSesion> {
  final _correo = TextEditingController();
  final _contrasena = TextEditingController();
  bool _ocultar = true;
  bool _enCurso = false;
  String? _errorCorreo;
  String? _errorContrasena;
  String? _errorGeneral;

  @override
  void dispose() {
    _correo.dispose();
    _contrasena.dispose();
    super.dispose();
  }

  Future<void> _entrar() async {
    final correo = _correo.text.trim();
    final contrasena = _contrasena.text;
    setState(() {
      _errorCorreo = correo.isEmpty ? 'Escribe tu correo.' : null;
      _errorContrasena = contrasena.isEmpty ? 'Escribe tu contraseña.' : null;
      _errorGeneral = null;
    });
    if (_errorCorreo != null || _errorContrasena != null) return;

    setState(() => _enCurso = true);
    try {
      await ref.read(sesionProvider.notifier).iniciarSesion(correo, contrasena);
      if (mounted) Navigator.of(context).pop(true);
    } on ErrorAuth catch (e) {
      if (mounted) setState(() => _errorGeneral = e.mensaje);
    } finally {
      if (mounted) setState(() => _enCurso = false);
    }
  }

  @override
  Widget build(BuildContext context) {
    final texto = Theme.of(context).textTheme;
    final esquema = Theme.of(context).colorScheme;
    final disponible = ref.watch(sesionProvider).disponible;
    return Padding(
      padding: EdgeInsets.fromLTRB(16, 0, 16, 16 + MediaQuery.viewInsetsOf(context).bottom),
      child: SingleChildScrollView(
        child: Column(
          mainAxisSize: MainAxisSize.min,
          crossAxisAlignment: CrossAxisAlignment.stretch,
          children: [
            Text('Iniciar sesión', style: texto.titleLarge),
            const SizedBox(height: 8),
            const Text(textoSinSesion),
            const SizedBox(height: 16),
            if (!disponible)
              const Text(
                'El inicio de sesión no está disponible en esta instalación. '
                'Puedes seguir usando la app sin cuenta.',
              )
            else ...[
              TextField(
                controller: _correo,
                enabled: !_enCurso,
                keyboardType: TextInputType.emailAddress,
                autofillHints: const [AutofillHints.email],
                autocorrect: false,
                textInputAction: TextInputAction.next,
                decoration: InputDecoration(labelText: 'Correo', errorText: _errorCorreo),
              ),
              const SizedBox(height: 12),
              TextField(
                controller: _contrasena,
                enabled: !_enCurso,
                obscureText: _ocultar,
                autofillHints: const [AutofillHints.password],
                textInputAction: TextInputAction.done,
                onSubmitted: (_) => _entrar(),
                decoration: InputDecoration(
                  labelText: 'Contraseña',
                  errorText: _errorContrasena,
                  suffixIcon: IconButton(
                    tooltip: _ocultar ? 'Mostrar contraseña' : 'Ocultar contraseña',
                    icon: Icon(_ocultar ? Icons.visibility : Icons.visibility_off),
                    onPressed: () => setState(() => _ocultar = !_ocultar),
                  ),
                ),
              ),
              if (_errorGeneral != null) ...[
                const SizedBox(height: 12),
                Semantics(
                  liveRegion: true,
                  child: Row(crossAxisAlignment: CrossAxisAlignment.start, children: [
                    Icon(Icons.error_outline, color: esquema.error),
                    const SizedBox(width: 8),
                    Expanded(child: Text(_errorGeneral!, style: TextStyle(color: esquema.error))),
                  ]),
                ),
              ],
              const SizedBox(height: 16),
              FilledButton(
                onPressed: _enCurso ? null : _entrar,
                child: _enCurso
                    ? const SizedBox(
                        width: 20,
                        height: 20,
                        child: CircularProgressIndicator(strokeWidth: 2.5),
                      )
                    : const Text('Entrar'),
              ),
              const SizedBox(height: 8),
              Text(
                'El registro de cuentas todavía no está disponible en el prototipo. '
                'Puedes seguir usando la app sin cuenta.',
                style: texto.bodySmall,
              ),
            ],
            const SizedBox(height: 8),
            TextButton(
              onPressed: _enCurso ? null : () => Navigator.of(context).pop(false),
              child: const Text('Ahora no'),
            ),
          ],
        ),
      ),
    );
  }
}
