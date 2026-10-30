import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:shared_preferences/shared_preferences.dart';

import 'package:busetas_app/app/app.dart';
import 'package:busetas_app/nucleo/configuracion.dart';

Future<void> _abrirApp(WidgetTester tester) async {
  SharedPreferences.setMockInitialValues({});
  final preferencias = await SharedPreferences.getInstance();
  await tester.pumpWidget(ProviderScope(
    overrides: [preferenciasProvider.overrideWithValue(preferencias)],
    child: const BusetasApp(fuentesWeb: false),
  ));
  await tester.pumpAndSettle();
}

void main() {
  testWidgets('muestra el banner de datos de ejemplo y la barra inferior', (tester) async {
    await _abrirApp(tester);

    expect(find.text(Configuracion.textoBanner), findsOneWidget);
    for (final etiqueta in ['Mapa', 'Buscar', 'Viajar', 'Guardados', 'Avisos']) {
      expect(find.text(etiqueta), findsWidgets);
    }
  });

  testWidgets('Ajustes guarda una dirección válida y rechaza una inválida', (tester) async {
    await _abrirApp(tester);

    await tester.tap(find.byTooltip('Ajustes'));
    await tester.pumpAndSettle();
    expect(find.text('Probar conexión'), findsOneWidget);

    await tester.enterText(find.byType(TextField), '192.168.0.10:8000');
    await tester.tap(find.text('Guardar'));
    await tester.pumpAndSettle();
    final contenedor = ProviderScope.containerOf(tester.element(find.byType(TextField)));
    expect(contenedor.read(servidorProvider), 'http://192.168.0.10:8000');

    await tester.enterText(find.byType(TextField), 'ftp://x');
    await tester.tap(find.text('Guardar'));
    await tester.pumpAndSettle();
    expect(find.textContaining('Escribe una dirección'), findsOneWidget);
    expect(contenedor.read(servidorProvider), 'http://192.168.0.10:8000');
  });
}
