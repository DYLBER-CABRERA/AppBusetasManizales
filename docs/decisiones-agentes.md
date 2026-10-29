# Decisiones de los agentes

Registra aquí cada decisión que cambie el contrato o el alcance (fecha, agente, qué, por qué).

## 2026-10-27 · backend-dev · B0 y B1

- **Dependencias y versiones fijadas** (`backend/pyproject.toml`; todas gratuitas y de código abierto): fastapi 0.162.0, uvicorn 0.54.0, pydantic 2.14.1, pydantic-settings 2.16.1, psycopg 3.3.6 (+pool), httpx 0.28.1, PyJWT 2.15.1, python-telegram-bot 22.8, pytest 9.2.0, pytest-asyncio 1.4.1, ruff 0.17.3. Son las del `CLAUDE.md` de backend; no se agregó ninguna otra.
- **Contrato en B0:** forma plana de `GET /rutas/{id}` y `paraderoIds` en `POST /rutas` (rutas circulares, D-P02). Detalle en `docs/03-contrato-api.md` §7.
- **`GET /salud` bajo `/api/v1`** y `501 PENDIENTE` como respuesta de los endpoints sin lógica (código `PENDIENTE` fuera de la lista de códigos de CLAUDE.md §6; temporal hasta cerrar B8).
- **Scripts con simulacro por defecto:** `cargar_semillas.py` y `crear_usuarios_demo.py` no tocan ninguna base sin `--aplicar`; `verificar_bd.py` revierte todo (ROLLBACK) y `--aplicar-migraciones` aborta si ya existe `public.empresa`.
- **Hitos adicionales:** además de los 6 de docs/01 §2.3 se geocodifican `La Enea` (barrio) y `Villamaría` (sector), necesarios como puntos de paso y para el ejemplo del bot. Coordenadas marcadas `validado:false` hasta que el equipo las revise en un mapa.
- **Paraderos ficticios:** la tabla `paradero` no tiene columna `ficticio`; se marca con `direccion = 'Paradero de ejemplo (ficticio)'` y con `ficticio:true` en los GeoJSON.
- **Uso histórico:** `evento_uso` no distingue simulado de real y no se modificó la tabla (`PENDIENTE(decisión)` según docs/01 §2.9). Tipos usados: ruta→`detalle_ruta`, horario→`horarios`, ETA→`eta`, paradero→`mapa`.

## 2026-10-27 · backend-dev · decisiones del equipo aplicadas a B1

- **`aviso.tipo_cambio`** (text, nullable, restringido a cierre/desvio/obra/condicion) agregado en `0002_tablas.sql`; la semilla del aviso de movilidad usa `obra`. Resuelve el `PENDIENTE` de `tipoCambio`.
- **Buseta 3102 también en Villamaría:** turno de hoy 04:30–14:00 en Villamaría y 14:00–23:30 en La Enea (supuesto: partir el día como la 1520, porque una buseta no puede estar en dos rutas a la vez). Actualizados `docs/01` §2.6 y `datos.json`. Resuelve el `PENDIENTE` de Socobuses · Villamaría sin buseta.
- **`evento_uso` queda como está:** sin columna que distinga simulado de real (`docs/01` §2.9).
- **Extensiones `with schema public`** (postgis, pg_trgm, unaccent, btree_gist) en `0001`, para que `normalizar_texto` (`public.unaccent`) funcione. `verificar_bd.py` ahora comprueba que estén en `public` y que exista `aviso.tipo_cambio`.

## 2026-10-28 · backend-dev · verificar_bd y progreso en tramos repetidos

- **`verificar_bd.py` independiente de las semillas y de la fecha de hoy:** `turno_vigente`, `guardar_posicion` y las violaciones intencionales crean sus propias empresas, rutas, servicios y busetas (`zz …`) con fechas fijas 2099-01-05/06, y cada verificación corre en un savepoint que siempre se revierte, así no chocan con `ux_rodamiento_empresa_fecha` ni entre sí. Solo `rutas_cercanas`, `progreso` y el sábado de Sideral usan la semilla.
- **Progreso en trazados que repiten calles: opción B (secuencial) con ayuda de A.** Una ruta circular que vuelve por la misma vía (Villamaría es ida y vuelta por la misma carretera) no se puede arreglar solo con puntos de paso: la geometría repite el tramo. Se añade en `0003` la función `progresos_paraderos_ruta(ruta, sentido)` (CTE recursiva: cada paradero se proyecta solo desde el progreso del anterior) y `progreso_paradero` la usa (si el paradero no está en la ruta, cae en la proyección más cercana). `progreso_en_ruta` no cambia. `generar_trazados.py` ahora ubica cada hito en orden de recorrido (primer vértice cercano a partir del anterior) y guarda `avance_m` por paradero; los 4 GeoJSON se regeneraron con OSRM.
- **PENDIENTE (B3):** la posición de una **buseta** sobre un tramo repetido sigue siendo ambigua con `progreso_en_ruta`; el simulador conoce su propio avance y el ingreso real podrá usar el último progreso conocido como pista.

