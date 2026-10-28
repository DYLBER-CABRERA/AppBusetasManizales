# backend/ — API, tiempo real, simulador de GPS y bot de Telegram

> Lee antes: `../CLAUDE.md`, `../docs/01-alcance-y-datos-simulados.md`, `../docs/03-contrato-api.md`.
> Eres el **único** que escribe en `backend/` y en `../docs/03-contrato-api.md` y `../contrato/openapi.json`.

## 1. Misión

Servir la API REST, los WebSockets y el bot de Telegram del prototipo, con **arquitectura hexagonal**, sobre Supabase (Postgres + PostGIS + Auth). Incluye un **simulador de GPS** que alimenta el sistema por el mismo caso de uso que usaría un GPS real.

## 2. Stack y dependencias permitidas

| Uso | Paquete |
|---|---|
| Lenguaje | Python 3.12+ |
| API | `fastapi`, `uvicorn[standard]` (WebSockets incluidos) |
| Esquemas HTTP y configuración | `pydantic` v2, `pydantic-settings` |
| Base de datos | `psycopg[binary,pool]` v3 asíncrono, SQL escrito a mano (funciones PostGIS) |
| HTTP saliente | `httpx` (API admin de Supabase Auth, OSRM y Nominatim en los scripts) |
| JWT | `PyJWT[crypto]` |
| Telegram | `python-telegram-bot` v21+ (asíncrono, *polling*) |
| Pruebas / calidad | `pytest`, `pytest-asyncio`, `ruff` |

Nada más sin anotarlo en `../docs/decisiones-agentes.md`. Sin ORM. Sin Shapely (la geometría de movimiento se hace en Python puro con *haversine*; las consultas espaciales, en PostGIS). Fija las versiones al crear `pyproject.toml`.

## 3. Estructura (la aprobada en la presentación, más `scripts/`)

```text
backend/
  pyproject.toml              # pythonpath de pytest = ["src"]
  .env.example
  src/
    composicion.py            # ÚNICO lugar que crea adaptadores y los inyecta
    servidor.py               # crea la app FastAPI (lifespan: pool BD, simulador, bot)
    nucleo/
      errores.py              # ErrorValidacion, ErrorNoAutenticado, ErrorNoAutorizado, ErrorNoEncontrado,
                              # ErrorConflictoVersion, ErrorConflictoNegocio, ErrorServicioExterno
      autorizacion.py         # Identidad(usuario_id, rol, empresa_id) y reglas por rol y empresa
      configuracion.py        # pydantic-settings (variables de entorno)
      registro.py             # logging con filtro que oculta secretos y datos personales
      version_optimista.py
    modulos/
      red/ horarios/ seguimiento/ planificacion/ busqueda/
      pasajero/ operacion/ avisos/ estadisticas/ administracion/
        dominio/              # entidades, servicios de dominio, puertos (Protocol)
        aplicacion/           # casos de uso
        infraestructura/      # routers, esquemas Pydantic, repositorios SQL, adaptadores
        __init__.py           # API pública del módulo
    adaptadores_externos/
      bot_telegram.py         # el chatbot llama a los casos de uso
      websocket_posiciones.py # difunde posiciones y alertas a las apps
    herramientas/
      simulador_gps.py        # mueve busetas y llama a registrar_posiciones
  scripts/
    generar_trazados.py       # OSRM -> GeoJSON (una vez)
    geocodificar_hitos.py     # Nominatim -> hitos.json (una vez; validar a mano)
    cargar_semillas.py
    crear_usuarios_demo.py
    verificar_bd.py           # pruebas de humo de restricciones y funciones SQL
    exportar_openapi.py       # escribe ../contrato/openapi.json
  supabase/
    migraciones/              # 0001..0005 (ver §6)
    semillas/                 # datos.json, hitos.json, trazados/*.geojson
  pruebas/
    unitarias/ integracion/
```

