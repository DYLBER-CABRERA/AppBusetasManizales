import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../../../nucleo/auth.dart';
import '../../../nucleo/sesion.dart';

const textoSinSesion = 'Inicia sesión para guardar. Con una cuenta guardas rutas y recibes avisos de llegada.';

/// Pide la sesión si hace falta (BR-02). Devuelve `true` si ya había sesión o si el
/// pasajero acaba de entrar; así la acción que la pidió puede continuar.
Future<bool> asegurarSesion(BuildContext context, WidgetRef ref) async {
  if (ref.read(sesionProvider).activa) return true;
  final notificador = ref.read(sesionProvider.notifier);
  final entro = await showModalBottomSheet<bool>(
    context: context,
    isScrollControlled: true,
    showDragHandle: true,
    builder: (_) => const HojaSesion(),
  );
  // Si cerró la hoja con la cuenta creada pero sin perfil, no se deja la sesión a medias.
  if (entro != true) await notificador.cancelarPendiente();
  return entro == true;
}

enum _Modo { entrar, crear, completar }

/// Hoja modal de sesión: iniciar sesión, crear cuenta o completar el perfil de una
/// cuenta que se registró sin terminarlo.
class HojaSesion extends ConsumerStatefulWidget {
  const HojaSesion({super.key});

  @override
  ConsumerState<HojaSesion> createState() => _HojaSesionState();
}

class _HojaSesionState extends ConsumerState<HojaSesion> {
  final _nombre = TextEditingController();
  final _apellido = TextEditingController();
  final _celular = TextEditingController();
  final _correo = TextEditingController();
  final _contrasena = TextEditingController();
  final _confirmacion = TextEditingController();
  _Modo _modo = _Modo.entrar;
  bool _ocultar = true;
  bool _enCurso = false;
  final _errores = <String, String>{};
  String? _errorGeneral;

  @override
  void dispose() {
    for (final c in [_nombre, _apellido, _celular, _correo, _contrasena, _confirmacion]) {
      c.dispose();
    }
    super.dispose();
  }

  void _cambiarModo(_Modo modo) => setState(() {
        _modo = modo;
        _errores.clear();
        _errorGeneral = null;
      });

  /// Validación básica en el cliente; el backend vuelve a validar.
  bool _validar() {
    final correo = _correo.text.trim();
    final errores = <String, String>{};
    if (_modo != _Modo.completar) {
      if (correo.isEmpty) {
        errores['correo'] = 'Escribe tu correo.';
      } else if (_modo == _Modo.crear && !RegExp(r'^[^@\s]+@[^@\s]+\.[^@\s]+$').hasMatch(correo)) {
        errores['correo'] = 'Ese correo no parece válido.';
      }
      if (_contrasena.text.isEmpty) {
        errores['contrasena'] = 'Escribe tu contraseña.';
      } else if (_modo == _Modo.crear && _contrasena.text.length < 6) {
        errores['contrasena'] = 'Usa al menos 6 caracteres.';
      }
    }
    if (_modo != _Modo.entrar) {
      if (_nombre.text.trim().isEmpty) {
        errores['nombre'] = 'Escribe tu nombre.';
      } else if (_nombre.text.trim().length > 60) {
        errores['nombre'] = 'Máximo 60 caracteres.';
      }
      if (_apellido.text.trim().isEmpty) {
        errores['apellido'] = 'Escribe tu apellido.';
      } else if (_apellido.text.trim().length > 60) {
        errores['apellido'] = 'Máximo 60 caracteres.';
      }
      if (!_celularValido(_celular.text)) {
        errores['celular'] = 'Escribe un celular colombiano de 10 dígitos que empiece por 3.';
      }
      if (_modo == _Modo.crear && _confirmacion.text != _contrasena.text) {
        errores['confirmacion'] = 'Las contraseñas no coinciden.';
      }
    }
    setState(() {
      _errores
        ..clear()
        ..addAll(errores);
      _errorGeneral = null;
    });
    return errores.isEmpty;
  }

  /// Acepta `+57`, espacios, guiones, puntos y paréntesis, igual que el backend.
  static bool _celularValido(String texto) {
    var digitos = texto.replaceAll(RegExp(r'[\s\-.()]'), '');
    if (digitos.startsWith('+57')) {
      digitos = digitos.substring(3);
    } else if (digitos.startsWith('57') && digitos.length == 12) {
      digitos = digitos.substring(2);
    }
    return RegExp(r'^3\d{9}$').hasMatch(digitos);
  }

  DatosPerfil _datos() => DatosPerfil(
        nombre: _nombre.text.trim(),
        apellido: _apellido.text.trim(),
        celular: _celular.text.trim(),
      );

  Future<void> _enviar() async {
    if (!_validar()) return;
    final sesion = ref.read(sesionProvider.notifier);
    setState(() => _enCurso = true);
    try {
      switch (_modo) {
        case _Modo.entrar:
          await sesion.iniciarSesion(_correo.text.trim(), _contrasena.text);
        case _Modo.crear:
          await sesion.registrar(_correo.text.trim(), _contrasena.text, _datos());
        case _Modo.completar:
          await sesion.completarPerfil(_datos());
      }
      if (mounted) Navigator.of(context).pop(true);
    } on ErrorPerfilPendiente catch (e) {
      if (mounted) {
        setState(() {
          _modo = _Modo.completar;
          _errores.clear();
          _errorGeneral = e.mensaje;
        });
      }
    } on ErrorPerfilInvalido catch (e) {
      if (mounted) {
        setState(() {
          _errores
            ..clear()
            ..addAll(e.campos);
          _errorGeneral = e.mensaje;
        });
      }
    } on ErrorAuth catch (e) {
      if (mounted) setState(() => _errorGeneral = e.mensaje);
    } finally {
      if (mounted) setState(() => _enCurso = false);
    }
  }