## 2026-10-28 · backend-dev · actualizar_bd.py

- **`backend/scripts/actualizar_bd.py`** (no estaba en la lista de scripts de `backend/CLAUDE.md` §3): actualiza una BD ya migrada y sembrada cuando cambian las funciones de `0003` o los GeoJSON. Simulacro sin conexión por defecto; `--comparar` abre una conexión de solo lectura; `--aplicar` ejecuta todo en una transacción. Reemplaza funciones con `create or replace`, agrega `aviso.tipo_cambio` si falta, actualiza `ruta_trazado` con UPDATE, mueve/crea paraderos por nombre y da de baja (lógica) solo los paraderos ficticios sin ninguna referencia. No toca usuarios, perfiles, rodamientos, avisos, favoritos, alertas ni busetas.

## 2026-10-28 · backend-dev · B2 consulta pública

- **Sin dependencias nuevas.** Casos de uso como clases invocables; repositorios SQL escritos a mano con `psycopg_pool` (filas como `dict`). `composicion.py` crea el pool **sin abrirlo** (el *lifespan* lo abre con `wait=False`) y arma `Servicios` con `construir_servicios(repos, config, reloj)`, que las pruebas reutilizan con repositorios en memoria (`pruebas/dobles.py`).
- **Sin `DATABASE_URL` los endpoints con lógica responden 503** (no 500); `pruebas/conftest.py` vacía `DATABASE_URL` para que ninguna prueba unitaria toque la BD real aunque exista `.env`.
- **Eventos de uso** como tarea en segundo plano de FastAPI (`BackgroundTasks`), tras responder, y solo si la consulta tuvo éxito. Mapeo en `docs/03` §8.
- **`nucleo/parametros.py`** (puerto `PuertoParametros` + valores por defecto de docs/03 §6) y `ParametrosSql` con caché de 60 s: la fila de BD manda; el valor por defecto solo se usa si falta.
- **Búsqueda sin `pg_trgm.similarity`**: solo *contiene* sobre `normalizar_texto`; evita depender del esquema donde Supabase instale las extensiones. Se puede añadir tolerancia a erratas más adelante.
- **Bucle de eventos en Windows:** `servidor.fabrica_bucle` (SelectorEventLoop) para `--loop`, porque psycopg asíncrono no soporta Proactor. Es riesgo no verificado contra la BD real (ver reporte).
- **Prueba de integración** `pruebas/integracion/test_consulta_publica_bd.py` (no corre por defecto; exige `PRUEBAS_INTEGRACION=1` y `-m integracion`). Solo escribe filas anónimas en `evento_uso`.

## 2026-10-28 · backend-dev · B3a seguimiento

- **Sin dependencias nuevas.** `EmisorEventosEnMemoria` (bus en proceso, un suscriptor roto no frena a los demás). `PuertoParametros` suma `objeto()` para `caja_ciudad`; la caja provisional también queda como valor por defecto en código.
- **Mensaje de ETA por horario:** el contrato de ejemplo incluye siempre «Esté pendiente de la siguiente buseta.»; se mantiene en ambos casos y solo cambia el arranque («Sin ubicación de busetas.» si nunca hubo posición, «Sin señal GPS en este momento.» si hay posición vieja).
- **`seguimientoDisponible`** = hay al menos una buseta con posición en la lista; **`unidadesEnServicio`** = busetas con turno publicado vigente en la ruta (con o sin GPS). Definición propia (docs/03 no la daba).
- **`fecha_invalida`** = hora sin zona horaria; `lat`/`lng` ya no se validan en el esquema Pydantic para poder devolver `coordenadas_invalidas` por posición (contrato §2.6).
- **Lectura de credenciales GPS** (`RepositorioFuentesGpsSql`) vive en `administracion`; el CRUD de B5 la extenderá.
- **`composicion.construir_contenedor`** acepta un reloj inyectable (pruebas con `RelojFijo`).