Reglas: `dominio` no importa FastAPI, Pydantic, psycopg ni nada externo (solo biblioteca estándar). `aplicacion` solo importa de `dominio`. Un módulo no importa archivos internos de otro; usa su `__init__.py`. Los routers no tienen reglas de negocio. Cada caso de uso recibe `Identidad` y sus puertos por constructor/clausura y devuelve *dataclasses* simples.

## 4. Módulos y casos de uso

| Módulo | Casos de uso (nombre en el código) | HU |
|---|---|---|
| `red` | `consultar_rutas_cercanas`, `listar_rutas`, `obtener_detalle_ruta`, `consultar_paraderos_cercanos`, `registrar_ruta`, `editar_ruta`, `eliminar_ruta`, `asignar_ruta_a_empresa`, `retirar_ruta_de_empresa`, `crear_paradero`, `editar_paradero`, `eliminar_paradero`, `crear_hito` | P01, P02, SM01–SM04 |
| `horarios` | `consultar_horarios`, `consultar_frecuencias`, `actualizar_horarios_servicio`, `actualizar_frecuencias_servicio` | P03, P04, J02 |
| `seguimiento` | `registrar_posiciones`, `consultar_busetas_en_vivo`, `calcular_eta_paradero` | P05, P06 |
| `planificacion` | `planificar_viaje` (solo directas) | P07 |
| `busqueda` | `buscar_rutas_por_texto`, `buscar_hitos`, `consultar_rutas_por_hito` | P08, P09 |
| `pasajero` | `listar_favoritos`, `agregar_favorito`, `quitar_favorito`, `crear_alerta_llegada`, `listar_alertas`, `eliminar_alerta`, `evaluar_alertas_por_posicion` | P10, P11 |
| `operacion` | `listar_busetas`, `guardar_buseta`, `listar_conductores`, `guardar_conductor`, `crear_rodamiento`, `actualizar_rodamiento`, `publicar_rodamiento`, `anular_rodamiento` | J01, J02, J04 |
| `avisos` | `publicar_aviso`, `retirar_aviso`, `consultar_avisos_vigentes` | J05, SM05, A05 |
| `estadisticas` | `registrar_evento_uso`, `consultar_estadisticas_uso` | J06 |
| `administracion` | `obtener_perfil` (`GET /yo`), `gestionar_usuarios`, `gestionar_empresas`, `gestionar_credenciales_gps`, `configurar_parametro`, `ejecutar_escenario_demo`, `consultar_estado_demo` | A01–A05 |

## 5. Puertos de salida (interfaces `typing.Protocol` en `dominio/`)

`RepositorioRutas`, `RepositorioParaderos`, `RepositorioHitos`, `RepositorioHorarios`, `RepositorioBusetas`, `RepositorioConductores`, `RepositorioRodamientos` (incluye `turno_vigente`), `RepositorioPosiciones` (guardar última, listar por servicio, `calcular_progreso`, `calcular_progreso_paradero`), `RepositorioCredencialesGps`, `RepositorioFavoritos`, `RepositorioAlertas`, `RepositorioAvisos`, `RepositorioUsuarios`, `RepositorioEmpresas`, `RepositorioParametros`, `RepositorioEventosUso`, `PuertoAutenticacion` (`verificar_token(jwt) -> Identidad`, `crear_usuario(...)`), `PuertoReloj` (`ahora()`, con implementación real y simulada), `EmisorEventos` (`emitir`, `suscribir`), `PuertoNotificador` (`notificar_alerta(destino, mensaje)`).

- Toda escritura recibe `version_esperada` y lanza `ErrorConflictoVersion` (409) con la versión actual. Implementación: `update … where id = %s and version = %s returning …`; si no afecta filas, distinguir 404 de 409.
- Los repositorios devuelven dicts en `snake_case`; la conversión a `camelCase` ocurre **solo** en los esquemas Pydantic (`alias_generator=to_camel`).
- Pool con `psycopg_pool.AsyncConnectionPool`. Si la conexión pasa por el *transaction pooler* de Supabase, desactiva las sentencias preparadas.

