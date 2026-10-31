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

/// Datos del perfil de pasajero (`POST /yo`).
class DatosPerfil {
  const DatosPerfil({required this.nombre, required this.apellido, required this.celular});

  final String nombre;
  final String apellido;
  final String celular;

  Map<String, String> aJson() => {'nombre': nombre, 'apellido': apellido, 'celular': celular};
}

/// La cuenta existe en Supabase Auth pero no tiene perfil: faltan los datos para crearlo.
class ErrorPerfilPendiente extends ErrorAuth {
  const ErrorPerfilPendiente()
      : super('Tu cuenta aún no tiene los datos del perfil. Complétalos para continuar.');
}

/// Datos del perfil rechazados por el backend (400), por campo.
class ErrorPerfilInvalido extends ErrorAuth {
  const ErrorPerfilInvalido(super.mensaje, this.campos);

  /// Clave: `nombre`, `apellido` o `celular`.
  final Map<String, String> campos;
}

/// Sesión del pasajero (BR-02: solo se exige para Guardados y alertas).
class SesionNotifier extends Notifier<EstadoSesion> {
  StreamSubscription<void>? _suscripcion;

  /// Hay sesión en Supabase pero todavía falta el perfil: la app no la trata como activa.
  bool _perfilPendiente = false;

  PuertoAuth get _auth => ref.read(authProvider);

  bool get perfilPendiente => _perfilPendiente;

  @override
  EstadoSesion build() {
    final auth = ref.watch(authProvider);
    _suscripcion = auth.cambios.listen((_) => _sincronizar());
    ref.onDispose(() => _suscripcion?.cancel());
    return _estado(auth);
  }

  EstadoSesion _estado(PuertoAuth auth) => EstadoSesion(
        disponible: auth.disponible,
        correo: auth.token == null || _perfilPendiente ? null : auth.correo,
      );

  void _sincronizar() => state = _estado(_auth);

  /// Entra y deja el perfil listo: comprueba con `GET /yo` que la cuenta sea de pasajero.
  /// Si la cuenta se registró pero nunca creó su perfil (`401`), lanza [ErrorPerfilPendiente]
  /// y conserva la sesión para que [completarPerfil] pueda terminar el registro.
  Future<void> iniciarSesion(String correo, String contrasena) async {
    _perfilPendiente = true;
    try {
      await _auth.iniciarSesion(correo, contrasena);
    } catch (_) {
      _perfilPendiente = false;
      rethrow;
    }
    await _confirmarPerfil(null);
  }

  /// Crea la cuenta en Supabase Auth y, enseguida, el perfil con `POST /yo`. Si el correo
  /// ya tenía cuenta se intenta entrar con esa contraseña, de modo que una cuenta que no
  /// terminó el registro pueda completarlo (el `POST /yo` no duplica ni sobrescribe).
  Future<void> registrar(String correo, String contrasena, DatosPerfil datos) async {
    _perfilPendiente = true;
    try {
      try {
        await _auth.registrar(correo, contrasena);
      } on ErrorCuentaExistente {
        try {
          await _auth.iniciarSesion(correo, contrasena);
        } on ErrorAuth {
          throw const ErrorAuth(
            'Ya existe una cuenta con ese correo. Entra con tu contraseña o usa otro correo.',
          );
        }
      }
    } catch (_) {
      _perfilPendiente = false;
      rethrow;
    }
    await _confirmarPerfil(datos);
  }

  /// Termina el registro de una cuenta que ya está dentro de Supabase pero sin perfil.
  Future<void> completarPerfil(DatosPerfil datos) => _confirmarPerfil(datos);

  /// Descarta una sesión a medias (el pasajero cerró la hoja sin completar el perfil).
  Future<void> cancelarPendiente() async {
    if (!_perfilPendiente) return;
    await _auth.cerrarSesion();
    _perfilPendiente = false;
    _sincronizar();
  }

  Future<void> _confirmarPerfil(DatosPerfil? datos) async {
    final api = ref.read(clienteApiProvider);
    try {
      final Object? respuesta;
      if (datos != null) {
        respuesta = await api.post('/yo', cuerpo: datos.aJson());
      } else {
        respuesta = await api.get('/yo');
      }
      final perfil = respuesta as Map<String, dynamic>;
      if (perfil['rol'] != 'pasajero') {
        await _descartar();
        throw const ErrorAuth(
          'Esta aplicación es para pasajeros. Tu cuenta es de gestión: usa el panel web.',
        );
      }
      _perfilPendiente = false;
      _sincronizar();
    } on ErrorApi catch (e) {
      if (datos == null && e.esNoAutenticado) throw const ErrorPerfilPendiente();
      if (e.esSinConexion) {
        // La cuenta ya existe: se conserva la sesión a medias para reintentar sin recrearla.
        throw ErrorAuth(e.mensaje);
      }
      if (e.codigo == 'VALIDACION') throw _perfilInvalido(e);
      if (e.codigo == 'CONFLICTO_NEGOCIO' || e.estado == 409) {
        await _descartar();
        throw const ErrorAuth(
          'Ese correo ya pertenece a otro perfil. Inicia sesión con esa cuenta o usa otro correo.',
        );
      }
      if (e.esNoAutenticado) {
        await _descartar();
        throw const ErrorAuth('No pudimos validar tu sesión. Inicia sesión de nuevo.');
      }
      throw ErrorAuth(e.mensaje);
    }
  }

  Future<void> _descartar() async {
    await _auth.cerrarSesion();
    _perfilPendiente = false;
    _sincronizar();
  }

  ErrorPerfilInvalido _perfilInvalido(ErrorApi e) {
    final campos = <String, String>{};
    final detalles = e.detalles;
    if (detalles is List) {
      for (final d in detalles) {
        if (d is Map && d['campo'] != null) {
          campos[d['campo'].toString().split('.').last] = (d['motivo'] ?? 'Dato no válido.').toString();
        }
      }
    }
    return ErrorPerfilInvalido(campos.isEmpty ? e.mensaje : 'Revisa los datos marcados.', campos);
  }

  Future<void> cerrarSesion() async {
    await _auth.cerrarSesion();
    _perfilPendiente = false;
    _sincronizar();
  }
}

final sesionProvider = NotifierProvider<SesionNotifier, EstadoSesion>(SesionNotifier.new);
