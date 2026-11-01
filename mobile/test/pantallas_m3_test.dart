import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:intl/date_symbol_data_local.dart';

import 'package:busetas_app/caracteristicas/avisos/presentacion/pantalla_avisos.dart';
import 'package:busetas_app/caracteristicas/guardados/presentacion/pantalla_guardados.dart';

import 'ayudas/api_falsa.dart';
import 'ayudas/auth_falso.dart';
import 'ayudas/canal_falso.dart';
import 'ayudas/datos_ejemplo.dart';
import 'ayudas/montaje.dart';

const _textoSinSesion = 'Inicia sesión para guardar. Con una cuenta guardas rutas y recibes avisos de llegada.';

Map<String, RespuestaFalsa> _fichaYEta() => {
      '/rutas/$idCable': RespuestaFalsa(detalleCable()),
      '/rutas/$idCable/horarios': RespuestaFalsa(horariosCable()),
      '/rutas/$idCable/frecuencias': RespuestaFalsa(frecuenciasCable()),
      '/rutas/$idCable/busetas': RespuestaFalsa(busetasJson([])),
      '/paraderos/p2/eta': RespuestaFalsa(etaJson([resultadoEtaJson()])),
      '/yo': RespuestaFalsa(perfilJson()),
      '/favoritos': const RespuestaFalsa(<Object>[]),
      '/alertas-llegada': const RespuestaFalsa(<Object>[]),
    };

/// Escribe correo y contraseña en la hoja de inicio de sesión y pulsa **Entrar**.
Future<void> _entrar(WidgetTester tester, {String contrasena = 'secreto'}) async {
  await tester.enterText(find.byType(TextField).at(0), 'pasajera@correo.example');
  await tester.enterText(find.byType(TextField).at(1), contrasena);
  await tester.tap(find.widgetWithText(FilledButton, 'Entrar'));
  await tester.pumpAndSettle();
}