## 6. Base de datos: recorte del esquema validado

`../docs/referencia/esquema.sql` está **validado** (PostgreSQL 16 + PostGIS 3.4). **Pártelo en las migraciones del prototipo** aplicando exactamente estos cambios (no reescribas lo que no se menciona):

**Conservar** extensiones `postgis`, `pg_trgm`, `unaccent`, `btree_gist`; la función `normalizar_texto`; las tablas `empresa`, `perfil_usuario`, `ruta`, `ruta_trazado`, `paradero`, `ruta_paradero`, `hito`, `servicio_ruta`, `horario`, `frecuencia`, `buseta`, `conductor`, `rodamiento`, `turno`, `credencial_fuente_gps`, `posicion_buseta`, `aviso`, `aviso_afecta`, `favorito`, `alerta_llegada`, `evento_uso`, `parametro_global`; sus restricciones, disparadores e índices; y las funciones `rutas_cercanas`, `paraderos_cercanos`, `paradero_mas_cercano_a_ruta`, `rutas_por_hito`, `progreso_en_ruta`, `progreso_paradero`, `turno_vigente`, `guardar_posicion`, `reemplazar_paraderos_de_ruta`, `estadisticas_uso`.

**Eliminar** las tablas `permiso_rol`, `dia_festivo`, `asignacion` (con `ux_asignacion_vigente` e `ix_asignacion_buseta`), `suscripcion_push`, `notificacion` (con `ix_notificacion_user`) e `importacion`; los tipos `tipo_importacion`, `estado_importacion`, `canal_notificacion`, `estado_notificacion`; las funciones `tipo_de_dia` y `limpiar_eventos_uso`; y los parámetros semilla `max_filas_excel`, `tamano_max_excel_mb`, `radio_transbordo_m`, `retencion_eventos_dias`. Quita también sus líneas de RLS.

**Modificar:**
1. `eliminar_ruta_con_asignaciones` → renómbrala `dar_de_baja_ruta`: quita la actualización de `asignacion`; conserva la baja de la ruta, la cancelación de turnos futuros y la baja de los servicios. Cuando haya turnos futuros y no venga `confirmar`, la decisión es del caso de uso (consulta antes con un `select`).
2. `alerta_llegada`: `usuario_id` pasa a admitir `null`; añade `telegram_chat_id bigint`; añade `check ((usuario_id is not null) <> (telegram_chat_id is not null))`; reemplaza `ux_alerta_unica` por dos índices únicos parciales (uno por `usuario_id`, otro por `telegram_chat_id`), ambos con `where estado <> 'desactivada'`.
3. `tg_*_act` y demás disparadores: sin cambios.

Archivos: `0001_extensiones_y_tipos.sql`, `0002_tablas.sql`, `0003_indices_y_funciones.sql`, `0004_seguridad.sql`, `0005_parametros.sql`. Los frontends **no** leen tablas: solo usan Supabase para Auth (el backend entra con la cadena de conexión y aplica la autorización).

`scripts/verificar_bd.py` debe comprobar y reportar: aplicar migraciones en limpio; `rutas_cercanas`, `progreso_en_ruta` (en circular), `turno_vigente` y `guardar_posicion` con datos semilla; violar a propósito la variante de variante, las franjas de frecuencia solapadas y un turno con buseta de otra empresa (debe fallar cada una). **Si algo de esto no funciona en Supabase, repórtalo; no lo maquilles.**

## 7. Servicios de dominio (la lógica que sí hay que probar)

Escribe cada uno **sin dependencias externas** y con pruebas unitarias antes del adaptador SQL.

