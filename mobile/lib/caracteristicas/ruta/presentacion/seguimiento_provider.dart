import 'dart:async';

import 'package:flutter/widgets.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../../../nucleo/conexion_ws.dart';
import '../../../nucleo/configuracion.dart';
import '../../../nucleo/errores.dart';
import '../datos/rutas_repositorio.dart';
import '../dominio/seguimiento.dart';
import 'ruta_providers.dart';

class EstadoSeguimiento {
  const EstadoSeguimiento({
    this.busetas = const [],
    this.seguimientoDisponible = false,
    this.unidadesEnServicio,
    this.ultimaActualizacion,
    this.segundosSinDatos = 0,
    this.desactualizado = false,
    this.estadoWs = EstadoWs.conectando,
    this.cargando = true,
    this.error,
  });

  final List<BusetaEnVivo> busetas;
  final bool seguimientoDisponible;

  /// `null` hasta la primera respuesta.
  final int? unidadesEnServicio;
  final DateTime? ultimaActualizacion;
  final int segundosSinDatos;

  /// Pasaron más de 3 intervalos sin datos (CT-08).
  final bool desactualizado;
  final EstadoWs estadoWs;
  final bool cargando;
  final ErrorApi? error;

  bool get tieneDatos => unidadesEnServicio != null;

  EstadoSeguimiento copiar({
    List<BusetaEnVivo>? busetas,
    bool? seguimientoDisponible,
    int? unidadesEnServicio,
    DateTime? ultimaActualizacion,
    int? segundosSinDatos,
    bool? desactualizado,
    EstadoWs? estadoWs,
    bool? cargando,
    ErrorApi? error,
    bool limpiarError = false,
  }) =>
      EstadoSeguimiento(
        busetas: busetas ?? this.busetas,
        seguimientoDisponible: seguimientoDisponible ?? this.seguimientoDisponible,
        unidadesEnServicio: unidadesEnServicio ?? this.unidadesEnServicio,
        ultimaActualizacion: ultimaActualizacion ?? this.ultimaActualizacion,
        segundosSinDatos: segundosSinDatos ?? this.segundosSinDatos,
        desactualizado: desactualizado ?? this.desactualizado,
        estadoWs: estadoWs ?? this.estadoWs,
        cargando: cargando ?? this.cargando,
        error: limpiarError ? null : (error ?? this.error),
      );
}

/// Busetas de una ruta en tiempo real: WebSocket `/ws/rutas/{id}` con reconexión y,
/// mientras no hay conexión, consulta REST cada `intervalo_refresco_cliente_s`.
/// Al dejar de escucharlo (salir de la pantalla) cierra el socket y los temporizadores.
class SeguimientoNotifier extends Notifier<EstadoSeguimiento> with WidgetsBindingObserver {
  SeguimientoNotifier(this.rutaId);

  final String rutaId;

  // Sin `final`: `build` se vuelve a ejecutar si el pasajero cambia el servidor en Ajustes.
  late ConexionWs _ws;
  late TiemposTiempoReal _tiempos;
  Timer? _sondeo;
  Timer? _reloj;
  DateTime? _ultima;
  int _pulsos = 0;
  bool _cerrado = false;

  @override
  EstadoSeguimiento build() {
    _cerrado = false;
    _tiempos = ref.read(tiemposTiempoRealProvider);
    final servidor = ref.watch(servidorProvider);
    _ws = ConexionWs(
      construirUrl: () => urlWebSocket(servidor, '/ws/rutas/$rutaId'),
      fabrica: ref.read(fabricaCanalProvider),
      alMensaje: _alMensaje,
      alCambiarEstado: _alEstadoWs,
      tiempos: _tiempos,
    );
    WidgetsBinding.instance.addObserver(this);
    ref.onDispose(() {
      _cerrado = true;
      WidgetsBinding.instance.removeObserver(this);
      _ws.cerrar();
      _sondeo?.cancel();
      _reloj?.cancel();
    });

    _pulsos = 0;
    _ultima = null;
    _iniciarTemporizadores();
    // Los avisos de la conexión escriben `state`, que aún no existe mientras `build`
    // no termina: se arranca en el siguiente microtask.
    scheduleMicrotask(() {
      if (_cerrado) return;
      _ws.iniciar();
      unawaited(_cargarRest());
    });
    return const EstadoSeguimiento();
  }

