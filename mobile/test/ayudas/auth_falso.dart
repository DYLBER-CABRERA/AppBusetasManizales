import 'dart:async';

import 'package:busetas_app/nucleo/auth.dart';
import 'package:busetas_app/nucleo/notificacion_local.dart';

/// Autenticación de prueba: no toca Supabase. La contraseña correcta es [contrasenaValida].
class AuthFalso implements PuertoAuth {
  AuthFalso({
    this.disponible = true,
    String? correoInicial,
    this.contrasenaValida = 'secreto',
    this.correosRegistrados = const {},
  }) {
    if (correoInicial != null) {
      _correo = correoInicial;
      _token = 'token-falso';
    }
  }

  factory AuthFalso.conSesion([String correo = 'pasajera@correo.example']) =>
      AuthFalso(correoInicial: correo);

  @override
  final bool disponible;
  final String contrasenaValida;

  /// Correos que ya tienen cuenta: `registrar` lanza [ErrorCuentaExistente].
  final Set<String> correosRegistrados;
  final registros = <String>[];
  String? _correo;
  String? _token;
  final _cambios = StreamController<void>.broadcast();
  final intentos = <String>[];

  @override
  String? get token => _token;

  @override
  String? get correo => _correo;

  @override
  Stream<void> get cambios => _cambios.stream;

  @override
  Future<void> iniciarSesion(String correo, String contrasena) async {
    intentos.add(correo);
    if (!disponible) throw const ErrorAuth('El inicio de sesión no está disponible en esta instalación.');
    if (contrasena != contrasenaValida) throw const ErrorAuth('Correo o contraseña incorrectos.');
    _correo = correo;
    _token = 'token-falso';
    _cambios.add(null);
  }

  @override
  Future<void> registrar(String correo, String contrasena) async {
    registros.add(correo);
    if (!disponible) throw const ErrorAuth('El registro no está disponible en esta instalación.');
    if (correosRegistrados.contains(correo)) throw const ErrorCuentaExistente();
    if (contrasena.length < 6) {
      throw const ErrorAuth('La contraseña es muy débil. Usa al menos 6 caracteres, mejor con letras y números.');
    }
    _correo = correo;
    _token = 'token-falso';
    _cambios.add(null);
  }

  @override
  Future<void> cerrarSesion() async {
    _correo = null;
    _token = null;
    _cambios.add(null);
  }
}

class NotificacionLocalFalsa implements PuertoNotificacionLocal {
  final mostradas = <({int id, String titulo, String cuerpo})>[];
  int permisosPedidos = 0;

  @override
  Future<void> pedirPermiso() async => permisosPedidos++;

  @override
  Future<void> mostrar({required int id, required String titulo, required String cuerpo}) async =>
      mostradas.add((id: id, titulo: titulo, cuerpo: cuerpo));
}