- **CalculadorTipoDia**: festivo (lista de `FESTIVOS`) → `dom_festivo`; si no, lunes–viernes `lun_vie`, sábado `sabado`, domingo `dom_festivo`; hora de `America/Bogota`.
- **DeductorDeRuta**: `servicio_ruta_id` del turno **publicado** de esa buseta que contiene el instante (`hora_salida ≤ t ≤ hora_fin_estimada`; sin fin: salida + `duracion_estandar_min` o 120). Usa `turno_vigente` (SQL).
- **CalculadorEta** (rutas circulares). Por cada servicio activo de la ruta:
  1. Servicio `suspendido` → `no_disponible` ("El servicio está suspendido.").
  2. Tipo de día y `horario`. Sin horario para ese día → `no_disponible` con "Información pendiente de actualización". Hora fuera de `[primera_salida, cierre | ultima_salida + duración]` → `no_disponible` ("Aún no inicia el servicio." / "El servicio ya cerró.").
  3. Posiciones con edad ≤ `umbral_posicion_obsoleta_s`: `d = (progreso_paradero − progreso_buseta) mod longitud_circuito`; `v` = velocidad reportada si ≥ 5 km/h, si no `velocidad_default_kmh`; `eta = d / v`. Tomar la menor → `fuente: "gps"`.
  4. Sin posición fresca y con frecuencia en la franja actual → `fuente: "horario"`, `rango: 0…minutos_max × 60` y el mensaje de la sección 3 del contrato. Si una buseta perdió la señal, agregar "Esté pendiente de la siguiente buseta".
  5. Sin frecuencia → `no_disponible` ("Frecuencia no informada por la empresa.").
- **EvaluadorAlertas**: para cada alerta activa del par ruta/paradero, calcula `d` como arriba para cada buseta con posición fresca; dispara si `d ≤ distancia_aviso_m` y pasó `enfriamiento_alerta_min` desde `ultima_notificacion_en`. Una buseta que acaba de pasar el paradero tiene `d ≈ longitud` (no dispara). Si `desvio_m > umbral_desvio_m`, notifica **una vez por episodio** el cambio de estado: mensaje «La buseta N se desvió de su recorrido. Tu llegada puede cambiar.», por Telegram (alertas con `telegram_chat_id`) y por `/ws/notificaciones` con `tipo: "alerta_desvio"` (alertas de usuario). El episodio termina cuando la buseta vuelve a `desvio_m ≤ umbral_desvio_m`. Cubre SPEC-009 (D-P14).
- **ValidadorRodamiento**: advertencias `solapamiento_buseta` y `solapamiento_conductor` comparando intervalos `[hora_salida, hora_fin_estimada | salida + duración]`; verifica que servicio, buseta y conductor sean de la empresa del rodamiento (si no → `ErrorNoEncontrado`). Guardar borrador permite advertencias; **publicar** con advertencias → `ErrorConflictoNegocio` con la lista.
- **PoliticaDeAvisos**: jefe → origen `empresa` (con su `empresa_id` y solo rutas de su empresa), Secretaría → `movilidad`, administrador → `aplicativo`; cuerpo no vacío y ≤ `longitud_max_aviso`.
- **PlanificadorViaje** (solo directas): resuelve origen y destino a coordenadas (hito o punto); paraderos a ≤ `radio_caminata_m` de cada uno; para cada servicio activo y en horario cuya ruta tenga ambos paraderos: `bus = (progreso_destino − progreso_origen) mod L / velocidad_default`, `espera = frecuencia_max / 2`, `caminata = metros / 80 por minuto`; ordena por `total` y corta en `max_opciones_viaje`. Una ruta compartida da una opción por empresa. Sin opciones: `motivo` y `paraderoMasCercano`.

## 8. Simulador de GPS (`herramientas/simulador_gps.py`)

Comportamiento exacto en `../docs/01-alcance-y-datos-simulados.md` §4. Implementación:

