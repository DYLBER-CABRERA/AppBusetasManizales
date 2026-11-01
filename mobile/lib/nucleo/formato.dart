import 'package:intl/intl.dart';

/// «220 m» o «1,2 km» (coma decimal en español, sin guardar nada del usuario).
String formatearDistancia(double metros) {
  if (metros < 1000) return '${metros.round()} m';
  return '${NumberFormat('0.0', 'es').format(metros / 1000)} km';
}
