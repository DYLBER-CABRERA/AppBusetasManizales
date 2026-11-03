import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_test/flutter_test.dart';

import 'package:busetas_app/app/widgets/boton_bot_busetas.dart';
import 'package:busetas_app/nucleo/enlaces.dart';

Future<void> _montar(WidgetTester tester, AbridorEnlaces abridor) => tester.pumpWidget(ProviderScope(
      overrides: [abridorEnlacesProvider.overrideWithValue(abridor)],
      child: const MaterialApp(
        home: Scaffold(floatingActionButton: BotonBotBusetas()),
      ),
    ));

void main() {
  testWidgets('tocar botBusetas abre el enlace del bot de Telegram', (tester) async {
    final abiertos = <Uri>[];
    await _montar(tester, (url) async {
      abiertos.add(url);
      return true;
    });

    await tester.tap(find.byType(FloatingActionButton));
    await tester.pumpAndSettle();

    expect(abiertos, [Uri.parse('https://t.me/BusetasAppBot')]);
    expect(find.byType(SnackBar), findsNothing);
  });

  testWidgets('si no se puede abrir el enlace avisa sin fallar', (tester) async {
    await _montar(tester, (_) async => false);

    await tester.tap(find.byType(FloatingActionButton));
    await tester.pumpAndSettle();

    expect(find.textContaining('No pudimos abrir Telegram'), findsOneWidget);
  });
}
