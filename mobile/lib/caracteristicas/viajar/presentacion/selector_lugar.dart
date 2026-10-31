import 'dart:async';

import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:latlong2/latlong.dart';

import '../../../nucleo/errores.dart';
import '../../../nucleo/ubicacion.dart';
import '../../buscar/datos/busqueda_repositorio.dart';
import '../../buscar/dominio/hito.dart';
import '../../buscar/presentacion/buscar_provider.dart';
import '../dominio/viaje.dart';
import 'selector_punto_mapa.dart';

/// Hoja para elegir origen o destino: Mi ubicación, un hito o un punto del mapa.
Future<LugarViaje?> elegirLugar(BuildContext context, {required String titulo}) =>
    showModalBottomSheet<LugarViaje>(
      context: context,
      isScrollControlled: true,
      showDragHandle: true,
      builder: (_) => _HojaLugar(titulo: titulo),
    );

class _HojaLugar extends ConsumerStatefulWidget {
  const _HojaLugar({required this.titulo});

  final String titulo;

  @override
  ConsumerState<_HojaLugar> createState() => _HojaLugarState();
}

class _HojaLugarState extends ConsumerState<_HojaLugar> {
  final _campo = TextEditingController();
  Timer? _espera;
  int _ticket = 0;
  List<Hito>? _hitos;
  bool _buscando = false;
  String? _error;

  @override
  void dispose() {
    _espera?.cancel();
    _campo.dispose();
    super.dispose();
  }

  void _escribir(String texto) {
    _espera?.cancel();
    final limpio = texto.trim();
    if (limpio.isEmpty) {
      _ticket++;
      setState(() {
        _hitos = null;
        _buscando = false;
        _error = null;
      });
      return;
    }
    setState(() => _buscando = true);
    _espera = Timer(const Duration(milliseconds: 350), () => _buscar(limpio));
  }

  Future<void> _buscar(String texto) async {
    final ticket = ++_ticket;
    try {
      final hitos = await ref.read(busquedaRepositorioProvider).hitos(texto);
      if (!mounted || ticket != _ticket) return;
      setState(() {
        _hitos = hitos;
        _buscando = false;
        _error = null;
      });
    } on ErrorApi catch (e) {
      if (!mounted || ticket != _ticket) return;
      setState(() {
        _buscando = false;
        _error = e.mensaje;
      });
    }
  }

  void _elegirHito(Hito h) =>
      Navigator.of(context).pop(LugarViaje.hito(id: h.id, nombre: h.nombre, punto: LatLng(h.lat, h.lng)));

  /// Chip de atajo: busca el hito por su nombre y lo elige.
  Future<void> _atajo(String nombre) async {
    try {
      final hitos = await ref.read(busquedaRepositorioProvider).hitos(nombre);
      if (!mounted) return;
      if (hitos.isEmpty) {
        setState(() => _error = 'No encontramos «$nombre». Prueba con otro lugar.');
        return;
      }
      final exacto = hitos.where((h) => h.nombre.toLowerCase() == nombre.toLowerCase());
      _elegirHito(exacto.isNotEmpty ? exacto.first : hitos.first);
    } on ErrorApi catch (e) {
      if (mounted) setState(() => _error = e.mensaje);
    }
  }

  Future<void> _enMapa() async {
    final punto = await Navigator.of(context).push<LatLng>(
      MaterialPageRoute(builder: (_) => SelectorPuntoMapa(titulo: widget.titulo)),
    );
    if (punto != null && mounted) Navigator.of(context).pop(LugarViaje.enMapa(punto));
  }

  @override
  Widget build(BuildContext context) {
    final texto = Theme.of(context).textTheme;
    final ubicacion = ref.watch(ubicacionProvider);
    final punto = ubicacion.value;
    return Padding(
      padding: EdgeInsets.fromLTRB(16, 0, 16, 16 + MediaQuery.viewInsetsOf(context).bottom),
      child: SingleChildScrollView(
        child: Column(
          mainAxisSize: MainAxisSize.min,
          crossAxisAlignment: CrossAxisAlignment.stretch,
          children: [
            Text(widget.titulo, style: texto.titleLarge),
            const SizedBox(height: 8),
            ListTile(
              contentPadding: EdgeInsets.zero,
              minVerticalPadding: 12,
              leading: const Icon(Icons.my_location),
              title: const Text('Mi ubicación'),
              subtitle: ubicacion.isLoading
                  ? const Text('Buscando tu ubicación…')
                  : punto == null
                      ? const Text('No tenemos tu ubicación. Activa el permiso o elige otro lugar.')
                      : null,
              enabled: punto != null,
              onTap: punto == null ? null : () => Navigator.of(context).pop(LugarViaje.miUbicacion(punto)),
            ),
            ListTile(
              contentPadding: EdgeInsets.zero,
              minVerticalPadding: 12,
              leading: const Icon(Icons.place_outlined),
              title: const Text('Elegir en el mapa'),
              onTap: _enMapa,
            ),
            const SizedBox(height: 8),
            TextField(
              controller: _campo,
              textInputAction: TextInputAction.search,
              decoration: const InputDecoration(
                labelText: 'Barrio o lugar',
                prefixIcon: Icon(Icons.search),
              ),
              onChanged: _escribir,
            ),
            const SizedBox(height: 8),
            Wrap(
              spacing: 8,
              runSpacing: 4,
              children: [
                for (final nombre in hitosAtajo)
                  ActionChip(
                    label: Text(nombre),
                    materialTapTargetSize: MaterialTapTargetSize.padded,
                    onPressed: () => _atajo(nombre),
                  ),
              ],
            ),
            if (_buscando)
              const Padding(
                padding: EdgeInsets.all(16),
                child: Center(child: CircularProgressIndicator()),
              ),
            if (_error != null)
              Padding(
                padding: const EdgeInsets.only(top: 12),
                child: Semantics(
                  liveRegion: true,
                  child: Text(_error!, style: TextStyle(color: Theme.of(context).colorScheme.error)),
                ),
              ),
            if (!_buscando && _hitos != null && _hitos!.isEmpty)
              Padding(
                padding: const EdgeInsets.only(top: 12),
                child: Text(
                  'Sin resultados para «${_campo.text.trim()}». Prueba con un hito como Catedral.',
                ),
              ),
            if (!_buscando && _hitos != null)
              for (final h in _hitos!)
                ListTile(
                  contentPadding: EdgeInsets.zero,
                  minVerticalPadding: 12,
                  leading: const Icon(Icons.location_on_outlined),
                  title: Text(h.nombre),
                  onTap: () => _elegirHito(h),
                ),
          ],
        ),
      ),
    );
  }
}
