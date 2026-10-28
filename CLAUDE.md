# BusetasApp Manizales — Prototipo de clase (instrucciones para TODOS los agentes)

> Léelo completo antes de escribir una sola línea. Después lee el `CLAUDE.md` de tu carpeta (`backend/`, `web-admin/` o `mobile/`).
> Este archivo manda sobre cualquier otro documento. Si dos documentos se contradicen, gana el orden: **este archivo → `docs/00..04` → `docs/referencia/`**.

## 1. Qué estamos construyendo

BusetasApp es una app para consultar rutas, horarios y llegada de busetas en Manizales. **Esto es un PROTOTIPO para presentar en clase.** No existe convenio con ninguna empresa, así que **no hay coordenadas GPS reales**: las busetas, sus posiciones, los horarios y los paraderos son **simulados** (ver `docs/01-alcance-y-datos-simulados.md`). Todo lo que se muestre debe verse y comportarse como real, pero estar etiquetado como "Datos de ejemplo".

Componentes (un solo repositorio, carpetas separadas):

| Carpeta | Qué es | Quién lo usa | Tecnología (decidida en la presentación) |
|---|---|---|---|
| `backend/` | API REST + WebSockets + simulador de GPS + bot de Telegram | todos | Python, FastAPI, Supabase (Postgres + PostGIS + Auth) |
| `web-admin/` | Paneles de escritorio de 3 roles | Jefe de operaciones, Secretaría de Movilidad, Administrador | Next.js (TypeScript) |
| `mobile/` | App del pasajero (se instala como APK) | Pasajero | Flutter (Android) |
| Bot de Telegram | Vive dentro de `backend/` (adaptador externo) | Pasajero | python-telegram-bot, modo *polling* |
| `docs/` | Contexto, contrato de API, diagramas, referencia | agentes y equipo | Markdown |

Mapas: **OpenStreetMap** (gratis, sin cuenta ni token). Flutter: `flutter_map`. Web: `react-leaflet`. La URL de teselas va en una variable de entorno para poder cambiarla.

## 2. Reglas de oro (evitan alucinaciones)

1. **No inventes.** Si algo no está en `docs/` (endpoint, tabla, columna, parámetro, dependencia, pantalla), no lo crees. Déjalo como `# PENDIENTE(decisión): <qué falta>` (o `// PENDIENTE(decisión): …`) y repórtalo en tu resumen final.
2. **No agregues dependencias** que no estén en tu `CLAUDE.md` sin dejar constancia en `docs/decisiones-agentes.md` (qué, por qué, licencia gratuita). Todo debe ser **gratuito o de código abierto**.
3. **Versiones:** al inicializar el proyecto instala la versión estable vigente y **fíjala** (`pyproject.toml`, `package.json`, `pubspec.yaml`). No asumas versiones de memoria; ante duda consulta la documentación oficial.
4. **Nunca inventes datos reales.** Los datos son de ejemplo y deben marcarse como tales. Excepción: los datos operativos tomados del levantamiento de campo (`docs/referencia/campo-*.md`) se usan tal cual y se citan en `docs/01-alcance-y-datos-simulados.md`.
5. **Secretos:** `.env` jamás se sube al repositorio. Solo `.env.example` con nombres de variables y valores falsos. `SUPABASE_SERVICE_ROLE_KEY` **nunca** llega a `web-admin/` ni a `mobile/`.
6. **Cada agente edita solo su carpeta** (ver §7). Si necesitas un cambio en otra carpeta, escríbelo en `docs/solicitudes-entre-agentes.md` y sigue con un mock.
7. **El contrato manda:** `docs/03-contrato-api.md` define los endpoints. Solo el agente de backend lo modifica, y lo hace en el mismo commit que cambia el código. Los frontends no llaman nada que no esté ahí.
8. **Termina cada tarea con un reporte corto:** qué hiciste, qué probaste (con el comando), qué quedó `PENDIENTE`, qué supuestos tomaste.

