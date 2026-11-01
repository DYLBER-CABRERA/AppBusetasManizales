import 'horarios.dart';

enum SituacionServicio { enHorario, aunNoInicia, yaCerro, sinDatos }

class ServicioHoy {
  const ServicioHoy(this.situacion, {this.primeraSalida});

  final SituacionServicio situacion;

  /// Primera salida de hoy (`HH:MM`), para «aún no inicia; sale a las 04:45».
  final String? primeraSalida;

  /// Segunda línea de «No hay busetas en servicio…» cuando la hora está fuera de horario.
  String? get detalle => switch (situacion) {
        SituacionServicio.yaCerro => 'El servicio de esta ruta ya cerró.',
        SituacionServicio.aunNoInicia =>
          'El servicio de esta ruta aún no inicia; sale a las $primeraSalida.',
        _ => null,
      };
}

/// Hora de Bogotá (UTC−5, sin horario de verano) a partir de un instante cualquiera.
DateTime horaBogota(DateTime instante) => instante.toUtc().subtract(const Duration(hours: 5));

int _minutos(String hora) {
  final partes = hora.split(':');
  return int.parse(partes[0]) * 60 + int.parse(partes[1]);
}

/// ¿Está la ruta dentro del horario de hoy? Toma la primera salida más temprana y el
/// cierre (o última salida) más tardío entre las empresas con dato para el día.
ServicioHoy servicioHoy(HorariosRuta horarios, DateTime ahoraBogota) {
  final deHoy = [
    for (final s in horarios.servicios)
      for (final h in s.horarios)
        if (h.tipoDia == horarios.tipoDiaHoy) h,
  ];
  if (deHoy.isEmpty) return const ServicioHoy(SituacionServicio.sinDatos);

  final primera = deHoy.map((h) => h.primeraSalida).reduce((a, b) => _minutos(a) <= _minutos(b) ? a : b);
  final fin = deHoy
      .map((h) => h.cierre ?? h.ultimaSalida)
      .reduce((a, b) => _minutos(a) >= _minutos(b) ? a : b);
  final ahora = ahoraBogota.hour * 60 + ahoraBogota.minute;

  if (ahora < _minutos(primera)) {
    return ServicioHoy(SituacionServicio.aunNoInicia, primeraSalida: primera);
  }
  if (ahora > _minutos(fin)) return ServicioHoy(SituacionServicio.yaCerro, primeraSalida: primera);
  return ServicioHoy(SituacionServicio.enHorario, primeraSalida: primera);
}
