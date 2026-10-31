import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:supabase_flutter/supabase_flutter.dart';

import 'configuracion.dart';
import 'errores.dart';

/// Error de inicio de sesión con el mensaje ya listo para el pasajero.
class ErrorAuth implements Exception {
  const ErrorAuth(this.mensaje);

  final String mensaje;

  @override
  String toString() => 'ErrorAuth($mensaje)';
}

/// Puerto de autenticación. Supabase Auth se usa **solo** para esto: los datos van
/// por la API del backend (nunca se consultan tablas de Supabase desde la app).
abstract class PuertoAuth {
  /// `false` si la compilación no trae `SUPABASE_URL` y `SUPABASE_ANON_KEY`.
  bool get disponible;

  /// Token JWT vigente o `null` sin sesión. Nunca se registra.
  String? get token;
  String? get correo;

  /// Avisa de cada inicio o cierre de sesión (y de la renovación del token).
  Stream<void> get cambios;

  Future<void> iniciarSesion(String correo, String contrasena);
  Future<void> cerrarSesion();
}

class AuthSupabase implements PuertoAuth {
  GoTrueClient get _auth => Supabase.instance.client.auth;

  @override
  bool get disponible => true;

  @override
  String? get token => _auth.currentSession?.accessToken;

  @override
  String? get correo => _auth.currentUser?.email;

  @override
  Stream<void> get cambios => _auth.onAuthStateChange.map((_) {});

  @override
  Future<void> iniciarSesion(String correo, String contrasena) async {
    try {
      await _auth.signInWithPassword(email: correo.trim(), password: contrasena);
    } on AuthRetryableFetchException {
      throw const ErrorAuth(mensajeSinConexion);
    } on AuthException catch (e) {
      throw ErrorAuth(_traducir(e));
    } catch (_) {
      throw const ErrorAuth(mensajeSinConexion);
    }
  }

  @override
  Future<void> cerrarSesion() async {
    try {
      await _auth.signOut();
    } catch (_) {
      // Sin red igual se descarta la sesión local.
      await _auth.signOut(scope: SignOutScope.local);
    }
  }

  static String _traducir(AuthException e) {
    final texto = '${e.code ?? ''} ${e.message}'.toLowerCase();
    if (texto.contains('invalid_credentials') || texto.contains('invalid login credentials')) {
      return 'Correo o contraseña incorrectos.';
    }
    if (texto.contains('email_not_confirmed') || texto.contains('not confirmed')) {
      return 'Confirma tu correo antes de entrar.';
    }
    if (texto.contains('rate') && texto.contains('limit')) {
      return 'Demasiados intentos. Espera un momento y vuelve a probar.';
    }
    return 'No pudimos iniciar sesión. Intenta de nuevo.';
  }
}

/// Compilación sin Supabase configurado: la app funciona sin cuenta (BR-01).
class AuthNoDisponible implements PuertoAuth {
  @override
  bool get disponible => false;

  @override
  String? get token => null;

  @override
  String? get correo => null;

  @override
  Stream<void> get cambios => const Stream.empty();

  @override
  Future<void> iniciarSesion(String correo, String contrasena) async => throw const ErrorAuth(
        'El inicio de sesión no está disponible en esta instalación. Puedes seguir usando la app sin cuenta.',
      );

  @override
  Future<void> cerrarSesion() async {}
}

final authProvider = Provider<PuertoAuth>(
  (ref) => Configuracion.supabaseUrl.isEmpty || Configuracion.supabaseAnonKey.isEmpty
      ? AuthNoDisponible()
      : AuthSupabase(),
);