## 3. Roles y reglas de negocio vigentes (4 roles)

El rol **conductor ya no existe** (ni módulo ni usuario). Los conductores son solo *datos* dentro del rodamiento. "Administrador de empresa" ahora se llama **Jefe de operaciones**.

| Rol (valor en BD) | Quién es | Puede | No puede | Dónde lo usa |
|---|---|---|---|---|
| `pasajero` | Usuario final. **Puede usar la app sin cuenta.** | Consultar rutas, horarios, mapa, ETA, buscar, planificar. Con cuenta: favoritos y alertas de llegada | Modificar datos operativos | App Flutter, Telegram |
| `jefe_operaciones` | Responsable de **una** empresa | Asignar buseta+conductor a rutas **ya asignadas a su empresa**, armar y publicar el rodamiento, editar horarios/frecuencias de su empresa, publicar avisos de su empresa, ver estadísticas de su empresa | Crear/editar/eliminar rutas o paraderos; ver datos de otra empresa | Web (escritorio) |
| `secretaria_movilidad` | Autoridad que alimenta la base de datos | Crear/editar/eliminar rutas y paraderos, **asignar rutas a cada empresa**, registrar cambios de movilidad (cierres, desvíos, obras) | Definir rodamientos o asignaciones diarias | Web (escritorio) |
| `administrador` | Dueño de la plataforma (el desarrollador). Control total | Todo lo de gestión + usuarios, roles, empresas, parámetros, claves de fuentes GPS, avisos del aplicativo, **panel de demo** | — | Web (escritorio) |

Reglas de negocio (de `docs/referencia/contexto-busetasapp.md`):
- **BR-01** Consultar rutas, horarios y mapa no exige cuenta.
- **BR-02** Favoritos y notificaciones exigen usuario registrado (en Telegram el `chat_id` hace de identidad: decisión **D-P08**, §5).
- **BR-03** El jefe solo asigna rutas ya registradas y define el rodamiento; no toca rutas ni paraderos.
- **BR-04** Solo la Secretaría crea/edita/elimina rutas, paraderos y cambios de ciudad, y es quien impone las rutas a cada empresa.
- **BR-05** Solo el jefe publica avisos de su empresa. Los cambios de ciudad los publica la Secretaría (origen `movilidad`); el administrador publica con origen `aplicativo`.
- **BR-06** Los conductores no tienen acceso a la plataforma.
- **BR-07** El administrador tiene control total.
- **BR-08** Rutas, paraderos y cambios de ciudad vienen de la Secretaría (en el prototipo, de la semilla simulada).

## 4. Arquitectura: hexagonal ligera sobre un monolito modular

Regla de dependencias (aplica a `backend/`; el resto sigue la idea de "la lógica no depende del framework"):

```text
dominio          -> (nada: ni FastAPI, ni psycopg, ni Pydantic, ni Supabase)
aplicacion       -> dominio
infraestructura  -> aplicacion, dominio
composicion.py   -> todo (único lugar que crea adaptadores y los inyecta)
```

- Un **caso de uso = una función o clase pequeña** con sus puertos inyectados; recibe y devuelve datos simples (dataclasses/DTO), no conoce HTTP.
- Los **controladores** solo traducen HTTP ↔ caso de uso. Sin reglas de negocio.
- **Puertos de salida** (interfaces): repositorios, autenticación, reloj, emisor de eventos, notificador de Telegram, fuente de posiciones.
- Un módulo no importa archivos internos de otro módulo; usa su `__init__.py` (API pública).

El detalle y el árbol de carpetas están en `backend/CLAUDE.md`.

## 5. Decisiones del prototipo (resuelven huecos; el equipo puede cambiarlas)

