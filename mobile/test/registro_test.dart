import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:intl/date_symbol_data_local.dart';

import 'package:busetas_app/caracteristicas/guardados/presentacion/pantalla_guardados.dart';

import 'ayudas/api_falsa.dart';
import 'ayudas/auth_falso.dart';
import 'ayudas/datos_ejemplo.dart';
import 'ayudas/montaje.dart';

Map<String, RespuestaFalsa> _base() => {
      '/favoritos': const RespuestaFalsa(<Object>[]),
      '/alertas-llegada': const RespuestaFalsa(<Object>[]),
    };

Map<String, dynamic> _perfilCompleto() => {
      ...perfilJson(),
      'nombre': 'Ana María',
      'apellido': 'Pérez',
      'celular': '3001234567',
    };

Future<void> _abrirCrearCuenta(WidgetTester tester) async {
  await tester.tap(find.text('Iniciar sesión'));
  await tester.pumpAndSettle();
  await tester.tap(find.text('No tengo cuenta · Crear cuenta'));
  await tester.pumpAndSettle();
}

Future<void> _llenar(
  WidgetTester tester, {
  String celular = '+57 300-123 4567',
  String contrasena = 'secreto1',
  String confirmacion = 'secreto1',
  String correo = 'ana@correo.example',
}) async {
  final campos = find.byType(TextField);
  await tester.enterText(campos.at(0), '  Ana María ');
  await tester.enterText(campos.at(1), 'Pérez');
  await tester.enterText(campos.at(2), celular);
  await tester.enterText(campos.at(3), correo);
  await tester.enterText(campos.at(4), contrasena);
  await tester.enterText(campos.at(5), confirmacion);
}

Future<void> _enviar(WidgetTester tester, String boton) async {
  final b = find.widgetWithText(FilledButton, boton);
  await tester.ensureVisible(b);
  await tester.tap(b);
  await tester.pumpAndSettle();
}

