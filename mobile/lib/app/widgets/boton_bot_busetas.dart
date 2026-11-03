import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../../nucleo/enlaces.dart';

final enlaceBotBusetas = Uri.parse('https://t.me/BusetasAppBot');

/// Botón flotante «botBusetas»: abre la conversación con el bot de Telegram.
class BotonBotBusetas extends ConsumerWidget {
  const BotonBotBusetas({super.key});

  Future<void> _abrir(BuildContext context, WidgetRef ref) async {
    final mensajero = ScaffoldMessenger.of(context);
    final abierto = await ref.read(abridorEnlacesProvider)(enlaceBotBusetas);
    if (!abierto) {
      mensajero
        ..hideCurrentSnackBar()
        ..showSnackBar(const SnackBar(
          content: Text('No pudimos abrir Telegram. Busca @BusetasAppBot en Telegram.'),
        ));
    }
  }

  @override
  Widget build(BuildContext context, WidgetRef ref) => Semantics(
        button: true,
        label: 'botBusetas: abrir el chat de Telegram',
        excludeSemantics: true,
        child: FloatingActionButton(
          heroTag: 'bot_busetas',
          tooltip: 'botBusetas',
          onPressed: () => _abrir(context, ref),
          child: const Icon(Icons.chat_bubble_outline),
        ),
      );
}