| ID | Decisión | Motivo |
|---|---|---|
| D-P01 | Stack: el de la presentación (Python/FastAPI, Flutter, Next.js, bot Telegram, WebSockets, Supabase, OpenStreetMap). El informe de arquitectura v2 y la Actividad 5 hablaban de Node/Express: **quedan obsoletos en lo tecnológico** (el diseño de módulos y reglas sigue vigente) | La presentación es lo aprobado por el equipo |
| D-P02 | **Todas las rutas del demo son circulares** (sentido único `circular`). El formulario "Registrar ruta" de la Secretaría solo crea circulares | Serviturismo opera rutas circulares (campo). Evita ida/vuelta y simplifica el ETA (distancia módulo la longitud del circuito) |
| D-P03 | Las posiciones las genera un **simulador interno** del backend (`MODO_DEMO=true`) que mueve busetas por los trazados y llama al mismo caso de uso `registrar_posiciones` que usaría un GPS real. El endpoint HTTP de ingesta existe y funciona, pero el demo no depende de él | No hay convenio; el dominio no cambia cuando llegue un GPS real |
| D-P04 | Tiempo real por **WebSocket** (`/ws/rutas/{rutaId}`), con *polling* REST (`GET /rutas/{id}/busetas`) como respaldo | La presentación lo define; el respaldo evita que falle la demo |
| D-P05 | ETA con GPS; si no hay posición fresca, **respaldo por horario y frecuencia** (`fuente: horario`). Serviturismo se simula **sin GPS** a propósito (en campo casi no lo usa) para mostrar el respaldo | Mockup del chatbot (pantalla 3) y datos de campo |
| D-P06 | Fuera del prototipo: importación de Excel (HU-J03), Web Push / notificaciones con la app cerrada, transbordos en la planificación, geocodificación de texto libre (Nominatim), pruebas de carga, RLS fina | Tiempo; no aportan a la demostración |
| D-P07 | Planificación de viaje: **solo rutas directas**, origen/destino elegidos en el mapa o por hito | Evita servicios externos |
| D-P08 | En Telegram no hay cuentas: el `chat_id` identifica al usuario para alertas. En la app, favoritos y alertas exigen sesión (BR-02). Se documenta como desviación consciente de BR-02 | El mockup del bot permite "Avisarme" sin registrarse |
| D-P09 | Notificaciones de llegada: mensaje de Telegram + evento WebSocket a la app abierta. No hay bandeja persistente ni push en segundo plano | Alcance del prototipo |
| D-P10 | Los trazados salen de calles reales (servicio OSRM/OpenStreetMap) **una sola vez**, en el script de semillas, y se guardan como GeoJSON en el repo. El demo no llama a OSRM | Reproducible y sin depender de internet en clase |
| D-P11 | Tipo de día (`lun_vie`, `sabado`, `dom_festivo`) se calcula en Python con una lista corta de festivos en configuración; no hay tabla de festivos | Simplifica la BD |
| D-P12 | JSON en `camelCase`, BD en `snake_case`, hora local `America/Bogota`, fechas ISO 8601 con zona | Ya definido en la Actividad 6 |
| D-P13 | SPEC-006 se contradice: HU-J02 dice que el jefe «ingresa datos de rutas» y BR-03 dice que no puede crear ni editar rutas. **Manda BR-03**: el jefe edita horarios, frecuencias, busetas y conductores; las rutas las crea solo la Secretaría | Coherencia con BR-03/BR-04 |
| D-P14 | Las alertas de llegada también avisan si la buseta se desvía del trazado (una vez por episodio), por Telegram y por `/ws/notificaciones` | SPEC-009, flujo alternativo |
| D-P15 | Reemplazar la buseta o el conductor de un turno ya guardado exige confirmación (`confirmarReemplazo=true`) | SPEC-006, HU-J01 |
| D-P16 | Villamaría es una ruta obligatoria del demo | Las SPECs dejan «Manizales y Villamaría» dentro del alcance |

## 6. Convenciones comunes