## 2026-10-28 · backend-dev · B3b tiempo real, simulador, demo y autenticación

- **Sin dependencias nuevas** (httpx, psycopg y PyJWT ya estaban; PyJWT no se usa todavía).
- **Verificación del JWT por `GET /auth/v1/user` de Supabase** en vez de validar la firma localmente: docs/03 §1 deja abierta "la clave/JWKS vigente que indique su panel" y no sabemos si el proyecto firma con secreto compartido o con claves asimétricas; la llamada funciona con ambos y no necesita un secreto nuevo. Costo: una petición a Supabase por token cada 30 s (caché en memoria). Si el equipo prefiere validación local, solo cambia `AutenticacionSupabase` (el puerto `PuertoAutenticacion` no cambia).
- **`RelojSimulado` corre desde la hora fijada** (antes quedaba congelado en `HH:MM:00`, lo que habría descartado todas las posiciones nuevas por no ser más recientes). `fijar_hora(None)` vuelve al reloj real.
- **El simulador lee `datos.json`** para el rodamiento de hoy en lugar de importar `scripts/` (el código de `src/` no depende de los scripts). Escribe en `rodamiento` y `turno` solo si faltan y solo con `MODO_DEMO=true`.
- **Serviturismo sin GPS por nombre de empresa** (constante `EMPRESAS_SIN_GPS_POR_DEFECTO` en el simulador, citando docs/01 §4): la BD no tiene un indicador de "empresa con GPS".
- **Bucle de eventos:** el simulador y la difusión WebSocket corren en el mismo bucle de uvicorn; el WebSocket solo funciona sobre una instancia (límite documentado).
- **PENDIENTE(B4/B6):** `senal_perdida`, `aviso_nuevo` y `/ws/notificaciones` con token.
- **PENDIENTE(decisión):** el simulador solo comprueba el turno; no consulta el horario del servicio para decidir si "ya cerró" (docs/01 §4 pide no mover la buseta fuera del horario). El ETA sí responde "El servicio ya cerró" / "Aún no inicia".

## 2026-10-28 · backend-dev · B4 operación del jefe y avisos por rol

- **Sin dependencias nuevas.** `ValidadorRodamiento` y `PoliticaDeAvisos` en `dominio/` (stdlib), con pruebas.
- **`version` de horarios y frecuencias = `servicio_ruta.version`** (un solo contador por servicio, incrementado por cada `PUT` de cualquiera de los dos): simple y atómico; el panel debe refrescar la versión con cada respuesta.
- **`PUT` de busetas/conductores:** `null` u omitido significa "no cambiar" (no se puede vaciar placa o código). Decisión por simplicidad del contrato actual, que no distingue ausencia de `null`.
- **Un solo `409 CONFLICTO_NEGOCIO` para el reemplazo (D-P15) y para publicar con solapamientos**, con la lista en `detalles` (`turnosAfectados` / `advertencias`).
- **Un rodamiento publicado no se edita** (solo se anula): evita cambiar turnos que el ETA y el simulador ya usan; si el equipo quiere editar uno publicado hay que definirlo.
- **Avisos del jefe sin paraderos** (BR-05: avisos de su empresa sobre sus rutas). Retirar = `estado: retirado` (no se borra la fila).
- **`aviso_nuevo` por WebSocket** al publicar (evento interno `aviso.publicado`), cerrando el PENDIENTE de B3b.
- **Pruebas:** se permite `E501` en `pruebas/` (literales largos de peticiones HTTP).

## 2026-10-28 · backend-dev · B5 movilidad, administración y estadísticas

- **Sin dependencias nuevas.** Alta de usuarios con la API admin de Supabase Auth vía `httpx` y `SUPABASE_SERVICE_ROLE_KEY` (solo backend, nunca registrada): `POST /auth/v1/invite`. Decisión: invitación por correo en vez de contraseña inicial, porque el contrato no maneja contraseñas. Si el correo de invitación no está configurado en el proyecto Supabase, la creación fallará con `503`.
- **Ruta compartida al registrar:** `confirmarCompartida` se exige cuando el alta trae más de una empresa (docs/03 solo lo nombraba para "ruta ya asignada a otra empresa").
- **Baja de paradero usado:** advierte pero no desvincula de las rutas (decisión de seguridad: no alterar trazados en silencio).
- **Identidad efectiva del administrador en endpoints del jefe:** `identidad_de_gestion` (nucleo/dependencias) devuelve un `Identidad` con rol jefe y la empresa de `empresaId`; los casos de uso no cambian. El `usuario_id` real queda como autor.
- **`dar_de_baja_ruta` usa `current_date` de la BD** (función de B1): el límite "turnos futuros" del chequeo previo usa la fecha del `PuertoReloj` (Bogotá); pueden diferir unas horas al caer la noche (UTC).

