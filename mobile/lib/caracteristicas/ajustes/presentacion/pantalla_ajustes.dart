import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../../../nucleo/configuracion.dart';
import 'probar_conexion_provider.dart';

class PantallaAjustes extends ConsumerStatefulWidget {
  const PantallaAjustes({super.key});

  @override
  ConsumerState<PantallaAjustes> createState() => _PantallaAjustesState();
}

class _PantallaAjustesState extends ConsumerState<PantallaAjustes> {
  late final TextEditingController _controlador;
  String? _errorCampo;

  @override
  void initState() {
    super.initState();
    _controlador = TextEditingController(text: ref.read(servidorProvider));
  }

  @override
  void dispose() {
    _controlador.dispose();
    super.dispose();
  }

  Future<void> _guardar() async {
    final valido = await ref.read(servidorProvider.notifier).guardar(_controlador.text);
    if (!mounted) return;
    if (!valido) {
      setState(() => _errorCampo = 'Escribe una dirección como http://192.168.0.10:8000');
      return;
    }
    setState(() => _errorCampo = null);
    _controlador.text = ref.read(servidorProvider);
    ref.read(probarConexionProvider.notifier).reiniciar();
    ScaffoldMessenger.of(context)
        .showSnackBar(const SnackBar(content: Text('Servidor guardado')));
  }

  Future<void> _restablecer() async {
    await ref.read(servidorProvider.notifier).restablecer();
    if (!mounted) return;
    setState(() => _errorCampo = null);
    _controlador.text = ref.read(servidorProvider);
    ref.read(probarConexionProvider.notifier).reiniciar();
  }

  @override
  Widget build(BuildContext context) {
    final prueba = ref.watch(probarConexionProvider);
    final texto = Theme.of(context).textTheme;
    return Scaffold(
      appBar: AppBar(title: const Text('Ajustes')),
      body: ListView(
        padding: const EdgeInsets.all(16),
        children: [
          Text('Servidor', style: texto.titleMedium),
          const SizedBox(height: 4),
          Text(
            'Dirección del backend en tu red (por ejemplo, el portátil de la demo). '
            'Se aplica sin reinstalar la app.',
            style: texto.bodyMedium,
          ),
          const SizedBox(height: 12),
          TextField(
            controller: _controlador,
            keyboardType: TextInputType.url,
            autocorrect: false,
            decoration: InputDecoration(
              labelText: 'Dirección del servidor',
              hintText: 'http://192.168.0.10:8000',
              errorText: _errorCampo,
            ),
            onSubmitted: (_) => _guardar(),
          ),
          const SizedBox(height: 12),
          Wrap(
            spacing: 8,
            runSpacing: 8,
            children: [
              FilledButton(onPressed: _guardar, child: const Text('Guardar')),
              OutlinedButton(
                onPressed: prueba is PruebaEnCurso
                    ? null
                    : () => ref.read(probarConexionProvider.notifier).probar(),
                child: const Text('Probar conexión'),
              ),
              TextButton(onPressed: _restablecer, child: const Text('Restablecer')),
            ],
          ),
          const SizedBox(height: 12),
          _ResultadoPrueba(estado: prueba),
          const Divider(height: 40),
          Text('Acerca de', style: texto.titleMedium),
          const SizedBox(height: 8),
          const Text('BusetasApp ${Configuracion.versionApp}'),
          const SizedBox(height: 4),
          const Text('Datos de ejemplo: las rutas, los paraderos y las busetas son simulados.'),
          const SizedBox(height: 4),
          const Text('Mapas © OpenStreetMap contributors.'),
        ],
      ),
    );
  }
}

class _ResultadoPrueba extends StatelessWidget {
  const _ResultadoPrueba({required this.estado});

  final EstadoPrueba estado;

  @override
  Widget build(BuildContext context) {
    final esquema = Theme.of(context).colorScheme;
    return switch (estado) {
      PruebaInactiva() => const SizedBox.shrink(),
      PruebaEnCurso() => const Row(children: [
          SizedBox(width: 20, height: 20, child: CircularProgressIndicator(strokeWidth: 2.5)),
          SizedBox(width: 12),
          Text('Probando conexión…'),
        ]),
      PruebaExitosa(:final milisegundos) => Semantics(
          liveRegion: true,
          child: Row(children: [
            Icon(Icons.check_circle, color: esquema.primary),
            const SizedBox(width: 8),
            Expanded(child: Text('Conexión correcta · $milisegundos ms')),
          ]),
        ),
      PruebaFallida(:final mensaje) => Semantics(
          liveRegion: true,
          child: Row(crossAxisAlignment: CrossAxisAlignment.start, children: [
            Icon(Icons.error_outline, color: esquema.error),
            const SizedBox(width: 8),
            Expanded(child: Text(mensaje, style: TextStyle(color: esquema.error))),
          ]),
        ),
    };
  }
}
