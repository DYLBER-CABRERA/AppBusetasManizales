import 'package:flutter_riverpod/flutter_riverpod.dart';

/// Hora actual del dispositivo; las pruebas la sustituyen para fijar el momento.
final relojProvider = Provider<DateTime Function()>((ref) => DateTime.now);