## 2026-10-28 · backend-dev · B6 pasajero, alertas y planificación

- **Sin dependencias nuevas.** `PuertoNotificador` (nucleo) con `NotificadorCompuesto`: WebSocket por usuario y, para chats de Telegram, una función `enviar_telegram` que asignará el bot (B7); sin bot el aviso por chat se omite con un registro informativo.
- **`CrearAlertaLlegada.para_destino`** admite `usuario_id` o `telegram_chat_id` (D-P08): el bot de B7 reutiliza el mismo caso de uso.
- **Estado `notificada`:** tras el primer aviso la alerta sigue evaluándose (el enfriamiento evita repeticiones); solo `DELETE` la desactiva.
- **Caminata de la planificación** = suma de la caminata de origen y de destino (docs/03 tenía un único `caminataMin`).
- **Sin frecuencia o sin horario hoy ⇒ sin opción** en la planificación (el ETA sí muestra `no_disponible`).
- **`requiere_rol(..., mensaje=)`** permite el texto «Inicia sesión para guardar.» del contrato en favoritos y alertas.
- **El estado de episodios de desvío vive en memoria** del servidor (una instancia): un reinicio puede repetir un aviso de desvío.

## 2026-10-28 · backend-dev · B7 bot de Telegram

- **Sin dependencias nuevas** (`python-telegram-bot` 22.8 ya estaba fijada). `adaptadores_externos/bot_telegram.py` tiene `LogicaBot` (conversación pura, probada sin red) y `BotTelegram` (adaptador PTB).
- **Estado del chat en memoria** (ubicación ≤ 10 min y pares ruta/paradero de los botones); se pierde al reiniciar el servidor, a propósito.
- **Texto libre:** se quitan palabras vacías y se prueba la frase y cada palabra contra hitos y rutas (primero hitos). No hay lógica de intención más allá de palabras clave.
- **`E501` permitido** en `bot_telegram.py` (textos largos de conversación).
- **PENDIENTE(decisión):** «Ver en mapa» del mockup no se implementó (no hay URL de mapa pública definida); «Ver ruta» muestra empresas y paradas en texto. No se probó contra la red de Telegram: requiere un token real.

## 2026-10-28 · backend-dev · B8 pulido

- **Se eliminó el código `PENDIENTE` / `501`** (`ErrorPendiente`, `pendiente()` y la respuesta 501 en OpenAPI): resuelve la desviación de la lista de códigos de CLAUDE.md §6 anotada en B0.
- **Pruebas de integración ampliadas** (`pruebas/integracion/test_flujos_bd.py`): 401/403/404, ETA con simulador, flujo de rodamiento con aislamiento entre jefes, eliminar ruta con confirmación, favoritos y planificación. **Escriben en la BD** (ver docstring). No se ejecutaron.
## 2026-10-28 · web-admin-dev · W0

- **Versiones fijadas** (`web-admin/package.json`, todas gratuitas/código abierto): next 16.4.3, react 19.3.1, tailwindcss 4.3.3, @supabase/supabase-js 2.118.0, @supabase/ssr 0.12.7, @tanstack/react-query 5.105.0, openapi-typescript 7.13.0, openapi-fetch 0.17.0, react-hook-form 7.91.0, zod 4.6.7, leaflet 1.9.4, react-leaflet 5.0.0, recharts 3.10.1, eslint 9.39.5.
- **TypeScript 5.9.3, no 7.x:** `openapi-typescript` 7.13 declara `peer typescript@^5` y `npm install` falla con 7.0.2.
- **Dependencias fuera de la lista de `web-admin/CLAUDE.md` §2** (necesarias, licencia MIT): `@hookform/resolvers` 6.0.2 (conecta `zod` con `react-hook-form`); `@tailwindcss/postcss` 4.3.3 y `postcss` 8.5.32 (Tailwind 4 con Next); `eslint-config-next` 16.4.3; tipos de desarrollo `@types/node` 20, `@types/react`, `@types/react-dom`, `@types/leaflet`.
- **`src/proxy.ts` en vez de `src/middleware.ts`:** Next 16 renombró el archivo. Solo exige que exista sesión (cookie de Supabase); el rol lo decide el backend vía `GET /yo` y lo aplica el layout `(panel)`.
- **Modo de ejemplo (PENDIENTE, quitar al integrar):** con `NEXT_PUBLIC_USAR_MOCKS=true` el cliente de API devuelve datos de `src/lib/mocks.ts` (doc 01 §2 y §5) cuando el backend responde 501 o no hay red; sin variables de Supabase el login acepta las cuentas del doc 01 §5 sin verificar contraseña (cookie `busetas_sesion_ejemplo`, solo en el navegador; el backend nunca la reconoce).
- **Tipos:** `src/lib/tipos-api.d.ts` se genera con `npm run tipos` desde `contrato/openapi.json`; no se edita a mano.