  Widget _campo(
    String clave,
    TextEditingController controlador,
    String etiqueta, {
    TextInputType? teclado,
    List<String>? sugerencias,
    TextInputAction accion = TextInputAction.next,
    bool secreto = false,
    Widget? sufijo,
    TextCapitalization mayusculas = TextCapitalization.none,
    VoidCallback? alEnviar,
  }) =>
      Padding(
        padding: const EdgeInsets.only(bottom: 12),
        child: TextField(
          controller: controlador,
          enabled: !_enCurso,
          keyboardType: teclado,
          autofillHints: sugerencias,
          autocorrect: false,
          obscureText: secreto,
          textInputAction: accion,
          textCapitalization: mayusculas,
          onSubmitted: alEnviar == null ? null : (_) => alEnviar(),
          decoration: InputDecoration(labelText: etiqueta, errorText: _errores[clave], suffixIcon: sufijo),
        ),
      );

  @override
  Widget build(BuildContext context) {
    final texto = Theme.of(context).textTheme;
    final esquema = Theme.of(context).colorScheme;
    final disponible = ref.watch(sesionProvider).disponible;
    final crear = _modo == _Modo.crear;
    final completar = _modo == _Modo.completar;
    final titulo = switch (_modo) {
      _Modo.entrar => 'Iniciar sesión',
      _Modo.crear => 'Crear cuenta',
      _Modo.completar => 'Completa tu perfil',
    };
    final botonVer = IconButton(
      tooltip: _ocultar ? 'Mostrar contraseña' : 'Ocultar contraseña',
      icon: Icon(_ocultar ? Icons.visibility : Icons.visibility_off),
      onPressed: () => setState(() => _ocultar = !_ocultar),
    );
    return Padding(
      padding: EdgeInsets.fromLTRB(16, 0, 16, 16 + MediaQuery.viewInsetsOf(context).bottom),
      child: SingleChildScrollView(
        child: Column(
          mainAxisSize: MainAxisSize.min,
          crossAxisAlignment: CrossAxisAlignment.stretch,
          children: [
            Text(titulo, style: texto.titleLarge),
            const SizedBox(height: 8),
            Text(completar
                ? 'Tu cuenta ya existe, pero falta tu nombre y tu celular para terminar el registro.'
                : textoSinSesion),
            const SizedBox(height: 16),
            if (!disponible)
              const Text(
                'El inicio de sesión no está disponible en esta instalación. '
                'Puedes seguir usando la app sin cuenta.',
              )
            else ...[
              if (crear || completar) ...[
                _campo('nombre', _nombre, 'Nombre',
                    sugerencias: const [AutofillHints.givenName],
                    mayusculas: TextCapitalization.words),
                _campo('apellido', _apellido, 'Apellido',
                    sugerencias: const [AutofillHints.familyName],
                    mayusculas: TextCapitalization.words),
                _campo('celular', _celular, 'Celular',
                    teclado: TextInputType.phone,
                    sugerencias: const [AutofillHints.telephoneNumber],
                    accion: completar ? TextInputAction.done : TextInputAction.next,
                    alEnviar: completar ? _enviar : null),
              ],
              if (!completar) ...[
                _campo('correo', _correo, 'Correo',
                    teclado: TextInputType.emailAddress, sugerencias: const [AutofillHints.email]),
                _campo('contrasena', _contrasena, 'Contraseña',
                    secreto: _ocultar,
                    sugerencias: [crear ? AutofillHints.newPassword : AutofillHints.password],
                    accion: crear ? TextInputAction.next : TextInputAction.done,
                    sufijo: botonVer,
                    alEnviar: crear ? null : _enviar),
              ],
              if (crear)
                _campo('confirmacion', _confirmacion, 'Confirma la contraseña',
                    secreto: _ocultar,
                    accion: TextInputAction.done,
                    alEnviar: _enviar),
              if (_errorGeneral != null) ...[
                Semantics(
                  liveRegion: true,
                  child: Row(crossAxisAlignment: CrossAxisAlignment.start, children: [
                    Icon(completar && _errores.isEmpty ? Icons.info_outline : Icons.error_outline,
                        color: esquema.error),
                    const SizedBox(width: 8),
                    Expanded(child: Text(_errorGeneral!, style: TextStyle(color: esquema.error))),
                  ]),
                ),
                const SizedBox(height: 12),
              ],
              FilledButton(
                onPressed: _enCurso ? null : _enviar,
                child: _enCurso
                    ? const SizedBox(
                        width: 20,
                        height: 20,
                        child: CircularProgressIndicator(strokeWidth: 2.5),
                      )
                    : Text(switch (_modo) {
                        _Modo.entrar => 'Entrar',
                        _Modo.crear => 'Crear cuenta',
                        _Modo.completar => 'Guardar y continuar',
                      }),
              ),
              if (!completar)
                TextButton(
                  onPressed: _enCurso ? null : () => _cambiarModo(crear ? _Modo.entrar : _Modo.crear),
                  child: Text(crear ? 'Ya tengo cuenta · Iniciar sesión' : 'No tengo cuenta · Crear cuenta'),
                ),
            ],
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
