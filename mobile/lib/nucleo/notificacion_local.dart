import 'package:flutter_local_notifications/flutter_local_notifications.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

/// Aviso del sistema (bandeja de Android) para alertas de llegada y desvío. Solo con
/// la app abierta o en segundo plano reciente: no hay push remoto (D-P09).
abstract class PuertoNotificacionLocal {
  Future<void> pedirPermiso();
  Future<void> mostrar({required int id, required String titulo, required String cuerpo});
}

class NotificacionLocalNula implements PuertoNotificacionLocal {
  @override
  Future<void> pedirPermiso() async {}

  @override
  Future<void> mostrar({required int id, required String titulo, required String cuerpo}) async {}
}

class NotificacionLocalReal implements PuertoNotificacionLocal {
  NotificacionLocalReal._(this._plugin);

  final FlutterLocalNotificationsPlugin _plugin;

  static const _canal = AndroidNotificationDetails(
    'alertas_llegada',
    'Alertas de llegada',
    channelDescription: 'Avisos cuando la buseta está cerca o se desvía del recorrido.',
    importance: Importance.high,
    priority: Priority.high,
  );

  static Future<NotificacionLocalReal> inicializar() async {
    final plugin = FlutterLocalNotificationsPlugin();
    await plugin.initialize(
      settings: const InitializationSettings(
        android: AndroidInitializationSettings('@mipmap/ic_launcher'),
      ),
    );
    return NotificacionLocalReal._(plugin);
  }

  @override
  Future<void> pedirPermiso() async {
    await _plugin
        .resolvePlatformSpecificImplementation<AndroidFlutterLocalNotificationsPlugin>()
        ?.requestNotificationsPermission();
  }

  @override
  Future<void> mostrar({required int id, required String titulo, required String cuerpo}) =>
      _plugin.show(
        id: id,
        title: titulo,
        body: cuerpo,
        notificationDetails: const NotificationDetails(android: _canal),
      );
}

/// En `main` se sustituye por la instancia ya inicializada.
final notificacionLocalProvider =
    Provider<PuertoNotificacionLocal>((ref) => NotificacionLocalNula());
