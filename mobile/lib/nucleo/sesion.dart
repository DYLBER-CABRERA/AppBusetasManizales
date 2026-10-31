import 'dart:async';

import 'package:flutter_riverpod/flutter_riverpod.dart';

import 'auth.dart';
import 'cliente_api.dart';
import 'errores.dart';

class EstadoSesion {
  const EstadoSesion({required this.disponible, this.correo});

  /// Hay Supabase configurado en esta compilación.
  final bool disponible;
  final String? correo;

  bool get activa => correo != null;

  @override
  bool operator ==(Object other) =>
      other is EstadoSesion && other.disponible == disponible && other.correo == correo;

  @override
  int get hashCode => Object.hash(disponible, correo);
}

/// Sesión del pasajero (BR-02: solo se exige para Guardados y alertas).
class SesionNotifier extends Notifier<EstadoSesion> {
  StreamSubscription<void>? _suscripcion;

  PuertoAuth get _auth => ref.read(authProvider);

  @override
  EstadoSesion build() {
    final auth = ref.watch(authProvider);
    _suscripcion = auth.cambios.listen((_) => _sincronizar());
    ref.onDispose(() => _suscripcion?.cancel());
    return EstadoSesion(disponible: auth.disponible, correo: auth.token == null ? null : auth.correo);
  }

  void _sincronizar() {
    final auth = _auth;
    state = EstadoSesion(disponible: auth.disponible, correo: auth.token == null ? null : auth.correo);
  }

  /// Entra y comprueba con `GET /yo` que la cuenta sea de pasajero. Si no tiene perfil
  /// (el backend no crea perfiles al registrarse) o es de otro rol, cierra la sesión.
  Future<void> iniciarSesion(String correo, String contrasena) async {
    await _auth.iniciarSesion(correo, contrasena);
    try {
      final perfil = await ref.read(clienteApiProvider).get('/yo') as Map<String, dynamic>;
      if (perfil['rol'] != 'pasajero') {
        await _auth.cerrarSesion();
        _sincronizar();
        throw const ErrorAuth(
          'Esta aplicación es para pasajeros. Tu cuenta es de gestión: usa el panel web.',
        );
      }
    } on ErrorApi catch (e) {
      await _auth.cerrarSesion();
      _sincronizar();
      throw ErrorAuth(
        e.esNoAutenticado
            ? 'Tu cuenta todavía no tiene perfil de pasajero en BusetasApp.'
            : e.mensaje,
      );
    }
    _sincronizar();
  }

  Future<void> cerrarSesion() async {
    await _auth.cerrarSesion();
    _sincronizar();
  }
}

final sesionProvider = NotifierProvider<SesionNotifier, EstadoSesion>(SesionNotifier.new);
