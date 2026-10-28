# mobile/ — App del pasajero (Flutter, Android)

> Lee antes: `../CLAUDE.md`, `../docs/01-alcance-y-datos-simulados.md`, `../docs/03-contrato-api.md`, `../docs/04-guia-ejecucion-y-apk.md` y **abre `../docs/referencia/prototipo-movil.html` en un navegador** (es el diseño de alta fidelidad). Textos y estados: `../docs/referencia/03-actividad-4-ux-prototipos.md`.
> Solo editas `mobile/`.

## 1. Misión

La app que el **pasajero** instala en su celular Android (APK, gratis) para ver el mapa, las rutas, las busetas en vivo y el ETA. Debe funcionar **sin cuenta** (BR-01); la cuenta solo se pide para Guardados y alertas.

## 2. Stack y dependencias permitidas

| Uso | Paquete |
|---|---|
| Framework | Flutter estable vigente (Dart), objetivo **Android** |
| Mapas | `flutter_map` + `latlong2` (teselas OpenStreetMap por `MAP_TILE_URL`; atribución visible) |
| Ubicación | `geolocator` (solo para "cerca de ti"; **no se guarda**) |
| Red | `dio` (REST) y `web_socket_channel` (tiempo real) |
| Auth | `supabase_flutter` (**solo Auth**; los datos van por la API del backend) |
| Estado y rutas | `flutter_riverpod`, `go_router` |
| Local | `shared_preferences` (dirección del servidor, último filtro) |
| UI | `google_fonts` (Bricolage Grotesque y Atkinson Hyperlegible), `intl` |
| Avisos locales | `flutter_local_notifications` (solo con la app abierta/en segundo plano reciente; sin push remoto) |

Nada más sin anotarlo en `../docs/decisiones-agentes.md`. Fija versiones al crear el proyecto. `applicationId`: `com.busetasapp.prototipo`; nombre visible: "BusetasApp".

## 3. Estructura

```text
mobile/
  pubspec.yaml
  lib/
    main.dart
    app/            # tema (claro/oscuro automático), router, shell con barra inferior
    nucleo/         # configuración, cliente API tipado, cliente WebSocket con reconexión, errores
    caracteristicas/
      mapa/         # mapa + hoja "Rutas cerca de ti"
      buscar/       # texto + chips de hitos
      ruta/         # ficha: Recorrido, Horarios, Frecuencia, En vivo
      eta/          # ETA de una parada + "Avisarme"
      viajar/       # planificación (directas)
      guardados/    # favoritos y alertas (requiere sesión)
      avisos/
      sesion/       # inicio de sesión / registro (hoja modal)
      ajustes/      # servidor + probar conexión + acerca de
  android/          # permisos y configuración de red (ver §6)
  test/
```

Cada característica separa `datos/` (llamadas a la API), `dominio/` (modelos) y `presentacion/` (pantallas y *providers*). No pongas lógica de negocio en los *widgets*.

## 4. Pantallas (barra inferior: Mapa · Buscar · Viajar · Guardados · Avisos)

| Pantalla | Qué hace | Endpoints / eventos |
|---|---|---|
| **Mapa** | Mapa centrado en la ubicación (si se niega el permiso, centro de Manizales); rutas dibujadas con su color; busetas **amarillas con el número lateral** que se mueven con animación entre posiciones; busetas `sin_senal` en gris. Hoja inferior "Rutas cerca de ti" (sello con el código público, nombre, empresas, distancia, "N en servicio"). Sin rutas a `radio_busqueda_m` → "No hay rutas a menos de 800 m. El paradero más cercano a la ruta … está en …" | `GET /rutas/cercanas`, WS `/ws/rutas/{id}` |
| **Buscar** | Campo "Ruta, barrio o lugar" y chips de hitos (Catedral, El Cable, Carrera 23, Fundadores, Terminal). Elegir un hito lista las rutas que pasan; escribir busca por número o nombre. Sin resultados: "Sin resultados para “xyz”. Prueba con un hito como Catedral o con el número de la ruta." | `GET /busqueda/rutas`, `/busqueda/hitos`, `/hitos/{id}/rutas` |
| **Ficha de ruta** | Cabecera con sello y empresas (chips: "Socobuses · 18", "Serviturismo · sin código"); mini mapa; pestañas **Recorrido** (paraderos en orden, tocar una → ETA), **Horarios** (por tipo de día, hoy resaltado, "Información pendiente de actualización"), **Frecuencia** (rango "De 10 a 15 min"), **En vivo** (lista de busetas con estado) y botón de guardar (marcador) | `GET /rutas/{id}`, `/horarios`, `/frecuencias`, `/busetas` |
| **ETA de parada** | Tarjeta por servicio: con GPS "4 min · Buseta 1544 viene hacia aquí · Fuente: GPS · hace 3 s"; con horario "Hasta N min" + aviso amarillo "Sin ubicación de busetas. Estimación por horario… Esté pendiente de la siguiente buseta."; sin datos "El servicio ya cerró". Botón **Avisarme cuando esté a 300 m** (pide sesión si no la hay) | `GET /paraderos/{id}/eta` |
| **Viajar** | Origen (Mi ubicación / hito / tocar el mapa) y destino; opciones directas con barra de tramos (caminata · espera · buseta) y total | `POST /viajes/planificar` |
| **Guardados** | Sin sesión: hoja "Inicia sesión para guardar. Con una cuenta guardas rutas y recibes avisos de llegada." Con sesión: favoritos y alertas activas (borrar) | `/favoritos`, `/alertas-llegada` |
| **Avisos** | Tarjetas con insignia de origen (Movilidad · Empresa · Aplicación) | `GET /avisos` |
| **Ajustes** (icono en la barra superior del Mapa) | Dirección del servidor (por defecto `API_BASE_URL`), **Probar conexión** (`/salud`), versión, "Datos de ejemplo" | — |