void main() {
  setUpAll(() => initializeDateFormatting('es'));

  group('Avisos', () {
    testWidgets('lista avisos con insignia de origen, tipo de cambio y vigencia', (tester) async {
      await montar(
        tester,
        pantalla: () => const PantallaAvisos(),
        respuestas: {
          '/avisos': RespuestaFalsa([
            avisoJson('a1', 'movilidad', 'Cierre por obras en la carrera 23',
                tipoCambio: 'obra', hasta: '2026-11-05T12:00:00-05:00'),
            avisoJson('a2', 'empresa', 'Horario de festivo', empresa: 'Sideral'),
            avisoJson('a3', 'aplicativo', 'Prototipo con datos de ejemplo'),
          ]),
        },
      );
      await tester.pumpAndSettle();

      expect(find.text('Cierre por obras en la carrera 23'), findsOneWidget);
      expect(find.text('Movilidad'), findsOneWidget);
      expect(find.text('Obra'), findsOneWidget);
      expect(find.textContaining('Hasta el 5'), findsOneWidget);
      expect(find.text('Sideral'), findsOneWidget, reason: 'la insignia de empresa lleva su nombre');
      expect(find.text('Aplicación'), findsOneWidget);
    });

    testWidgets('sin avisos explica y ofrece actualizar', (tester) async {
      await montar(
        tester,
        pantalla: () => const PantallaAvisos(),
        respuestas: {'/avisos': const RespuestaFalsa(<Object>[])},
      );
      await tester.pumpAndSettle();

      expect(find.text('No hay avisos vigentes.'), findsOneWidget);
      expect(find.text('Actualizar'), findsOneWidget);
    });

    testWidgets('error de conexión: banner con Reintentar que se recupera', (tester) async {
      final respuestas = {
        '/avisos': errorFalso(503, 'SERVICIO_EXTERNO_NO_DISPONIBLE', 'Base de datos no disponible.'),
      };
      await montar(tester, pantalla: () => const PantallaAvisos(), respuestas: respuestas);
      await tester.pumpAndSettle();
      expect(find.text('Base de datos no disponible.'), findsOneWidget);

      respuestas['/avisos'] = RespuestaFalsa([avisoJson('a1', 'aplicativo', 'Prototipo')]);
      await tester.tap(find.text('Reintentar'));
      await tester.pumpAndSettle();
      expect(find.text('Prototipo'), findsOneWidget);
    });
  });

  group('Sesión y Guardados', () {
    testWidgets('sin sesión muestra el texto del documento de UX y abre la hoja', (tester) async {
      await montar(tester, pantalla: () => const PantallaGuardados(), respuestas: _fichaYEta());
      await tester.pumpAndSettle();

      expect(find.text('Inicia sesión para guardar.'), findsOneWidget);
      expect(find.text('Con una cuenta guardas rutas y recibes avisos de llegada.'), findsOneWidget);

      await tester.tap(find.text('Iniciar sesión'));
      await tester.pumpAndSettle();
      expect(find.text(_textoSinSesion), findsOneWidget);
      expect(find.widgetWithText(FilledButton, 'Entrar'), findsOneWidget);
    });

    testWidgets('la hoja valida campos vacíos sin llamar a la red', (tester) async {
      final auth = AuthFalso();
      await montar(tester, pantalla: () => const PantallaGuardados(), respuestas: _fichaYEta(), auth: auth);
      await tester.pumpAndSettle();
      await tester.tap(find.text('Iniciar sesión'));
      await tester.pumpAndSettle();

      await tester.tap(find.widgetWithText(FilledButton, 'Entrar'));
      await tester.pumpAndSettle();

      expect(find.text('Escribe tu correo.'), findsOneWidget);
      expect(find.text('Escribe tu contraseña.'), findsOneWidget);
      expect(auth.intentos, isEmpty);
    });

    testWidgets('contraseña incorrecta muestra el error y deja la hoja abierta', (tester) async {
      await montar(tester, pantalla: () => const PantallaGuardados(), respuestas: _fichaYEta());
      await tester.pumpAndSettle();
      await tester.tap(find.text('Iniciar sesión'));
      await tester.pumpAndSettle();

      await _entrar(tester, contrasena: 'mala');

      expect(find.text('Correo o contraseña incorrectos.'), findsOneWidget);
      expect(find.widgetWithText(FilledButton, 'Entrar'), findsOneWidget);
    });

    testWidgets('al entrar valida GET /yo, manda el token y muestra la cuenta', (tester) async {
      final adaptador = await montar(
        tester,
        pantalla: () => const PantallaGuardados(),
        respuestas: {
          ..._fichaYEta(),
          '/favoritos': RespuestaFalsa([favoritoJson('f1')]),
          '/alertas-llegada': RespuestaFalsa([alertaJson('al1')]),
        },
      );
      await tester.pumpAndSettle();
      await tester.tap(find.text('Iniciar sesión'));
      await tester.pumpAndSettle();

      await _entrar(tester);

      expect(adaptador.de('GET', '/yo'), isNotEmpty);
      expect(adaptador.de('GET', '/favoritos').first.autorizacion, 'Bearer token-falso');
      expect(find.text('pasajera@correo.example'), findsOneWidget);
      expect(find.text('El Cable'), findsOneWidget);
      expect(find.text('Cerrar sesión'), findsOneWidget);
      expect(find.text('Te avisamos cuando esté a 300 m'), findsOneWidget);
    });

    testWidgets('una cuenta sin perfil pasa a «Completa tu perfil» y conserva la sesión', (tester) async {
      final auth = AuthFalso();
      await montar(
        tester,
        pantalla: () => const PantallaGuardados(),
        respuestas: {
          ..._fichaYEta(),
          '/yo': errorFalso(401, 'NO_AUTENTICADO', 'Inicia sesión para continuar.'),
        },
        auth: auth,
      );
      await tester.pumpAndSettle();
      await tester.tap(find.text('Iniciar sesión'));
      await tester.pumpAndSettle();

      await _entrar(tester);

      expect(find.text('Completa tu perfil'), findsOneWidget);
      expect(find.text('Guardar y continuar'), findsOneWidget);
      expect(auth.token, isNotNull, reason: 'hace falta el token para POST /yo');
    });

    testWidgets('una cuenta de gestión se rechaza: la app es para pasajeros', (tester) async {
      final auth = AuthFalso();
      await montar(
        tester,
        pantalla: () => const PantallaGuardados(),
        respuestas: {..._fichaYEta(), '/yo': RespuestaFalsa(perfilJson(rol: 'jefe_operaciones'))},
        auth: auth,
      );
      await tester.pumpAndSettle();
      await tester.tap(find.text('Iniciar sesión'));
      await tester.pumpAndSettle();

      await _entrar(tester);

      expect(find.textContaining('Esta aplicación es para pasajeros'), findsOneWidget);
      expect(auth.token, isNull);
    });

    testWidgets('sin Supabase configurado la hoja lo explica y la app sigue usable', (tester) async {
      await montar(
        tester,
        pantalla: () => const PantallaGuardados(),
        respuestas: _fichaYEta(),
        auth: AuthFalso(disponible: false),
      );
      await tester.pumpAndSettle();
      await tester.tap(find.text('Iniciar sesión'));
      await tester.pumpAndSettle();

      expect(find.textContaining('no está disponible en esta instalación'), findsOneWidget);
      expect(find.widgetWithText(FilledButton, 'Entrar'), findsNothing);
    });

    testWidgets('con sesión: lista favoritos y alertas y permite quitarlos', (tester) async {
      final respuestas = {
        ..._fichaYEta(),
        '/rutas': RespuestaFalsa([resumenCable]),
        '/favoritos': RespuestaFalsa([
          favoritoJson('f1'),
          favoritoJson('f2', rutaId: 'vieja', nombre: 'Ruta eliminada', disponible: false),
        ]),
        '/alertas-llegada': RespuestaFalsa([alertaJson('al1', estado: 'notificada')]),
        'DELETE /favoritos/f1': const RespuestaFalsa(null, 204),
        'DELETE /alertas-llegada/al1': const RespuestaFalsa(null, 204),
      };
      final adaptador = await montar(
        tester,
        pantalla: () => const PantallaGuardados(),
        respuestas: respuestas,
        auth: AuthFalso.conSesion(),
      );
      await tester.pumpAndSettle();

      expect(find.text('El Cable'), findsOneWidget);
      expect(find.text('Ruta eliminada'), findsOneWidget);
      expect(find.text('Ya no disponible'), findsOneWidget);
      expect(find.text('El Cable · Paradero Carrera 23'), findsOneWidget);
      expect(find.textContaining('Ya te avisamos'), findsOneWidget);

      respuestas['/favoritos'] = RespuestaFalsa([favoritoJson('f2', rutaId: 'vieja', nombre: 'Ruta eliminada', disponible: false)]);
      await tester.tap(find.byTooltip('Quitar de guardados').first);
      await tester.pumpAndSettle();
      expect(adaptador.de('DELETE', '/favoritos/f1'), hasLength(1));
      expect(find.text('El Cable'), findsNothing);
      expect(find.text('Quitado'), findsOneWidget);

      respuestas['/alertas-llegada'] = const RespuestaFalsa(<Object>[]);
      await tester.tap(find.byTooltip('Quitar alerta'));
      await tester.pumpAndSettle();
      expect(adaptador.de('DELETE', '/alertas-llegada/al1'), hasLength(1));
      expect(find.textContaining('Sin alertas activas'), findsOneWidget);
    });

    testWidgets('token rechazado por el backend: pide cerrar sesión', (tester) async {
      final auth = AuthFalso.conSesion();
      await montar(
        tester,
        pantalla: () => const PantallaGuardados(),
        respuestas: {
          ..._fichaYEta(),
          '/favoritos': errorFalso(401, 'NO_AUTENTICADO', 'Inicia sesión para guardar.'),
          '/alertas-llegada': errorFalso(401, 'NO_AUTENTICADO', 'Inicia sesión para guardar.'),
        },
        auth: auth,
      );
      await tester.pumpAndSettle();

      expect(find.text('No pudimos validar tu sesión.'), findsOneWidget);
      await tester.tap(find.widgetWithText(OutlinedButton, 'Cerrar sesión'));
      await tester.pumpAndSettle();
      expect(auth.token, isNull);
      expect(find.text('Inicia sesión para guardar.'), findsOneWidget);
    });
  });

  group('Guardar ruta (ficha)', () {
    testWidgets('sin sesión pide entrar y luego guarda la ruta', (tester) async {
      final adaptador = await montar(
        tester,
        pantalla: () => const SizedBox(),
        inicial: '/ruta/$idCable',
        respuestas: {
          ..._fichaYEta(),
          'POST /favoritos': RespuestaFalsa(favoritoJson('f1')),
        },
      );
      await tester.pumpAndSettle();

      await tester.tap(find.byTooltip('Guardar ruta'));
      await tester.pumpAndSettle();
      expect(find.text(_textoSinSesion), findsOneWidget);

      await _entrar(tester);

      expect(adaptador.de('POST', '/favoritos').single.cuerpo, {'tipo': 'ruta', 'rutaId': idCable});
      expect(find.text('Guardado'), findsOneWidget);
    });

    testWidgets('con la ruta ya guardada el marcador la quita', (tester) async {
      final respuestas = {
        ..._fichaYEta(),
        '/favoritos': RespuestaFalsa([favoritoJson('f1')]),
        'DELETE /favoritos/f1': const RespuestaFalsa(null, 204),
      };
      final adaptador = await montar(
        tester,
        pantalla: () => const SizedBox(),
        inicial: '/ruta/$idCable',
        respuestas: respuestas,
        auth: AuthFalso.conSesion(),
      );
      await tester.pumpAndSettle();

      respuestas['/favoritos'] = const RespuestaFalsa(<Object>[]);
      await tester.tap(find.byTooltip('Quitar de guardados'));
      await tester.pumpAndSettle();

      expect(adaptador.de('DELETE', '/favoritos/f1'), hasLength(1));
      expect(find.byTooltip('Guardar ruta'), findsOneWidget);
    });
  });

  group('Avisarme (ETA)', () {
    const eta = '/ruta/$idCable/paradero/p2';

    testWidgets('sin sesión pide entrar y luego crea la alerta a 300 m', (tester) async {
      final respuestas = {
        ..._fichaYEta(),
        'POST /alertas-llegada': RespuestaFalsa(alertaJson('al1')),
      };
      final adaptador = await montar(
        tester,
        pantalla: () => const SizedBox(),
        inicial: eta,
        respuestas: respuestas,
      );
      await tester.pumpAndSettle();
      expect(find.text('Avisarme cuando esté a 300 m'), findsOneWidget);

      await tester.tap(find.text('Avisarme cuando esté a 300 m'));
      await tester.pumpAndSettle();
      expect(find.text(_textoSinSesion), findsOneWidget);

      respuestas['/alertas-llegada'] = RespuestaFalsa([alertaJson('al1')]);
      await _entrar(tester);

      expect(adaptador.de('POST', '/alertas-llegada').single.cuerpo, {'rutaId': idCable, 'paraderoId': 'p2'});
      expect(find.text('Alerta activada'), findsOneWidget);
      expect(find.text('Alerta activa'), findsOneWidget);
      expect(find.text('Quitar alerta'), findsOneWidget);
    });

    testWidgets('alerta repetida (409): avisa que ya existe', (tester) async {
      await montar(
        tester,
        pantalla: () => const SizedBox(),
        inicial: eta,
        respuestas: {
          ..._fichaYEta(),
          'POST /alertas-llegada': errorFalso(409, 'CONFLICTO_NEGOCIO', 'Ya existe una alerta.'),
        },
        auth: AuthFalso.conSesion(),
      );
      await tester.pumpAndSettle();

      await tester.tap(find.text('Avisarme cuando esté a 300 m'));
      await tester.pumpAndSettle();

      expect(find.text('Ya tenías una alerta activa para este paradero.'), findsOneWidget);
    });

    testWidgets('con alerta activa se puede quitar', (tester) async {
      final respuestas = {
        ..._fichaYEta(),
        '/alertas-llegada': RespuestaFalsa([alertaJson('al1')]),
        'DELETE /alertas-llegada/al1': const RespuestaFalsa(null, 204),
      };
      final adaptador = await montar(
        tester,
        pantalla: () => const SizedBox(),
        inicial: eta,
        respuestas: respuestas,
        auth: AuthFalso.conSesion(),
      );
      await tester.pumpAndSettle();
      expect(find.text('Alerta activa'), findsOneWidget);
      expect(find.text('Te avisamos cuando la buseta esté a 300 m.'), findsOneWidget);

      respuestas['/alertas-llegada'] = const RespuestaFalsa(<Object>[]);
      await tester.tap(find.text('Quitar alerta'));
      await tester.pumpAndSettle();

      expect(adaptador.de('DELETE', '/alertas-llegada/al1'), hasLength(1));
      expect(find.text('Avisarme cuando esté a 300 m'), findsOneWidget);
    });
  });

  group('Notificaciones de llegada', () {
    testWidgets('con sesión escucha /ws/notificaciones y muestra banner y aviso del sistema', (tester) async {
      final canal = CanalFalso();
      final fabrica = FabricaCanalesFalsa([canal]);
      final locales = NotificacionLocalFalsa();
      await montar(
        tester,
        pantalla: () => const Text('contenido'),
        respuestas: _fichaYEta(),
        auth: AuthFalso.conSesion(),
        fabrica: fabrica,
        locales: locales,
      );
      await tester.pump();
      await tester.pump(const Duration(milliseconds: 50));

      expect(fabrica.urls.single.path, '/ws/notificaciones');
      expect(fabrica.urls.single.queryParameters['token'], 'token-falso');
      expect(locales.permisosPedidos, 1);

      canal.servidorEnvia({
        'tipo': 'alerta_llegada',
        'alertaId': 'al1',
        'rutaId': idCable,
        'paraderoId': 'p2',
        'distanciaM': 300,
        'mensaje': 'La buseta 1544 está a 300 m de tu paradero.',
      });
      await tester.pump();
      await tester.pump();

      expect(find.text('Tu buseta está cerca'), findsOneWidget);
      expect(find.text('La buseta 1544 está a 300 m de tu paradero.'), findsOneWidget);
      expect(locales.mostradas.single.cuerpo, 'La buseta 1544 está a 300 m de tu paradero.');

      await tester.tap(find.text('Cerrar'));
      await tester.pump();
      expect(find.text('Tu buseta está cerca'), findsNothing);
    });

    testWidgets('el desvío se muestra una vez con el texto del servidor', (tester) async {
      final canal = CanalFalso();
      final locales = NotificacionLocalFalsa();
      await montar(
        tester,
        pantalla: () => const Text('contenido'),
        respuestas: _fichaYEta(),
        auth: AuthFalso.conSesion(),
        fabrica: FabricaCanalesFalsa([canal]),
        locales: locales,
      );
      await tester.pump();
      await tester.pump(const Duration(milliseconds: 50));

      canal.servidorEnvia({
        'tipo': 'alerta_desvio',
        'alertaId': 'al1',
        'rutaId': idCable,
        'paraderoId': 'p2',
        'busetaNumero': '1544',
        'mensaje': 'La buseta 1544 se desvió de su recorrido. Tu llegada puede cambiar.',
      });
      await tester.pump();
      await tester.pump();

      expect(find.text('La buseta se desvió'), findsOneWidget);
      expect(find.text('La buseta 1544 se desvió de su recorrido. Tu llegada puede cambiar.'), findsOneWidget);
      expect(locales.mostradas, hasLength(1));
    });

    testWidgets('el banner se oculta solo a los 8 segundos', (tester) async {
      final canal = CanalFalso();
      await montar(
        tester,
        pantalla: () => const Text('contenido'),
        respuestas: _fichaYEta(),
        auth: AuthFalso.conSesion(),
        fabrica: FabricaCanalesFalsa([canal]),
      );
      await tester.pump();
      await tester.pump(const Duration(milliseconds: 50));

      canal.servidorEnvia({'tipo': 'alerta_llegada', 'mensaje': 'La buseta 1544 está a 300 m de tu paradero.'});
      await tester.pump();
      await tester.pump();
      expect(find.text('Tu buseta está cerca'), findsOneWidget);

      await tester.pump(const Duration(seconds: 9));
      expect(find.text('Tu buseta está cerca'), findsNothing);
    });

    testWidgets('sin sesión no se abre ningún socket de notificaciones', (tester) async {
      final fabrica = FabricaCanalesFalsa();
      await montar(
        tester,
        pantalla: () => const Text('contenido'),
        respuestas: _fichaYEta(),
        fabrica: fabrica,
      );
      await tester.pump();
      await tester.pump(const Duration(milliseconds: 50));

      expect(fabrica.urls, isEmpty);
    });

    testWidgets('al cerrar sesión se cierra el socket', (tester) async {
      final canal = CanalFalso();
      final auth = AuthFalso.conSesion();
      await montar(
        tester,
        pantalla: () => const PantallaGuardados(),
        respuestas: _fichaYEta(),
        auth: auth,
        fabrica: FabricaCanalesFalsa([canal]),
      );
      await tester.pumpAndSettle();

      await tester.tap(find.text('Cerrar sesión'));
      await tester.pumpAndSettle();

      expect(canal.cerrado, isTrue);
    });
  });
}