- Tarea asíncrona iniciada en el *lifespan* solo si `MODO_DEMO=true`.
- Carga cada trazado como lista de puntos (`st_asgeojson`), precalcula distancias acumuladas con *haversine* y avanza cada buseta `v × dt` por el circuito (con módulo). Repártelas a distancias distintas al iniciar.
- Cada ciclo arma el mismo lote que enviaría un GPS real y llama a `registrar_posiciones` (no por HTTP). `POST /ingesta/posiciones` existe y se prueba con una clave de empresa creada desde el panel; es la puerta futura.
- Usa `PuertoReloj` (nunca `datetime.now()` directo) para que `fijar_hora` funcione.
- Estado de escenarios en memoria (`EstadoDemo`), expuesto por `ejecutar_escenario_demo` / `consultar_estado_demo`.
- Al iniciar con `MODO_DEMO`, `cargar_semillas` (o un paso de arranque) asegura el rodamiento publicado de **hoy** y el borrador de mañana con solapamiento (ver doc 01 §2.7), y carga el uso histórico simulado si `evento_uso` está vacía (doc 01 §2.9).

## 9. WebSocket y eventos

`registrar_posiciones` emite `posicion.aceptada`; suscriptores en `composicion.py`: el difusor WebSocket (`/ws/rutas/{rutaId}`) y `evaluar_alertas_por_posicion` (que llama a `PuertoNotificador`, con adaptadores Telegram y `/ws/notificaciones`). Mantén un gestor de conexiones por ruta y por usuario; limpia conexiones caídas; no bloquees el ciclo de posiciones si un cliente es lento. Una sola instancia (límite documentado: no escala horizontalmente).

## 10. Bot de Telegram (`adaptadores_externos/bot_telegram.py`)

Arranca en el *lifespan* si existe `TELEGRAM_BOT_TOKEN`, en modo *polling*, y **solo llama a casos de uso** (nunca a SQL). Flujos, textos y botones: `../docs/referencia/mockup-chatbot-telegram.html/.png` y la skill `busetasapp-telegram-bot`.

- `/start`: saludo + menú (Rutas cerca de mí · ¿Cuándo llega? · Horarios · Avisos · Ayuda).
- **Rutas cerca de mí**: pedir ubicación con botón de ubicación; consultar `consultar_rutas_cercanas` (radio 500 m); lista "Ruta X · paradero a N m"; botones "Ver ruta" y "¿Cuándo llega?". La ubicación vive solo en memoria del chat (≤ 10 min); **no se guarda**.
- **¿Cuándo llega?**: usa `calcular_eta_paradero`; con GPS: "Próxima buseta en N min · Según el GPS · actualizado hace N s"; sin GPS: aviso amarillo "Sin señal GPS en este momento. Te doy un estimado por horario: sale cada N min aprox."
- **Avisarme cuando esté cerca**: crea alerta con `telegram_chat_id`; confirma "Listo, te aviso cuando la <empresa/ruta> esté a 300 m de tu paradero." Cuando se dispara, el bot escribe primero; si la buseta se desvía, también escribe primero: «⚠️ La buseta N se desvió de su recorrido. Tu llegada puede cambiar.» (una vez por episodio).
- **Horarios** y **Avisos**: por ruta, y avisos vigentes.
- **Ayuda / "cómo funciona"**: explica en pocas líneas qué hace BusetasApp, cómo usar el bot, que los datos son de ejemplo, y los 4 roles.
- **Texto libre**: coincidencia por palabras clave sin acentos (hitos, nombres de ruta, "horario", "cuándo llega", "avisos", "ayuda"); ejemplo del mockup: «¿Qué ruta va a Villamaría?» → rutas que pasan por ese hito/ruta. Sin coincidencia → menú. **Sin LLM** (gratis y determinista).
- Siempre incluir "Datos de ejemplo" en `/start` y `/ayuda`.

## 11. Autorización

