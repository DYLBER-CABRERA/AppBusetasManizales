import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:latlong2/latlong.dart';
import 'package:shared_preferences/shared_preferences.dart';

import 'package:busetas_app/caracteristicas/eta/dominio/eta.dart';
import 'package:busetas_app/caracteristicas/ruta/dominio/horarios.dart';
import 'package:busetas_app/caracteristicas/ruta/dominio/interpolacion.dart';
import 'package:busetas_app/caracteristicas/ruta/dominio/servicio_hoy.dart';
import 'package:busetas_app/caracteristicas/ruta/presentacion/seguimiento_provider.dart';
import 'package:busetas_app/nucleo/cliente_api.dart';
import 'package:busetas_app/nucleo/configuracion.dart';
import 'package:busetas_app/nucleo/conexion_ws.dart';

import 'ayudas/api_falsa.dart';
import 'ayudas/canal_falso.dart';
import 'ayudas/datos_ejemplo.dart';

const _rapidos = TiemposTiempoReal(
  intervaloRefresco: Duration(milliseconds: 60),
  esperasReconexion: [Duration(milliseconds: 20), Duration(milliseconds: 40)],
  latido: Duration(hours: 1),
);

Future<void> esperarHasta(bool Function() condicion, {int maxMs = 3000}) async {
  final limite = DateTime.now().add(Duration(milliseconds: maxMs));
  while (!condicion()) {
    if (DateTime.now().isAfter(limite)) fail('La condición no se cumplió en ${maxMs}ms');
    await Future<void>.delayed(const Duration(milliseconds: 10));
  }
}