## 2026-10-28 · web-admin-dev · W1

- **Selector de empresa del administrador** en `/jefe/*` (`src/app/(panel)/jefe/layout.tsx`): solo visible para el rol `administrador` (el rol sale de `GET /yo`). Agrega `empresaId` como parámetro de consulta a `/mis-servicios`, `/busetas`, `/conductores` y `/rodamientos`. Vive en memoria y se borra al cerrar sesión; el jefe nunca lo envía. `PENDIENTE`: aún no está en `contrato/openapi.json`.
- **Servidor de ejemplo del jefe** (`src/lib/mocks-jefe.ts`, `PENDIENTE`, quitar al integrar): replica versión, reemplazo, solapamientos y publicar mientras el backend responda 501; usa localStorage para probar el 409 con dos pestañas.
- **Asignar:** Fin estimado es obligatorio en el formulario (la API lo admite vacío) para que se puedan detectar solapamientos. Un turno con la misma ruta y hora de salida se reemplaza, no se duplica.
- **Rodamiento publicado:** se muestra de solo lectura. Anular y editar uno publicado quedan `PENDIENTE(decisión)`.

## 2026-10-28 · web-admin-dev · W2

- **Panel de demo con el backend real** (sin datos de ejemplo): `GET /demo/estado` cada 3 s y `POST /demo/escenarios` para las siete acciones. El ítem del menú aparece solo si `/demo/estado` responde 200; con 404 la página explica que falta `MODO_DEMO=true`.
- **Mapa en vivo:** `BusetaDemo` no trae `empresaId`, ruta ni coordenadas, así que el panel usa `GET /empresas` (nombre → id para los escenarios por empresa) y, por cada ruta de `GET /rutas`, el WebSocket `/ws/rutas/{id}` con reconexión (1, 2, 4, 8 s, máx. 15 s) y respaldo `GET /rutas/{id}/busetas` cada 5 s cuando el WebSocket no entrega datos en 8 s. Etiqueta de cada buseta con su número y, si no tiene señal, la palabra «sin señal» (borde rojo ladrillo, círculo vacío).
- **Parámetros y fuentes GPS (PENDIENTE, datos de ejemplo hasta B5):** `src/lib/mocks-admin.ts`. Los mínimos y máximos de ejemplo son inventados salvo «50 a 2000» de la distancia de aviso; los reales los manda el backend (`minimo`/`maximo`). La clave de una fuente nunca se guarda: vive en memoria mientras el modal está abierto (sin Esc para cerrarlo por accidente) y se borra de la caché de la mutación.
- **`Modal`** admite `sinEscape`.

## 2026-10-28 · web-admin-dev · integración con el backend completo (B5 a B8)

- **Datos de ejemplo eliminados:** se borraron `mocks.ts`, `mocks-jefe.ts` y `mocks-admin.ts`, el parámetro `ejemplo` de `consultar`, la sesión de ejemplo (cookie y modo de login) y `NEXT_PUBLIC_USAR_MOCKS`. Ningún endpoint del contrato responde 501. El login exige Supabase configurado.
- **`empresaId`** ya es parámetro tipado del contrato (§12). El middleware de `src/lib/api.ts` lo agrega solo cuando el administrador eligió empresa y solo a las rutas del jefe y a `PUT /servicios/{id}/horarios|frecuencias`.
- **Parámetros:** `caja_ciudad` (objeto, sin mínimo ni máximo) se muestra de solo lectura (`PENDIENTE(decisión)`: editor). La pantalla avisa que un cambio tarda hasta 60 s (caché del backend). Fuentes GPS solo lista empresas en estado `activo`.

## 2026-10-28 · web-admin-dev · W3 Secretaría de Movilidad

