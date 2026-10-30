/// Horarios y frecuencias por servicio y tipo de día (`/rutas/{id}/horarios` y `/frecuencias`).
library;

enum TipoDia {
  lunVie('lun_vie', 'Lun–vie'),
  sabado('sabado', 'Sábados'),
  domFestivo('dom_festivo', 'Dom/festivos');

  const TipoDia(this.valor, this.etiqueta);

  final String valor;
  final String etiqueta;

  static TipoDia desdeValor(String valor) =>
      TipoDia.values.firstWhere((t) => t.valor == valor, orElse: () => TipoDia.lunVie);
}

/// Deja `HH:MM` aunque el servidor mande segundos (`04:45:00`). `24:00` se respeta.
String hhmm(String hora) => hora.length >= 5 ? hora.substring(0, 5) : hora;

List<Map<String, dynamic>> _lista(Object? valor) =>
    ((valor as List?) ?? const []).cast<Map<String, dynamic>>();

class Horario {
  const Horario({
    required this.tipoDia,
    required this.primeraSalida,
    required this.ultimaSalida,
    this.cierre,
    this.nota,
  });

  factory Horario.desdeJson(Map<String, dynamic> j) => Horario(
        tipoDia: TipoDia.desdeValor(j['tipoDia'] as String),
        primeraSalida: hhmm(j['primeraSalida'] as String),
        ultimaSalida: hhmm(j['ultimaSalida'] as String),
        cierre: j['cierre'] == null ? null : hhmm(j['cierre'] as String),
        nota: j['nota'] as String?,
      );

  final TipoDia tipoDia;
  final String primeraSalida;
  final String ultimaSalida;
  final String? cierre;
  final String? nota;
}

class HorariosDeServicio {
  const HorariosDeServicio({
    required this.servicioId,
    required this.empresaNombre,
    required this.estado,
    required this.horarios,
    required this.tiposDiaPendientes,
    this.codigoPublico,
  });

  factory HorariosDeServicio.desdeJson(Map<String, dynamic> j) => HorariosDeServicio(
        servicioId: j['servicioId'] as String,
        empresaNombre: j['empresaNombre'] as String,
        codigoPublico: j['codigoPublico'] as String?,
        estado: j['estado'] as String,
        horarios: _lista(j['horarios']).map(Horario.desdeJson).toList(),
        tiposDiaPendientes: ((j['tiposDiaPendientes'] as List?) ?? const [])
            .map((t) => TipoDia.desdeValor(t as String))
            .toList(),
      );

  final String servicioId;
  final String empresaNombre;
  final String? codigoPublico;

  /// `completo` | `parcial` | `pendiente_actualizacion`.
  final String estado;
  final List<Horario> horarios;
  final List<TipoDia> tiposDiaPendientes;

  String get titulo => '$empresaNombre · ${codigoPublico ?? 'sin código'}';

  /// Una fila por tipo de día, en orden fijo; `null` = información pendiente.
  List<(TipoDia, Horario?)> get filas => [
        for (final tipo in TipoDia.values)
          (tipo, horarios.where((h) => h.tipoDia == tipo).firstOrNull),
      ];
}

class HorariosRuta {
  const HorariosRuta({required this.tipoDiaHoy, required this.servicios});

  factory HorariosRuta.desdeJson(Map<String, dynamic> j) => HorariosRuta(
        tipoDiaHoy: TipoDia.desdeValor(j['tipoDiaHoy'] as String),
        servicios: _lista(j['servicios']).map(HorariosDeServicio.desdeJson).toList(),
      );

  final TipoDia tipoDiaHoy;
  final List<HorariosDeServicio> servicios;
}

class Frecuencia {
  const Frecuencia({
    required this.tipoDia,
    required this.franjaInicio,
    required this.franjaFin,
    required this.minutosMin,
    required this.minutosMax,
    this.nota,
  });

  factory Frecuencia.desdeJson(Map<String, dynamic> j) => Frecuencia(
        tipoDia: TipoDia.desdeValor(j['tipoDia'] as String),
        franjaInicio: hhmm(j['franjaInicio'] as String),
        franjaFin: hhmm(j['franjaFin'] as String),
        minutosMin: j['minutosMin'] as int,
        minutosMax: j['minutosMax'] as int,
        nota: j['nota'] as String?,
      );

  final TipoDia tipoDia;
  final String franjaInicio;
  final String franjaFin;
  final int minutosMin;
  final int minutosMax;
  final String? nota;

  /// «De 10 a 15 min» o «Cada 8 min» si el rango es un solo valor.
  String get texto =>
      minutosMin == minutosMax ? 'Cada $minutosMin min' : 'De $minutosMin a $minutosMax min';
}

class FrecuenciasDeServicio {
  const FrecuenciasDeServicio({
    required this.servicioId,
    required this.empresaNombre,
    required this.frecuencias,
  });

  factory FrecuenciasDeServicio.desdeJson(Map<String, dynamic> j) => FrecuenciasDeServicio(
        servicioId: j['servicioId'] as String,
        empresaNombre: j['empresaNombre'] as String,
        frecuencias: _lista(j['frecuencias']).map(Frecuencia.desdeJson).toList(),
      );

  final String servicioId;
  final String empresaNombre;
  final List<Frecuencia> frecuencias;

  List<Frecuencia> deTipoDia(TipoDia tipo) =>
      frecuencias.where((f) => f.tipoDia == tipo).toList()
        ..sort((a, b) => a.franjaInicio.compareTo(b.franjaInicio));
}

class FrecuenciasRuta {
  const FrecuenciasRuta({required this.servicios});

  factory FrecuenciasRuta.desdeJson(Map<String, dynamic> j) => FrecuenciasRuta(
        servicios: _lista(j['servicios']).map(FrecuenciasDeServicio.desdeJson).toList(),
      );

  final List<FrecuenciasDeServicio> servicios;
}
