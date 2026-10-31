/// Modelos de la planificación según `contrato/openapi.json` (PlanificarEntrada,
/// Lugar, OpcionViaje, RespuestaPlanificacion). Solo rutas directas (D-P07).
library;

import 'package:latlong2/latlong.dart';

import '../../ruta/dominio/ruta.dart';

/// Origen o destino: «Mi ubicación», un hito o un punto tocado en el mapa.
class LugarViaje {
  const LugarViaje._(this.nombre, this.tipo, {this.punto, this.hitoId});

  /// La ubicación del pasajero solo viaja en la consulta puntual; no se guarda.
  const LugarViaje.miUbicacion(LatLng punto) : this._('Mi ubicación', TipoLugar.ubicacion, punto: punto);

  /// [punto] solo sirve para sugerir rutas cercanas; al backend se manda el `hitoId`.
  const LugarViaje.hito({required String id, required String nombre, LatLng? punto})
      : this._(nombre, TipoLugar.hito, hitoId: id, punto: punto);

  const LugarViaje.enMapa(LatLng punto) : this._('Punto en el mapa', TipoLugar.mapa, punto: punto);

  final String nombre;
  final TipoLugar tipo;
  final LatLng? punto;
  final String? hitoId;

  /// `Lugar` del contrato: exactamente una forma, coordenadas o `hitoId`.
  Map<String, Object> aJson() =>
      hitoId != null ? {'hitoId': hitoId!} : {'lat': punto!.latitude, 'lng': punto!.longitude};

  /// Coordenadas del lugar, si se conocen (Mi ubicación, punto del mapa o hito).
  LatLng? get coordenadas => punto;

  /// Dos lugares son «el mismo» si apuntan al mismo hito o al mismo punto.
  bool mismoQue(LugarViaje otro) =>
      hitoId != null || otro.hitoId != null
          ? hitoId == otro.hitoId
          : punto != null && punto == otro.punto;
}

enum TipoLugar { ubicacion, hito, mapa }

class OpcionViaje {
  const OpcionViaje({
    required this.rutaId,
    required this.servicioId,
    required this.paraderoOrigen,
    required this.paraderoDestino,
    required this.caminataMin,
    required this.esperaMin,
    required this.busMin,
    required this.totalMin,
  });

  factory OpcionViaje.desdeJson(Map<String, dynamic> j) => OpcionViaje(
        rutaId: j['rutaId'] as String,
        servicioId: j['servicioId'] as String,
        paraderoOrigen: ParaderoCercano.desdeJson(j['paraderoOrigen'] as Map<String, dynamic>),
        paraderoDestino: ParaderoCercano.desdeJson(j['paraderoDestino'] as Map<String, dynamic>),
        caminataMin: (j['caminataMin'] as num).toDouble(),
        esperaMin: (j['esperaMin'] as num).toDouble(),
        busMin: (j['busMin'] as num).toDouble(),
        totalMin: (j['totalMin'] as num).toDouble(),
      );

  final String rutaId;
  final String servicioId;
  final ParaderoCercano paraderoOrigen;
  final ParaderoCercano paraderoDestino;
  final double caminataMin;
  final double esperaMin;
  final double busMin;
  final double totalMin;
}

class RespuestaPlanificacion {
  const RespuestaPlanificacion({required this.opciones, this.motivo, this.paraderoMasCercano});

  factory RespuestaPlanificacion.desdeJson(Map<String, dynamic> j) => RespuestaPlanificacion(
        opciones: ((j['opciones'] as List?) ?? const [])
            .cast<Map<String, dynamic>>()
            .map(OpcionViaje.desdeJson)
            .toList(),
        motivo: j['motivo'] as String?,
        paraderoMasCercano: j['paraderoMasCercano'] == null
            ? null
            : ParaderoCercano.desdeJson(j['paraderoMasCercano'] as Map<String, dynamic>),
      );

  final List<OpcionViaje> opciones;
  final String? motivo;
  final ParaderoCercano? paraderoMasCercano;
}

/// Una ruta que pasa cerca del origen aunque la planificación no encontró viaje directo,
/// con su paradero más cercano (la planificación va de paradero a paradero).
class RutaCercanaAlOrigen {
  const RutaCercanaAlOrigen({required this.ruta, this.paradero});

  final RutaResumen ruta;
  final ParaderoCercano? paradero;
}

/// «4 min», «1 min»; los minutos del backend llevan un decimal y se muestran enteros
/// (nunca «0 min»: lo mínimo que se promete es 1).
String minutosViaje(double minutos) {
  final n = minutos.round();
  return '${n < 1 ? 1 : n} min';
}