- **Rutas:** tarjetas desde `GET /rutas`; registrar con paraderos en orden (lista + mapa; tocar un paradero del mapa lo agrega o quita) y empresas con códigos opcionales; editar con `version` (`GET /rutas/{id}`, sin caché para partir siempre de la versión vigente). Más de una empresa sin `confirmarCompartida` → 409 → modal «Ruta compartida». Eliminar: confirmación y, si hay turnos futuros (`detalles.turnosFuturos`), segundo modal con la lista y `confirmar=true`. `RutaResumen` no trae `version`: se pide a `GET /rutas/{id}` al eliminar y, para quitar una empresa, a `GET /rutas/{id}/horarios` (versión del servicio).
- **Asignar y quitar empresa** por ruta (`POST /rutas/{id}/servicios`, `DELETE /servicios/{id}`): se agregó porque BR-04 asigna rutas a cada empresa. Asignar a una ruta que ya opera otra empresa muestra el modal de ruta compartida.
- **Paraderos:** mapa para fijar la ubicación y editar tocando un paradero; el duplicado (409) se muestra como «Ya existe un paradero llamado X a menos de 20 m…» (el backend no devuelve la distancia exacta); la baja de uno usado por rutas lista `detalles.rutas` y pide confirmar.
- **Movilidad:** formulario con tipo, título, mensaje, rutas y paraderos afectados y vigencia (hora de Bogotá, -05:00); lista los avisos `movilidad` vigentes con **Retirar**. El contador de caracteres usa 500 fijo (`PENDIENTE`: la Secretaría no puede leer `longitud_max_aviso`).

## 2026-10-28 · web-admin-dev · modal de la clave GPS y pruebas

- **Defecto corregido:** el modal de la clave nueva se cerraba con el segundo Esc (Chromium cierra un `<dialog>` cuyo `cancel` se canceló sin avisar otra vez). `Modal` tiene ahora la opción `obligatorio` (reemplaza `sinEscape`): cancela `keydown` de Esc, cancela `cancel` y, si el navegador lo cierra igualmente, lo reabre. El clic fuera no lo cierra. `ModalClaveNueva` solo se cierra con el botón «Cerrar», habilitado tras copiar la clave o marcar «Ya guardé la clave en un lugar seguro» (por si el portapapeles falla). El foco va al botón Copiar (`data-foco-inicial`); los ids de título usan `useId`.
- **Pruebas (dependencias de desarrollo, MIT, fuera de la lista de web-admin/CLAUDE.md §2):** `vitest` 3.2.7 (la 5.x exige Node 22), `jsdom` 26.1.0, `@testing-library/react` 16.3.3, `@testing-library/dom` 10.4.2, `@testing-library/user-event` 14.6.8. `npm test`. `npm audit` avisa de vulnerabilidades solo en el servidor de desarrollo de vitest; `npm audit --omit=dev` da 0. Limitación: jsdom no reproduce el cierre real de Chromium; la prueba simula el segundo Esc con `dialog.close()`. Hay que verificar a mano en el navegador.

## 2026-10-29 · web-admin-dev · W4

- **Jefe:** `/jefe/horarios` (pestañas Horarios, Frecuencias, Busetas y conductores): editor por tipo de día con las validaciones de `src/lib/horarios.ts` (probadas con vitest): primera ≤ última salida, cierre ≥ última salida, fin > inicio, mín ≤ máx, franjas sin solape (`24:00` permitido como fin). Un día sin marcar queda «Información pendiente de actualización». Cada PUT incrementa la `version` del servicio: el editor toma siempre la última cargada y, tras guardar, se vuelven a pedir horarios y frecuencias. Alta de busetas y conductores solamente (no edición). `/jefe/avisos`: el jefe debe elegir al menos una ruta (contrato §11) y ve solo los avisos `empresa` de su empresa; el administrador entrando ahí es dirigido a `/admin/avisos`. `/jefe/uso`: barras por día (recharts, sin SSR, con tabla alternativa), tablas por ruta y por tipo; el administrador pasa la empresa elegida como `empresaId`.
- **Administrador:** `/admin/usuarios` (búsqueda por correo, crear con invitación por correo, editar rol, empresa —solo jefe—, activo; 409 al quitar el rol al último administrador), `/admin/empresas` (crear, editar nombre y estado con `version`), `/admin/avisos` (origen `aplicativo`, lista todos los avisos vigentes y permite retirar cualquiera; el máximo de caracteres sale de `longitud_max_aviso`).
- **PENDIENTE(decisión):** el jefe sigue usando 500 caracteres fijos para avisos (no puede leer el parámetro); edición de busetas y conductores; editor de `caja_ciudad`.