void main() {
  TestWidgetsFlutterBinding.ensureInitialized();

  group('urlWebSocket', () {
    test('http → ws con puerto y sin el prefijo /api/v1', () {
      expect(
        urlWebSocket('http://192.168.0.10:8000', '/ws/rutas/abc').toString(),
        'ws://192.168.0.10:8000/ws/rutas/abc',
      );
    });

    test('https → wss', () {
      expect(urlWebSocket('https://demo.example.com', '/ws/rutas/x').toString(),
          'wss://demo.example.com/ws/rutas/x');
    });
  });

  group('ConexionWs', () {
    late List<EstadoWs> estados;
    late List<Map<String, dynamic>> mensajes;

    ConexionWs crear(FabricaCanalesFalsa fabrica) => ConexionWs(
          url: Uri.parse('ws://prueba/ws/rutas/r1'),
          fabrica: fabrica.crear,
          alMensaje: mensajes.add,
          alCambiarEstado: estados.add,
          tiempos: _rapidos,
        );

    setUp(() {
      estados = [];
      mensajes = [];
    });

    test('conecta, entrega los JSON e ignora pong y texto no JSON', () async {
      final canal = CanalFalso();
      final ws = crear(FabricaCanalesFalsa([canal]))..iniciar();
      await esperarHasta(() => estados.contains(EstadoWs.conectado));

      canal.servidorEnvia({'tipo': 'posiciones', 'busetas': <Object>[]});
      canal.servidorEnviaTexto('pong');
      canal.servidorEnviaTexto('esto no es json');
      await esperarHasta(() => mensajes.isNotEmpty);
      await Future<void>.delayed(const Duration(milliseconds: 30));

      expect(mensajes, hasLength(1));
      expect(mensajes.single['tipo'], 'posiciones');
      expect(estados, [EstadoWs.conectando, EstadoWs.conectado]);
      ws.cerrar();
    });

    test('si el servidor corta, reconecta solo', () async {
      final primero = CanalFalso();
      final segundo = CanalFalso();
      final fabrica = FabricaCanalesFalsa([primero, segundo]);
      final ws = crear(fabrica)..iniciar();
      await esperarHasta(() => estados.contains(EstadoWs.conectado));

      primero.servidorCierra();
      await esperarHasta(() => estados.where((e) => e == EstadoWs.conectado).length == 2);

      expect(fabrica.urls, hasLength(2));
      expect(estados, contains(EstadoWs.desconectado));
      segundo.servidorEnvia({'tipo': 'aviso_nuevo', 'avisoId': 'a1'});
      await esperarHasta(() => mensajes.isNotEmpty);
      ws.cerrar();
    });

    test('reintenta con espera creciente hasta lograrlo y no se rinde', () async {
      final fabrica = FabricaCanalesFalsa([CanalFalso(falla: true), CanalFalso(falla: true), CanalFalso()]);
      final ws = crear(fabrica)..iniciar();
      final inicio = DateTime.now();
      await esperarHasta(() => estados.contains(EstadoWs.conectado));

      expect(fabrica.urls, hasLength(3));
      // 20 ms + 40 ms de espera como mínimo entre los tres intentos.
      expect(DateTime.now().difference(inicio).inMilliseconds, greaterThanOrEqualTo(55));
      ws.cerrar();
    });

    test('cerrar() detiene los reintentos y cierra el canal', () async {
      final canal = CanalFalso();
      final fabrica = FabricaCanalesFalsa([canal]);
      final ws = crear(fabrica)..iniciar();
      await esperarHasta(() => estados.contains(EstadoWs.conectado));

      ws.cerrar();
      canal.servidorCierra();
      await Future<void>.delayed(const Duration(milliseconds: 150));

      expect(canal.cerrado, isTrue);
      expect(fabrica.urls, hasLength(1), reason: 'no debe reconectar tras cerrar');
    });
  });

  group('SeguimientoNotifier', () {
    late AdaptadorFalso adaptador;
    late FabricaCanalesFalsa fabrica;
    late ProviderContainer contenedor;

    Future<void> montar(Map<String, RespuestaFalsa> respuestas, FabricaCanalesFalsa f) async {
      SharedPreferences.setMockInitialValues({});
      final preferencias = await SharedPreferences.getInstance();
      adaptador = AdaptadorFalso(respuestas);
      fabrica = f;
      contenedor = ProviderContainer(
        retry: (_, _) => null,
        overrides: [
          preferenciasProvider.overrideWithValue(preferencias),
          clienteApiProvider.overrideWithValue(crearApiFalsa(adaptador)),
          fabricaCanalProvider.overrideWithValue(fabrica.crear),
          tiemposTiempoRealProvider.overrideWithValue(_rapidos),
        ],
      );
      // Mantiene vivo el proveedor autoDispose mientras dura la prueba.
      contenedor.listen(seguimientoProvider('r1'), (_, _) {});
    }

    EstadoSeguimiento estado() => contenedor.read(seguimientoProvider('r1'));

    tearDown(() => contenedor.dispose());

    test('carga inicial por REST y mezcla por id los mensajes del WebSocket', () async {
      final canal = CanalFalso();
      await montar({
        '/rutas/r1/busetas': RespuestaFalsa(busetasJson([
          busetaJson('b1', '1544', lat: 5.0),
          busetaJson('b2', '1520', lat: 5.1),
        ])),
      }, FabricaCanalesFalsa([canal]));

      await esperarHasta(() => estado().tieneDatos && estado().estadoWs == EstadoWs.conectado);
      expect(estado().busetas.map((b) => b.numeroLateral), ['1544', '1520']);
      expect(estado().unidadesEnServicio, 2);

      // El mensaje trae solo b1 (movida) y una buseta nueva b3: b2 se conserva.
      canal.servidorEnvia({
        'tipo': 'posiciones',
        'rutaId': 'r1',
        'calculadoEn': '2026-10-29T10:00:03-05:00',
        'busetas': [busetaJson('b1', '1544', lat: 5.5), busetaJson('b3', '2683', lat: 5.3)],
      });
      await esperarHasta(() => estado().busetas.length == 3);

      final porNumero = {for (final b in estado().busetas) b.numeroLateral: b};
      expect(porNumero['1544']!.lat, 5.5, reason: 'b1 se actualizó');
      expect(porNumero['1520']!.lat, 5.1, reason: 'b2 no estaba en el mensaje y se conserva');
      expect(porNumero['2683'], isNotNull);
      expect(estado().unidadesEnServicio, 3);
      expect(estado().desactualizado, isFalse);
    });

    test('senal_perdida deja la buseta sin señal', () async {
      final canal = CanalFalso();
      await montar({
        '/rutas/r1/busetas': RespuestaFalsa(busetasJson([busetaJson('b1', '1544')])),
      }, FabricaCanalesFalsa([canal]));
      await esperarHasta(() => estado().estadoWs == EstadoWs.conectado && estado().tieneDatos);

      canal.servidorEnvia({'tipo': 'senal_perdida', 'numeroLateral': '1544'});
      await esperarHasta(() => estado().busetas.single.sinSenal);
    });

    test('sin WebSocket consulta REST cada intervalo (respaldo)', () async {
      final respuestas = {
        '/rutas/r1/busetas': RespuestaFalsa(busetasJson([busetaJson('b1', '1544', lat: 5.0)])),
      };
      await montar(respuestas, FabricaCanalesFalsa()); // todos los canales fallan

      await esperarHasta(() => estado().tieneDatos);
      expect(estado().estadoWs, isNot(EstadoWs.conectado));

      respuestas['/rutas/r1/busetas'] =
          RespuestaFalsa(busetasJson([busetaJson('b1', '1544', lat: 5.9)]));
      await esperarHasta(() => estado().busetas.single.lat == 5.9);
      expect(
        adaptador.peticiones.where((u) => u.path.endsWith('/busetas')).length,
        greaterThanOrEqualTo(2),
      );
    });

    test('pasados 3 intervalos sin datos marca desactualizado y se recupera', () async {
      final respuestas = {
        '/rutas/r1/busetas': RespuestaFalsa(busetasJson([busetaJson('b1', '1544')])),
      };
      await montar(respuestas, FabricaCanalesFalsa());
      await esperarHasta(() => estado().tieneDatos);

      respuestas['/rutas/r1/busetas'] =
          errorFalso(503, 'SERVICIO_EXTERNO_NO_DISPONIBLE', 'Base de datos no disponible.');
      await esperarHasta(() => estado().desactualizado);
      expect(estado().error?.mensaje, 'Base de datos no disponible.');
      expect(estado().busetas, hasLength(1), reason: 'se conserva lo cargado');

      respuestas['/rutas/r1/busetas'] = RespuestaFalsa(busetasJson([busetaJson('b1', '1544')]));
      await esperarHasta(() => !estado().desactualizado && estado().error == null);
    });

    test('sin busetas ni seguimiento nunca se marca desactualizado (Serviturismo sin GPS)', () async {
      await montar({
        '/rutas/r1/busetas': RespuestaFalsa(busetasJson([], unidades: 1)),
      }, FabricaCanalesFalsa([CanalFalso()]));
      await esperarHasta(() => estado().tieneDatos);
      await Future<void>.delayed(const Duration(milliseconds: 400));

      expect(estado().desactualizado, isFalse);
      expect(estado().unidadesEnServicio, 1);
      expect(estado().seguimientoDisponible, isFalse);
    });

    test('al dejar de escucharlo se cierra el WebSocket', () async {
      final canal = CanalFalso();
      await montar({
        '/rutas/r1/busetas': RespuestaFalsa(busetasJson([busetaJson('b1', '1544')])),
      }, FabricaCanalesFalsa([canal]));
      await esperarHasta(() => estado().estadoWs == EstadoWs.conectado);

      contenedor.dispose();
      await esperarHasta(() => canal.cerrado);
    });
  });

  group('interpolar', () {
    const a = LatLng(5.0, -75.0);
    const b = LatLng(6.0, -76.0);

    test('extremos y punto medio', () {
      expect(interpolar(a, b, 0), a);
      expect(interpolar(a, b, 1), b);
      final medio = interpolar(a, b, 0.5);
      expect(medio.latitude, closeTo(5.5, 1e-9));
      expect(medio.longitude, closeTo(-75.5, 1e-9));
    });

    test('t fuera de rango se acota', () {
      expect(interpolar(a, b, -3), a);
      expect(interpolar(a, b, 7), b);
    });
  });

  group('servicioHoy', () {
    final horarios = HorariosRuta.desdeJson(horariosCable()); // lun_vie 04:45–21:30
    // `DateTime.utc` + `horaBogota` = hora local de Bogotá.
    DateTime bogota(int h, int m) => horaBogota(DateTime.utc(2026, 10, 29, h + 5, m));

    test('antes de la primera salida: aún no inicia y dice a qué hora sale', () {
      final r = servicioHoy(horarios, bogota(3, 10));
      expect(r.situacion, SituacionServicio.aunNoInicia);
      expect(r.detalle, 'El servicio de esta ruta aún no inicia; sale a las 04:45.');
    });

    test('después del cierre: ya cerró', () {
      final r = servicioHoy(horarios, bogota(22, 0));
      expect(r.situacion, SituacionServicio.yaCerro);
      expect(r.detalle, 'El servicio de esta ruta ya cerró.');
    });

    test('dentro del horario no hay detalle', () {
      final r = servicioHoy(horarios, bogota(12, 0));
      expect(r.situacion, SituacionServicio.enHorario);
      expect(r.detalle, isNull);
    });

    test('sin horario para hoy no se inventa nada', () {
      final soloSabado = HorariosRuta(tipoDiaHoy: TipoDia.sabado, servicios: horarios.servicios);
      expect(servicioHoy(soloSabado, bogota(12, 0)).situacion, SituacionServicio.sinDatos);
    });

    test('usa el cierre y no la última salida cuando existe', () {
      final conCierre = HorariosRuta.desdeJson({
        'tipoDiaHoy': 'lun_vie',
        'servicios': [
          {
            'servicioId': 's',
            'empresaId': 'e',
            'empresaNombre': 'Socobuses',
            'estado': 'completo',
            'horarios': [
              {'tipoDia': 'lun_vie', 'primeraSalida': '05:30', 'ultimaSalida': '22:00', 'cierre': '23:00'},
            ],
            'tiposDiaPendientes': <Object>[],
            'version': 1,
          },
        ],
      });
      expect(servicioHoy(conCierre, bogota(22, 30)).situacion, SituacionServicio.enHorario);
    });

    test('horaBogota resta 5 horas al instante UTC', () {
      final h = horaBogota(DateTime.utc(2026, 10, 30, 4, 21));
      expect((h.hour, h.minute), (23, 21));
    });
  });

  group('ETA', () {
    test('gps: minutos redondeados, buseta y fuente con antigüedad', () {
      final r = ResultadoEta.desdeJson(resultadoEtaJson());
      expect(r.fuente, FuenteEta.gps);
      expect(r.principal, '4 min');
      expect(r.busetaNumeroLateral, '1544');
      expect(r.lineaFuente, 'Fuente: GPS · hace 3 s');
      expect(r.titulo, 'Sideral · 39');
    });

    test('gps con menos de un minuto', () {
      expect(textoMinutos(45), 'Menos de 1 min');
      expect(textoMinutos(60), '1 min');
      expect(textoMinutos(150), '3 min');
    });

    test('horario: «Hasta N min» desde el tope del rango', () {
      final r = ResultadoEta.desdeJson(resultadoEtaJson(
        fuente: 'horario',
        etaSegundos: null,
        maxSegundos: 900,
        mensaje: 'Sin ubicación de busetas.',
      ));
      expect(r.principal, 'Hasta 15 min');
      expect(r.lineaFuente, 'Fuente: horario');
    });

    test('no disponible: sin cifra y con el mensaje del servidor', () {
      final r = ResultadoEta.desdeJson(resultadoEtaJson(
        fuente: 'no_disponible',
        etaSegundos: null,
        mensaje: 'El servicio ya cerró.',
      ));
      expect(r.principal, isNull);
      expect(r.mensaje, 'El servicio ya cerró.');
      expect(r.lineaFuente, 'Fuente: sin datos');
    });

    test('RespuestaEta lee la lista de resultados', () {
      final respuesta = RespuestaEta.desdeJson(etaJson([
        resultadoEtaJson(),
        resultadoEtaJson(fuente: 'no_disponible', etaSegundos: null),
      ]));
      expect(respuesta.resultados, hasLength(2));
      expect(respuesta.rutaId, idCable);
    });
  });
}
