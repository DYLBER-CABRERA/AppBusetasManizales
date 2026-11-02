import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:shared_preferences/shared_preferences.dart';

/// Valores de compilación (`--dart-define`). La dirección del servidor se puede
/// sobrescribir en Ajustes sin recompilar.
class Configuracion {
  Configuracion._();

  /// 10.0.2.2 es el portátil visto desde el emulador de Android.
  static const apiBaseUrl =
      String.fromEnvironment('API_BASE_URL', defaultValue: 'http://10.0.2.2:8000');
  static const supabaseUrl = String.fromEnvironment('SUPABASE_URL');
  static const supabaseAnonKey = String.fromEnvironment('SUPABASE_ANON_KEY');
  static const mapTileUrl = String.fromEnvironment(
    'MAP_TILE_URL',
    defaultValue: 'https://tile.openstreetmap.org/{z}/{x}/{y}.png',
  );

  static const prefijoApi = '/api/v1';
  static const versionApp = '0.1.0';
  static const textoBanner = 'Datos de ejemplo · no son rutas oficiales';
}

/// Deja la dirección como `http://host:puerto`: agrega el esquema si falta y
/// quita barras finales y el prefijo `/api/v1`. Devuelve `null` si no es válida.
String? normalizarServidor(String entrada) {
  var texto = entrada.trim();
  if (texto.isEmpty) return null;
  if (!texto.contains('://')) texto = 'http://$texto';
  final uri = Uri.tryParse(texto);
  if (uri == null || uri.host.isEmpty) return null;
  if (uri.scheme != 'http' && uri.scheme != 'https') return null;
  final puerto = uri.hasPort ? ':${uri.port}' : '';
  return '${uri.scheme}://${uri.host}$puerto';
}

/// Se sobrescribe en `main` con la instancia ya cargada.
final preferenciasProvider = Provider<SharedPreferences>(
  (ref) => throw UnimplementedError('preferenciasProvider sin inicializar'),
);

const _claveServidor = 'servidor';

class ServidorNotifier extends Notifier<String> {
  @override
  String build() {
    final guardado = ref.watch(preferenciasProvider).getString(_claveServidor);
    return (guardado != null ? normalizarServidor(guardado) : null) ??
        normalizarServidor(Configuracion.apiBaseUrl) ??
        Configuracion.apiBaseUrl;
  }

  /// Devuelve `false` si la dirección no es válida (no cambia nada).
  Future<bool> guardar(String entrada) async {
    final normalizada = normalizarServidor(entrada);
    if (normalizada == null) return false;
    await ref.read(preferenciasProvider).setString(_claveServidor, normalizada);
    state = normalizada;
    return true;
  }

  Future<void> restablecer() async {
    await ref.read(preferenciasProvider).remove(_claveServidor);
    state = normalizarServidor(Configuracion.apiBaseUrl) ?? Configuracion.apiBaseUrl;
  }
}

final servidorProvider = NotifierProvider<ServidorNotifier, String>(ServidorNotifier.new);