void main() {
  setUpAll(() => initializeDateFormatting('es'));

  testWidgets('crea la cuenta en Auth, completa el perfil con POST /yo y deja la sesión activa',
      (tester) async {
    final auth = AuthFalso();
    final adaptador = await montar(
      tester,
      pantalla: () => const PantallaGuardados(),
      respuestas: {..._base(), 'POST /yo': RespuestaFalsa(_perfilCompleto(), 201)},
      auth: auth,
    );
    await tester.pumpAndSettle();
    await _abrirCrearCuenta(tester);
    expect(find.text('Confirma la contraseña'), findsOneWidget);

    await _llenar(tester);
    await _enviar(tester, 'Crear cuenta');

    expect(auth.registros, ['ana@correo.example']);
    final llamada = adaptador.de('POST', '/yo').single;
    expect(llamada.autorizacion, 'Bearer token-falso');
    expect(llamada.cuerpo, {
      'nombre': 'Ana María',
      'apellido': 'Pérez',
      'celular': '+57 300-123 4567',
    });
    expect(find.text('ana@correo.example'), findsOneWidget, reason: 'sesión activa en Guardados');
    expect(find.text('Cerrar sesión'), findsOneWidget);
  });

  testWidgets('valida en el cliente sin llamar a la red', (tester) async {
    final auth = AuthFalso();
    final adaptador = await montar(
      tester,
      pantalla: () => const PantallaGuardados(),
      respuestas: _base(),
      auth: auth,
    );
    await tester.pumpAndSettle();
    await _abrirCrearCuenta(tester);

    await _enviar(tester, 'Crear cuenta');
    expect(find.text('Escribe tu nombre.'), findsOneWidget);
    expect(find.text('Escribe tu apellido.'), findsOneWidget);
    expect(find.textContaining('celular colombiano'), findsOneWidget);
    expect(find.text('Escribe tu correo.'), findsOneWidget);

    await _llenar(tester, celular: '2001234567', contrasena: 'secreto1', confirmacion: 'otra-cosa');
    await _enviar(tester, 'Crear cuenta');
    expect(find.textContaining('celular colombiano'), findsOneWidget);
    expect(find.text('Las contraseñas no coinciden.'), findsOneWidget);

    await _llenar(tester, contrasena: '123', confirmacion: '123', correo: 'sin-arroba');
    await _enviar(tester, 'Crear cuenta');
    expect(find.text('Ese correo no parece válido.'), findsOneWidget);
    expect(find.text('Usa al menos 6 caracteres.'), findsOneWidget);

    expect(auth.registros, isEmpty);
    expect(adaptador.de('POST', '/yo'), isEmpty);
  });

  testWidgets('400 VALIDACION muestra el motivo en el campo que corresponde', (tester) async {
    await montar(
      tester,
      pantalla: () => const PantallaGuardados(),
      respuestas: {
        ..._base(),
        'POST /yo': RespuestaFalsa({
          'error': {
            'codigo': 'VALIDACION',
            'mensaje': 'Datos no válidos.',
            'reintentable': false,
            'detalles': [
              {'campo': 'celular', 'motivo': 'Debe ser un celular colombiano.'},
              {'campo': 'body.apellido', 'motivo': 'Es demasiado largo.'},
            ],
          },
        }, 400),
      },
    );
    await tester.pumpAndSettle();
    await _abrirCrearCuenta(tester);
    await _llenar(tester);
    await _enviar(tester, 'Crear cuenta');

    expect(find.text('Debe ser un celular colombiano.'), findsOneWidget);
    expect(find.text('Es demasiado largo.'), findsOneWidget);
    expect(find.text('Revisa los datos marcados.'), findsOneWidget);
    expect(find.text('Cerrar sesión'), findsNothing, reason: 'el registro no terminó');
  });

  testWidgets('409: el correo es de otro perfil, se explica y se descarta la sesión', (tester) async {
    final auth = AuthFalso();
    await montar(
      tester,
      pantalla: () => const PantallaGuardados(),
      respuestas: {
        ..._base(),
        'POST /yo': errorFalso(409, 'CONFLICTO_NEGOCIO', 'El correo ya pertenece a otro perfil.'),
      },
      auth: auth,
    );
    await tester.pumpAndSettle();
    await _abrirCrearCuenta(tester);
    await _llenar(tester);
    await _enviar(tester, 'Crear cuenta');

    expect(find.textContaining('Ese correo ya pertenece a otro perfil'), findsOneWidget);
    expect(auth.token, isNull);
  });

  testWidgets('error de Auth (correo ya registrado y otra contraseña) no llama a /yo', (tester) async {
    final adaptador = await montar(
      tester,
      pantalla: () => const PantallaGuardados(),
      respuestas: _base(),
      auth: AuthFalso(correosRegistrados: {'ana@correo.example'}),
    );
    await tester.pumpAndSettle();
    await _abrirCrearCuenta(tester);
    await _llenar(tester, contrasena: 'distinta', confirmacion: 'distinta');
    await _enviar(tester, 'Crear cuenta');

    expect(find.textContaining('Ya existe una cuenta con ese correo'), findsOneWidget);
    expect(adaptador.de('POST', '/yo'), isEmpty);
  });

  testWidgets('correo registrado sin perfil: entra con la misma contraseña y completa con POST /yo',
      (tester) async {
    final auth = AuthFalso(correosRegistrados: {'ana@correo.example'}, contrasenaValida: 'secreto1');
    final adaptador = await montar(
      tester,
      pantalla: () => const PantallaGuardados(),
      respuestas: {..._base(), 'POST /yo': RespuestaFalsa(_perfilCompleto())},
      auth: auth,
    );
    await tester.pumpAndSettle();
    await _abrirCrearCuenta(tester);
    await _llenar(tester);
    await _enviar(tester, 'Crear cuenta');

    expect(auth.intentos, ['ana@correo.example']);
    expect(adaptador.de('POST', '/yo'), hasLength(1));
    expect(find.text('Cerrar sesión'), findsOneWidget);
  });

  testWidgets('login sin perfil (401): pide los datos y los envía con POST /yo', (tester) async {
    final auth = AuthFalso();
    final respuestas = {
      ..._base(),
      '/yo': errorFalso(401, 'NO_AUTENTICADO', 'Inicia sesión para continuar.'),
      'POST /yo': RespuestaFalsa(_perfilCompleto(), 201),
    };
    final adaptador = await montar(
      tester,
      pantalla: () => const PantallaGuardados(),
      respuestas: respuestas,
      auth: auth,
    );
    await tester.pumpAndSettle();
    await tester.tap(find.text('Iniciar sesión'));
    await tester.pumpAndSettle();
    await tester.enterText(find.byType(TextField).at(0), 'ana@correo.example');
    await tester.enterText(find.byType(TextField).at(1), 'secreto');
    await _enviar(tester, 'Entrar');

    expect(find.text('Completa tu perfil'), findsOneWidget);
    expect(find.text('Cerrar sesión'), findsNothing, reason: 'sin perfil la sesión no cuenta como activa');

    final campos = find.byType(TextField);
    await tester.enterText(campos.at(0), 'Ana María');
    await tester.enterText(campos.at(1), 'Pérez');
    await tester.enterText(campos.at(2), '3001234567');
    // Tras crear el perfil, GET /yo ya responde.
    respuestas['/yo'] = RespuestaFalsa(_perfilCompleto());
    await _enviar(tester, 'Guardar y continuar');

    expect(adaptador.de('POST', '/yo').single.autorizacion, 'Bearer token-falso');
    expect(find.text('Cerrar sesión'), findsOneWidget);
  });

  testWidgets('cerrar la hoja con el perfil pendiente descarta la sesión', (tester) async {
    final auth = AuthFalso();
    await montar(
      tester,
      pantalla: () => const PantallaGuardados(),
      respuestas: {
        ..._base(),
        '/yo': errorFalso(401, 'NO_AUTENTICADO', 'Inicia sesión para continuar.'),
      },
      auth: auth,
    );
    await tester.pumpAndSettle();
    await tester.tap(find.text('Iniciar sesión'));
    await tester.pumpAndSettle();
    await tester.enterText(find.byType(TextField).at(0), 'ana@correo.example');
    await tester.enterText(find.byType(TextField).at(1), 'secreto');
    await _enviar(tester, 'Entrar');
    expect(find.text('Completa tu perfil'), findsOneWidget);

    final ahoraNo = find.text('Ahora no');
    await tester.ensureVisible(ahoraNo);
    await tester.tap(ahoraNo);
    await tester.pumpAndSettle();

    expect(auth.token, isNull);
    expect(find.text('Cerrar sesión'), findsNothing);
  });
}
