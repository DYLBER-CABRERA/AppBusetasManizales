import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:url_launcher/url_launcher.dart';

/// Abre [url] fuera de la app (Telegram si está instalada, o el navegador).
/// Devuelve `false` si no hay nada que pueda abrirla; nunca lanza.
typedef AbridorEnlaces = Future<bool> Function(Uri url);

Future<bool> _abrirExterno(Uri url) async {
  try {
    return await launchUrl(url, mode: LaunchMode.externalApplication);
  } catch (_) {
    return false;
  }
}

final abridorEnlacesProvider = Provider<AbridorEnlaces>((ref) => _abrirExterno);