  void _iniciarTemporizadores() {
    _sondeo = Timer.periodic(_tiempos.intervaloRefresco, (_) {
      _pulsos++;
      final sinSocket = state.estadoWs != EstadoWs.conectado;
      // Con socket, REST solo concilia de vez en cuando (busetas que terminaron su turno).
      if (sinSocket || _pulsos % 6 == 0) unawaited(_cargarRest());
    });
    const segundo = Duration(seconds: 1);
    final periodo = _tiempos.intervaloRefresco < segundo ? _tiempos.intervaloRefresco : segundo;
    _reloj = Timer.periodic(periodo, (_) => _revisarDesactualizado());
  }

  void _revisarDesactualizado() {
    final ultima = _ultima;
    if (_cerrado || ultima == null) return;
    final sin = DateTime.now().difference(ultima);
    final hayQueSeguir = state.busetas.isNotEmpty || state.seguimientoDisponible;
    final desactualizado = hayQueSeguir && sin > _tiempos.intervaloRefresco * 3;
    if (state.segundosSinDatos != sin.inSeconds || state.desactualizado != desactualizado) {
      state = state.copiar(segundosSinDatos: sin.inSeconds, desactualizado: desactualizado);
    }
  }

  Future<void> _cargarRest() async {
    try {
      final datos = await ref.read(rutasRepositorioProvider).busetas(rutaId);
      if (_cerrado) return;
      _ultima = DateTime.now();
      state = state.copiar(
        busetas: datos.busetas,
        seguimientoDisponible: datos.seguimientoDisponible,
        unidadesEnServicio: datos.unidadesEnServicio,
        ultimaActualizacion: _ultima,
        segundosSinDatos: 0,
        desactualizado: false,
        cargando: false,
        limpiarError: true,
      );
    } on ErrorApi catch (e) {
      if (_cerrado) return;
      state = state.copiar(cargando: false, error: e);
    }
  }

  void _alEstadoWs(EstadoWs estado) {
    if (_cerrado) return;
    state = state.copiar(estadoWs: estado);
  }

  void _alMensaje(Map<String, dynamic> mensaje) {
    if (_cerrado) return;
    switch (mensaje['tipo']) {
      case 'posiciones':
        final nuevas = ((mensaje['busetas'] as List?) ?? const [])
            .cast<Map<String, dynamic>>()
            .map(BusetaEnVivo.desdeJson);
        // Cada mensaje trae solo las busetas que reportaron en ese ciclo: se mezcla por id.
        final porId = {for (final b in state.busetas) b.busetaId: b};
        for (final b in nuevas) {
          porId[b.busetaId] = b;
        }
        final lista = porId.values.toList()..sort((a, b) => a.numeroLateral.compareTo(b.numeroLateral));
        _ultima = DateTime.now();
        state = state.copiar(
          busetas: lista,
          seguimientoDisponible: lista.isNotEmpty,
          unidadesEnServicio: lista.length > (state.unidadesEnServicio ?? 0)
              ? lista.length
              : (state.unidadesEnServicio ?? lista.length),
          ultimaActualizacion: _ultima,
          segundosSinDatos: 0,
          desactualizado: false,
          cargando: false,
          limpiarError: true,
        );
      case 'senal_perdida':
        final numero = mensaje['numeroLateral'];
        state = state.copiar(busetas: [
          for (final b in state.busetas) b.numeroLateral == numero ? b.conSenalPerdida() : b,
        ]);
      case 'aviso_nuevo':
        ref.invalidate(rutaDetalleProvider(rutaId));
    }
  }

  /// Botón **Actualizar**: consulta REST ya y, si no hay socket, reintenta conectarlo.
  Future<void> actualizar() async {
    if (state.estadoWs != EstadoWs.conectado) _ws.reconectar();
    await _cargarRest();
  }

  @override
  void didChangeAppLifecycleState(AppLifecycleState state) {
    if (_cerrado) return;
    if (state == AppLifecycleState.paused || state == AppLifecycleState.hidden) {
      _ws.cerrar();
    } else if (state == AppLifecycleState.resumed) {
      _ws.iniciar();
      unawaited(_cargarRest());
    }
  }
}

final seguimientoProvider =
    NotifierProvider.autoDispose.family<SeguimientoNotifier, EstadoSeguimiento, String>(
  SeguimientoNotifier.new,
);

/// Estado vacío para pantallas que no están a la vista (sin socket abierto).
const seguimientoEnPausa = EstadoSeguimiento(cargando: false);