- **Idioma:** todo en español (UI, mensajes de error, nombres de tablas, archivos, funciones). Código: identificadores en `snake_case` (Python/Dart: `lowerCamelCase` en Dart, `camelCase` en TS). Archivos Python en `snake_case.py`, web en `kebab-case`.
- **Errores de API:** `{ "error": { "codigo": "...", "mensaje": "...", "reintentable": false, "detalles": null } }`. Códigos: `VALIDACION` 400, `NO_AUTENTICADO` 401, `NO_AUTORIZADO` 403, `NO_ENCONTRADO` 404, `CONFLICTO_VERSION` 409, `CONFLICTO_NEGOCIO` 409, `SERVICIO_EXTERNO_NO_DISPONIBLE` 503, `ERROR_INTERNO` 500.
- **Control de versión optimista:** toda escritura sobre recursos editables lleva `version`; si no coincide, `409 CONFLICTO_VERSION`. La interfaz ofrece "Recargar".
- **Nunca registres en logs** tokens, cabecera `Authorization`, `X-Clave-Fuente`, correos ni coordenadas del pasajero. La ubicación del pasajero no se guarda.
- **Banner permanente** en todas las interfaces: "Datos de ejemplo · no son rutas oficiales".
- **Identidad visual** (de los mockups): verde `#0E7C66` acciones, amarillo `#F6C500` solo busetas en vivo, tinta `#13271E`, fondo `#EDF1EC`, rojo ladrillo solo errores. Tipografías Bricolage Grotesque (títulos) y Atkinson Hyperlegible (texto). Contraste ≥ 4.5:1, objetivos táctiles ≥ 44 px, la información nunca depende solo del color.

## 7. Propiedad de carpetas y trabajo en paralelo

| Agente | Edita | Lee (solo) |
|---|---|---|
| `backend-dev` | `backend/`, `docs/03-contrato-api.md`, `contrato/openapi.json` | todo `docs/` |
| `web-admin-dev` | `web-admin/` | `docs/`, `contrato/openapi.json` |
| `mobile-dev` | `mobile/` | `docs/`, `contrato/openapi.json` |

Flujo: (1) el agente de backend publica primero el **esqueleto del contrato** (`contrato/openapi.json` generado por FastAPI + datos semilla) → (2) los frontends generan sus clientes/tipos a partir de ese archivo y trabajan con datos simulados hasta que el backend responda → (3) integración. Una rama por agente: `feat/backend-*`, `feat/web-*`, `feat/mobile-*`. Commits pequeños en español: `feat(backend): ...`, `fix(mobile): ...`.

## 8. Definición de terminado (por funcionalidad)

- Hace lo que dice la historia en `docs/01-alcance-y-datos-simulados.md` §3 (incluidos los flujos alternativo y de error).
- Se probó con un comando o paso manual que dejaste escrito en tu reporte.
- Sin secretos ni datos personales en logs, sin `print` de depuración.
- Estados de UI: cargando, vacío, error de conexión, sin señal de la buseta, sin sesión.
- El contrato (`docs/03-contrato-api.md`) y el código coinciden.

## 9. Cuentas y datos de demostración

Ver `docs/01-alcance-y-datos-simulados.md` §5. Resumen: 3 cuentas de gestión (jefe de Sideral, Secretaría, administrador) y 1 pasajero, creadas en Supabase Auth por `backend/scripts/crear_usuarios_demo.py`. Contraseñas en `.env` (no en el repo).

## 10. Qué leer según tu tarea

| Tarea | Lee |
|---|---|
| Entender el producto y la demo | `docs/00-plan-prototipo-demo.md` |
| Datos simulados, historias incluidas y excluidas | `docs/01-alcance-y-datos-simulados.md` |
| Diagramas reducidos (ER, secuencias, arquitectura) | `docs/02-diagramas.md` |
| Endpoints y WebSocket | `docs/03-contrato-api.md` |
| Cómo correr todo y generar el APK | `docs/04-guia-ejecucion-y-apk.md` |
| Qué documento de referencia sigue vigente | `docs/referencia/LEEME.md` |
| Qué cumple cada SPEC, qué requisitos no funcionales se desvían a propósito | `docs/05-trazabilidad-specs-y-rnf.md` |