## 5. Comportamientos clave

- **Banner permanente** "Datos de ejemplo · no son rutas oficiales" bajo la barra superior.
- **Tiempo real:** al abrir una ruta o el mapa, conecta `/ws/rutas/{rutaId}`; reconexión con espera creciente (1, 2, 4, 8 s, máx. 15 s); mientras no haya conexión consulta `GET /rutas/{id}/busetas` cada `intervalo_refresco_cliente_s`. Pasados 3 intervalos sin datos, muestra "Última actualización hace N s" con **Actualizar**. Cierra el WebSocket al salir de la pantalla.
- **Marcadores:** interpola la posición entre mensajes (≈ 1 s) para que la buseta se deslice; respeta `prefers-reduced-motion` equivalente (`MediaQuery.disableAnimations`).
- **Alertas:** con sesión, conecta `/ws/notificaciones?token=` y al llegar `alerta_llegada` muestra banner dentro de la app y una notificación local. Sin push remoto (D-P09).
- **Estados de UI** en toda pantalla con datos: cargando (esqueletos), vacío (título + causa + acción), error de conexión (banner con **Reintentar** conservando lo cargado), desactualizado, sin señal, sin sesión.
- **Ubicación:** se pide al usarla; si se niega, se usa el centro de Manizales o el hito elegido. Jamás se envía a un servidor salvo como parámetro de la consulta puntual y nunca se registra.
- **Accesibilidad:** objetivos ≥ 44 dp, texto escalable, contraste ≥ 4.5:1, `Semantics` en marcadores y botones, información nunca solo por color. Modo oscuro automático.
- Idioma `es`; horas 24 h; zona `America/Bogota`.

## 6. Android (necesario para que el APK funcione en la demo)

- Permiso `INTERNET` en `android/app/src/main/AndroidManifest.xml` (el de release **no** hereda el de depuración) y ubicación (`ACCESS_COARSE_LOCATION`, `ACCESS_FINE_LOCATION`).
- Tráfico en claro hacia el portátil (`http://192.168.x.x:8000`): `android:usesCleartextTraffic="true"` o una *network security config* limitada a IPs privadas. Documenta la elección.
- Firma: la de depuración vale para la demo. No hay publicación en Google Play.
- Configuración por `--dart-define`: `API_BASE_URL`, `SUPABASE_URL`, `SUPABASE_ANON_KEY`, `MAP_TILE_URL`. La dirección del servidor se puede sobrescribir en Ajustes **sin recompilar**.
- Comandos de compilación y distribución: `../docs/04-guia-ejecucion-y-apk.md` §7. Si algo difiere al crear el proyecto, **corrige la guía**.

## 7. Orden de construcción

1. **M0** Proyecto, tema, navegación, cliente API (con datos de prueba mientras el backend devuelve 501), Ajustes de servidor y "Probar conexión".
2. **M1** Mapa + hoja de rutas cercanas + Buscar + Ficha de ruta (Recorrido/Horarios/Frecuencia).
3. **M2** En vivo (WebSocket + respaldo REST + animación) y ETA con sus tres fuentes.
4. **M3** Avisos, sesión (Supabase Auth), Guardados, "Avisarme" y notificación local.
5. **M4** Viajar.
6. **M5** Pulido, estados de error, APK de release probado en un celular real contra el backend del portátil.

## 8. Pruebas

- `flutter analyze` sin errores; `flutter test` para los modelos y la lógica de ETA/interpolación.
- Recorrido manual en un celular real: instalar APK → Ajustes → servidor → Mapa → buseta se mueve → ficha → parada → ETA → apagar WiFi (banner de error) → volver (reconexión) → Panel de demo "perder señal" (buseta gris) → Avisarme (pide sesión).

## 8 bis. Ajustes por la revisión de las SPECs (tienen prioridad sobre las secciones anteriores)

- **Sin busetas (HU-P05):** «No hay busetas en servicio en esta ruta en este momento.»; fuera de horario: «El servicio de esta ruta ya cerró» o «aún no inicia; sale a las 04:45».
- **Ruta inexistente (HU-P02):** «No encontramos esa ruta. Estas rutas cercanas podrían servirte:» con `GET /rutas/cercanas` (o `GET /hitos/{id}/rutas` si el destino es un hito).
- **Desvío (HU-P11):** `/ws/notificaciones` ahora también emite `tipo: "alerta_desvio"`. Muéstralo como notificación dentro de la app con el texto del mensaje (una vez por episodio). Contrato en `docs/03-contrato-api.md`.
- **Villamaría** es una ruta más del catálogo, del mapa y de la búsqueda.
- Textos completos: `docs/01-alcance-y-datos-simulados.md` §3.1.

## 9. Qué NO hacer

- No hay versión iOS ni publicación en tiendas.
- No implementar mapas de pago ni claves de pago.
- No guardar la ubicación del pasajero.
- No llamar a tablas de Supabase desde la app.
- No inventar endpoints: pide lo que falte en `../docs/solicitudes-entre-agentes.md`.