- Dependencias FastAPI `identidad_opcional`, `requiere_rol(*roles)`; la **autorización real vive en el caso de uso** (recibe `Identidad`), no solo en el router.
- Matriz: `../docs/03-contrato-api.md` §2. El jefe nunca recibe `empresa_id` por parámetro; recurso de otra empresa → 404.
- CORS con lista blanca (`CORS_ORIGENES`); la app móvil no usa CORS. Limitar peticiones solo si queda tiempo (no es del prototipo).
- `X-Id-Peticion` en cada respuesta; errores internos sin trazas al cliente.

## 12. Pruebas mínimas obligatorias

`pytest` desde `backend/`. Unitarias con repositorios en memoria y reloj fijo:

| Componente | Casos |
|---|---|
| CalculadorEta | 1000 m a 20 km/h → 180 s; velocidad 0 usa la por defecto; dos busetas toma la más cercana; circular (longitud 10 000 m, buseta en 9 500 m, paradero en 500 m → 1000 m → 180 s); posición vieja → respaldo; sin frecuencia; fuera de horario; suspendido; sábado sin horario |
| DeductorDeRuta | turno vigente; buseta con dos turnos (cambia de ruta); fuera de turno → `None` |
| EvaluadorAlertas | entra en distancia; enfriamiento; ya pasó; desvío |
| ValidadorRodamiento | solapamiento de buseta; de conductor; turnos consecutivos sin solape; recurso de otra empresa; reemplazo de buseta/conductor en un turno existente sin `confirmarReemplazo` (409) |
| CalculadorTipoDia | lunes, sábado, domingo, festivo entre semana |
| PoliticaDeAvisos | origen por rol; vacío; demasiado largo |
| PlanificadorViaje | directa; sentido (circular); ruta compartida → dos opciones; fuera de horario |
| Versión optimista | versión distinta → `ErrorConflictoVersion` |

Integración (marca `@pytest.mark.integracion`, contra la BD de desarrollo): `/salud`, `rutas/cercanas`, `rutas/{id}`, ETA con simulador corriendo, flujo rodamiento (borrador con advertencia → corregir → publicar), eliminar ruta con confirmación, aislamiento entre jefes de dos empresas, 401/403/404/409.

## 13. Orden de construcción

1. **B0 Contrato primero:** proyecto, `nucleo/`, configuración, `/salud`, `composicion.py`, y **todos los routers declarados** con sus esquemas Pydantic y respuesta `501 PENDIENTE` donde falte lógica. Ejecuta `scripts/exportar_openapi.py` y publica `../contrato/openapi.json` para los frontends.
2. **B1 Datos:** migraciones, `generar_trazados.py`, `geocodificar_hitos.py`, `cargar_semillas.py`, `crear_usuarios_demo.py`, `verificar_bd.py`.
3. **B2 Consulta pública** (rutas, detalle, horarios, frecuencias, búsqueda, hitos, avisos GET, eventos de uso).
4. **B3 Tiempo real:** `registrar_posiciones`, simulador, ingesta HTTP, WebSocket, ETA, panel de demo, reloj simulado.
5. **B4 Operación y avisos por rol** (busetas, conductores, horarios, rodamientos, publicar).
6. **B5 Movilidad y administración** (rutas/paraderos con versión, usuarios, empresas, claves GPS, parámetros, estadísticas).
7. **B6 Pasajero:** favoritos, alertas, planificación.
8. **B7 Bot de Telegram.**
9. **B8 Pruebas, pulido y actualización del contrato.**

Después de cada bloque: ejecuta las pruebas, actualiza `../docs/03-contrato-api.md` si cambió algo, y haz un commit.

## 14. Qué NO hacer

- No agregar Excel, Web Push, geocodificación en tiempo de ejecución, transbordos, ni un LLM.
- No exponer `SUPABASE_SERVICE_ROLE_KEY`; no registrar tokens ni coordenadas del pasajero.
- No inventar endpoints ni columnas: lo no previsto va como `PENDIENTE(decisión)` y se reporta.
- No usar `datetime.now()` fuera de `PuertoReloj`.
