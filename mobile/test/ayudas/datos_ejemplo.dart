/// JSON con la forma de `contrato/openapi.json` (valores de ejemplo, no oficiales).
library;

const idCable = 'ruta-cable';
const idEnea = 'ruta-enea';

Map<String, dynamic> servicio(String empresa, String? codigo, {String id = 's1'}) => {
      'servicioId': id,
      'empresaId': 'e-$empresa',
      'empresaNombre': empresa,
      'codigoPublico': codigo,
    };

Map<String, dynamic> rutaResumen(String id, String nombre, List<Map<String, dynamic>> servicios,
        {double? distanciaM}) =>
    {
      'id': id,
      'nombre': nombre,
      'tipoRecorrido': 'circular',
      'esVariante': false,
      'distanciaM': distanciaM,
      'servicios': servicios,
    };

final resumenCable = rutaResumen(idCable, 'El Cable', [servicio('Sideral', '39')], distanciaM: 220);
final resumenEnea = rutaResumen(
  idEnea,
  'La Enea',
  [servicio('Socobuses', '18', id: 's2'), servicio('Serviturismo', null, id: 's3')],
  distanciaM: 410,
);

Map<String, dynamic> detalleCable() => {
      ...resumenCable,
      'descripcion': 'Recorrido de ejemplo (no oficial).',
      'longitudM': 14424.8,
      'trazado': {
        'type': 'LineString',
        'coordinates': [
          [-75.506, 5.0495],
          [-75.51, 5.06],
          [-75.5173, 5.0674],
        ],
      },
      'paraderos': [
        {'orden': 2, 'paraderoId': 'p2', 'nombre': 'Carrera 23', 'lat': 5.0672, 'lng': -75.5153},
        {'orden': 1, 'paraderoId': 'p1', 'nombre': 'Terminal', 'lat': 5.0494, 'lng': -75.5063},
      ],
      'avisos': [
        {
          'id': 'a1',
          'origen': 'movilidad',
          'titulo': 'Cierre por obras en la carrera 23',
          'cuerpo': 'Desvío temporal.',
          'empresaNombre': null,
        },
      ],
      'version': 1,
    };

Map<String, dynamic> horariosCable() => {
      'tipoDiaHoy': 'lun_vie',
      'servicios': [
        {
          'servicioId': 's1',
          'empresaId': 'e-Sideral',
          'empresaNombre': 'Sideral',
          'codigoPublico': '39',
          'estado': 'parcial',
          'horarios': [
            {
              'tipoDia': 'lun_vie',
              'primeraSalida': '04:45',
              'ultimaSalida': '21:30',
              'cierre': null,
              'nota': null,
            },
            {
              'tipoDia': 'dom_festivo',
              'primeraSalida': '06:00',
              'ultimaSalida': '21:00',
              'cierre': null,
              'nota': null,
            },
          ],
          'tiposDiaPendientes': ['sabado'],
          'version': 1,
        },
      ],
    };

Map<String, dynamic> frecuenciasCable() => {
      'servicios': [
        {
          'servicioId': 's1',
          'empresaId': 'e-Sideral',
          'empresaNombre': 'Sideral',
          'frecuencias': [
            {
              'tipoDia': 'lun_vie',
              'franjaInicio': '04:45',
              'franjaFin': '21:30',
              'minutosMin': 8,
              'minutosMax': 10,
              'nota': null,
            },
          ],
          'version': 1,
        },
      ],
    };

Map<String, dynamic> busetasVacio() => {
      'seguimientoDisponible': false,
      'unidadesEnServicio': 0,
      'calculadoEn': '2026-10-29T10:00:00-05:00',
      'busetas': <Object>[],
    };

Map<String, dynamic> hitoCatedral() => {
      'id': 'h1',
      'nombre': 'Catedral',
      'tipo': 'hito',
      'alias': ['catedral', 'la catedral'],
      'lat': 5.0674,
      'lng': -75.5173,
    };

Map<String, dynamic> busetaJson(
  String id,
  String numero, {
  double lat = 5.06,
  double lng = -75.51,
  String estado = 'activa',
  String empresa = 'Sideral',
  String reportadaEn = '2026-10-29T10:00:00-05:00',
}) =>
    {
      'busetaId': id,
      'numeroLateral': numero,
      'empresa': empresa,
      'servicioId': 's1',
      'estado': estado,
      'lat': lat,
      'lng': lng,
      'velocidadKmh': 33.2,
      'rumbo': 91,
      'reportadaEn': reportadaEn,
      'mensaje': estado == 'sin_senal' ? 'Ubicación no disponible. Última señal hace más de 60 s.' : null,
    };

Map<String, dynamic> busetasJson(List<Map<String, dynamic>> busetas, {int? unidades}) => {
      'seguimientoDisponible': busetas.isNotEmpty,
      'unidadesEnServicio': unidades ?? busetas.length,
      'calculadoEn': '2026-10-29T10:00:00-05:00',
      'busetas': busetas,
    };

Map<String, dynamic> resultadoEtaJson({
  String fuente = 'gps',
  int? etaSegundos = 240,
  int? maxSegundos,
  String? mensaje,
}) =>
    {
      'servicioId': 's1',
      'empresa': 'Sideral',
      'codigoPublico': '39',
      'fuente': fuente,
      'etaSegundos': etaSegundos,
      'rango': maxSegundos == null ? null : {'minSegundos': 0, 'maxSegundos': maxSegundos},
      'busetaNumeroLateral': fuente == 'gps' ? '1544' : null,
      'ultimaSenalHaceS': fuente == 'gps' ? 3 : null,
      'mensaje': mensaje,
    };

Map<String, dynamic> etaJson(List<Map<String, dynamic>> resultados) => {
      'paraderoId': 'p2',
      'rutaId': idCable,
      'calculadoEn': '2026-10-29T10:00:00-05:00',
      'resultados': resultados,
    };

Map<String, dynamic> avisoJson(
  String id,
  String origen,
  String titulo, {
  String? empresa,
  String? tipoCambio,
  String? hasta,
}) =>
    {
      'id': id,
      'origen': origen,
      'titulo': titulo,
      'cuerpo': 'Detalle de $titulo.',
      'desde': '2026-10-29T00:00:00-05:00',
      'hasta': hasta,
      'empresaId': null,
      'empresaNombre': empresa,
      'paraderoIds': <Object>[],
      'rutaIds': <Object>[],
      'tipoCambio': tipoCambio,
    };

Map<String, dynamic> perfilJson({String rol = 'pasajero'}) => {
      'usuarioId': 'u1',
      'correo': 'pasajera@correo.example',
      'rol': rol,
      'empresaId': null,
      'empresaNombre': null,
    };

Map<String, dynamic> favoritoJson(String id, {String? rutaId = idCable, String nombre = 'El Cable', bool disponible = true}) => {
      'id': id,
      'tipo': 'ruta',
      'nombre': nombre,
      'rutaId': rutaId,
      'paraderoId': null,
      'disponible': disponible,
    };

Map<String, dynamic> alertaJson(String id, {String estado = 'activa', String rutaId = idCable, String paraderoId = 'p2'}) => {
      'id': id,
      'rutaId': rutaId,
      'paraderoId': paraderoId,
      'distanciaAvisoM': 300,
      'estado': estado,
      'ultimaNotificacionEn': null,
      'version': 1,
    };
