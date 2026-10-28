# Alcance del prototipo y datos simulados

## 1. Principio

Si un dato no existe todavía (posiciones GPS, trazados oficiales, paraderos oficiales), **se simula con reglas claras y se etiqueta**. Si el dato salió del levantamiento de campo (horarios, frecuencias, números laterales 2683 y 2676, hitos), **se usa tal cual**. Nada se presenta como oficial.

## 2. Semilla de datos (generada por `backend/scripts/`)

### 2.1 Empresas

| Empresa | GPS simulado | Nota |
|---|---|---|
| Sideral | Sí | Fuente: `campo-sideral.md` |
| Socobuses | Sí | Fuente: `campo-socobuses.md` (GPS en toda la flota) |
| Serviturismo | **No** (señal ausente por defecto) | Fuente: `campo-serviturismo.md` ("algunas unidades con GPS", seguimiento por planilla). Muestra el respaldo por horario |

### 2.2 Rutas (todas circulares, D-P02)

| Ruta | Servicios (empresa · código público) | Origen del dato |
|---|---|---|
| **El Cable** | Sideral · **39** | Código y frecuencia reales (campo). El recorrido es de ejemplo |
| **Centro** | Sideral · **22** | Código y frecuencia reales (campo). Recorrido de ejemplo |
| **La Enea** | Socobuses · 18 *(ficticio)* y Serviturismo · *sin código* | Ruta compartida real; código 18 ficticio; Serviturismo no tiene código (campo) |
| **Villamaría** *(obligatoria: las SPECs la dejan dentro del alcance, «Manizales y Villamaría»)* | Serviturismo · *sin código* y Socobuses · 21 *(ficticio)* | Operada por ambas en campo; código ficticio |

No se simulan San Sebastián/Ansebas ni Bosques de La Enea (variante) en el prototipo. El modelo ya las soporta; se omiten por tiempo.

**Trazados (D-P10):** los genera `scripts/generar_trazados.py` llamando **una sola vez** a un servicio de rutas de OpenStreetMap (OSRM) con una lista ordenada de hitos como puntos de paso y cerrando el circuito. Guarda `backend/supabase/semillas/trazados/<ruta>.geojson`. **El equipo debe revisar cada GeoJSON en un mapa** (por ejemplo pegándolo en geojson.io) antes de aprobarlo. Si OSRM no responde, el agente debe pedir el archivo al usuario, no inventar coordenadas.

Orden de puntos de paso sugerido (de los mockups; coordenadas por geocodificar y validar):
- El Cable: Terminal → Carrera 23 → Fundadores → El Cable → (regreso al inicio).
- Centro: Terminal → Catedral → Parque de Caldas → Fundadores → (regreso).
- La Enea: Fundadores → Carrera 23 → barrio La Enea → (regreso).
- Villamaría: Terminal → entrada a Villamaría → (regreso). **Obligatoria.** Si OSRM no entrega un trazado razonable, no la omitas en silencio: repórtalo como `PENDIENTE(decisión)` para que el equipo lo corrija a mano.

### 2.3 Hitos (búsqueda prioritaria)

Catedral, El Cable, Carrera 23, Fundadores, Terminal, Parque de Caldas (nombres tomados de los documentos de campo). Las coordenadas se obtienen con `scripts/geocodificar_hitos.py` (Nominatim/OpenStreetMap, ≤ 1 petición por segundo, con `User-Agent` propio) y **el equipo las valida**. Referencia de sanidad (aproximada, a verificar): la Catedral queda cerca de 5.069° N, 75.517° O. Cada hito guarda alias (`catedral`, `la catedral`, `cable`, …).

### 2.4 Paraderos (ficticios)

Los puntos de paso de cada ruta (hitos) son paraderos con el nombre del hito. Además, `generar_trazados.py` crea paraderos intermedios cada ~400 m sobre el trazado llamados `Paradero <ruta> <n>`, marcados `ficticio`. Cada ruta debe quedar con entre 6 y 12 paraderos ordenados (`ruta_paradero.orden`).

### 2.5 Horarios y frecuencias

Datos de campo (`campo-*.md`), por servicio:

| Servicio | `lun_vie` | `sabado` | `dom_festivo` | Frecuencia |
|---|---|---|---|---|
| Sideral · El Cable (39) | 04:45 – 21:30 | **sin dato (a propósito, "información pendiente de actualización")** | 06:00 – 21:00 | 8–10 min |
| Sideral · Centro (22) | 04:45 – 21:30 | sin dato | 06:00 – 21:00 | ~15 min |
| Socobuses · La Enea (18) | primera 05:30, última 22:00, cierre 23:00 | igual que `lun_vie` (capacidad plena L–S) | igual horario; frecuencia **15 min *(ficticia; en campo solo se sabe que opera al ~40 %)*** | 6 min |
| Socobuses · Villamaría | igual que La Enea | igual | igual | 10 min en horas alta, 15 en valle *(franjas ficticias: 06:00–10:00 y 16:30–20:00 alta)* |
| Serviturismo · La Enea y Villamaría | 04:40 – 22:00 | igual | 04:40 – 21:00 | 4 min |

### 2.6 Busetas y conductores (simulados)

| Buseta (número lateral) | Empresa | Ruta(s) | Origen |
|---|---|---|---|
| 1520 | Sideral | El Cable por la mañana, Centro por la tarde | Ficticio (mockups) |
| 1544 | Sideral | El Cable | Ficticio |
| 1388 | Sideral | Centro | Ficticio |
| 3101 | Socobuses | La Enea | Ficticio |
| 3102 | Socobuses | Villamaría por la mañana (04:30–14:00), La Enea por la tarde (14:00–23:30) | Ficticio. Decisión del equipo: da una buseta con GPS a Socobuses · Villamaría |
| **2683** | Serviturismo | La Enea | **Real** (campo) |
| **2676** | Serviturismo | Villamaría | **Real** (campo) |

Conductores ficticios por empresa (≥ 3): p. ej. Carlos R., Marta L., Julián P. (Sideral). Solo `nombre` y `codigo` opcional.

### 2.7 Rodamientos de la semilla

- **Rodamiento de hoy, publicado**, regenerado en cada arranque de `MODO_DEMO` con la fecha actual: un turno de 04:30 a 23:30 por buseta (1520 tiene dos turnos: 05:00–13:00 El Cable y 13:00–22:00 Centro). Así `turno_vigente` siempre devuelve la ruta correcta en horario de clase.
- **Rodamiento de mañana de Sideral, en borrador, con un solapamiento deliberado**: buseta 1520 con turno 06:00–06:50 en El Cable y otro que sale a las 06:40 en Centro (igual que el mockup). Sirve para el paso 3 del guion.

### 2.8 Avisos de ejemplo

Uno de origen `empresa` (Sideral, "Horario de festivo"), uno `movilidad` ("Cierre por obras en la carrera 23", afecta El Cable) y uno `aplicativo` ("Prototipo con datos de ejemplo").

### 2.9 Uso histórico simulado (para estadísticas, HU-J06)

Sin esto, la gráfica del jefe saldría vacía en la clase. `cargar_semillas` inserta, **solo si `evento_uso` está vacía**, eventos anónimos de los **últimos 14 días** (consulta de ruta, de horario, de ETA y de paradero):
- Reparto por ruta con pesos distintos (El Cable > Centro > La Enea > Villamaría) y por empresa, para que cada jefe vea solo lo suyo.
- Perfil diario con picos de 06:00 a 08:00 y de 17:00 a 19:00; menos volumen sábado y domingo. Orden de magnitud: decenas de eventos por ruta y día. Cifras de ejemplo, **no** datos reales.
- Usa las columnas que ya tiene `evento_uso` en el esquema recortado. Si no hay forma de distinguir un evento simulado de uno real, **no modifiques la tabla**: repórtalo como `PENDIENTE(decisión)`.
- Es idempotente: reiniciar el backend no duplica los eventos.

## 3. Historias de usuario: qué entra

Estado: ✅ completa · 🟡 reducida · ❌ fuera del prototipo.

| HU | Descripción corta | Estado | Cómo queda en el prototipo |
|---|---|---|---|
| P01 | Ver rutas y paradas en el mapa | ✅ | Radio de búsqueda por parámetro; sin rutas cerca → paradero más cercano |
| P02 | Ver recorrido de una ruta | ✅ | Trazado + paraderos ordenados; ruta con varias empresas → chips por empresa |
| P03 | Horarios y días | ✅ | Sábado de Sideral muestra "Información pendiente de actualización" |
| P04 | Frecuencia por franja | ✅ | Rango "De 10 a 15 min" |
| P05 | Ubicación en tiempo real | ✅ | WebSocket + respaldo REST; estado `sin_senal` |
| P06 | ETA a una parada | ✅ | `gps` o `horario` o `no_disponible` |
| P07 | Planificar viaje | 🟡 | Solo directas (D-P07), origen/destino por mapa o hito |
| P08 | Buscar por número/nombre | ✅ | Sin distinguir tildes |
| P09 | Buscar por hito/barrio | ✅ | Hitos con alias; sin cobertura → paradero más cercano |
| P10 | Favoritas | ✅ | Requiere sesión |
| P11 | Alerta de llegada | 🟡 | Telegram (por `chat_id`) y evento WebSocket con la app abierta (D-P08, D-P09). **También avisa si la buseta se desvía** (SPEC-009, D-P14) |
| P12 | Usar sin cuenta | ✅ | Todo lo público sin token |
| J01 | Asignar buseta y conductor | 🟡 | Asignar = agregar un turno al rodamiento en borrador; sin tabla de asignaciones. **Si el turno ya tenía buseta/conductor, pide confirmación para reemplazar** (D-P15) |
| J02 | Datos operativos | 🟡 | Editar horarios y frecuencias de su empresa, crear busetas y conductores. **No crea rutas** (BR-03 manda sobre el texto de HU-J02; D-P13) |
| J03 | Subir Excel | ❌ | Botón visible y desactivado: "No incluido en el prototipo" |
| J04 | Rodamiento y solapamientos | ✅ | Guardar borrador con advertencias; publicar bloqueado con solapamientos |
| J05 | Avisos de empresa | ✅ | Límite de caracteres por parámetro |
| J06 | Estadísticas de uso | 🟡 | Consultas por ruta y día de su empresa, con gráfica simple. **La demo trae 14 días de uso simulado** (§2.9) |
| SM01 | Registrar ruta y asignarla | 🟡 | Trazado = línea que une los paraderos elegidos, en orden (simplificado) |
| SM02 | Editar ruta | ✅ | Con control de versión |
| SM03 | Eliminar ruta | ✅ | Advertencia si hay turnos futuros; `confirmar=true` |
| SM04 | Gestionar paraderos | ✅ | Duplicado a < 20 m con el mismo nombre → aviso |
| SM05 | Cambio de movilidad | ✅ | Aviso origen `movilidad` con rutas afectadas |
| A01 | Usuarios | ✅ | Crear, activar/desactivar, asignar rol y empresa |
| A02 | Roles y permisos | 🟡 | Los 4 roles son fijos; pantalla de solo lectura |
| A03 | Empresas y fuentes GPS | ✅ | Claves visibles una sola vez; revocar |
| A04 | Parámetros | ✅ | Con mínimo y máximo |
| A05 | Avisos del aplicativo | ✅ | — |

Extras exclusivos del prototipo: **Panel de demo** (admin), **reloj simulado**, **ajustes de servidor** en la app.

### 3.1 Textos de los flujos alternativos (SPEC-001, 003, 006)

| Caso | Dónde | Texto / comportamiento |
|---|---|---|
| HU-P05: no hay busetas en la ruta | App (mapa de la ruta) | «No hay busetas en servicio en esta ruta en este momento.» Si la hora está fuera del horario: «El servicio de esta ruta ya cerró» o «aún no inicia; sale a las 04:45». Usa `seguimientoDisponible` y las unidades que ya devuelve `GET /rutas/{id}/busetas` |
| HU-P05: señal perdida | App y bot | «Ubicación no disponible. Última señal hace más de 60 s.» (ya definido en el contrato) |
| HU-P02: la ruta no existe (404 o búsqueda sin coincidencia) | App | «No encontramos esa ruta. Estas rutas cercanas podrían servirte:» y lista de `GET /rutas/cercanas`; si el usuario escribió un destino que es un hito, `GET /hitos/{id}/rutas` |
| HU-J01: el turno ya tenía asignación | Panel del jefe | Modal: «La ruta ya tiene asignada la buseta 1520 a las 06:00. ¿Reemplazarla por la 1544?» con **Reemplazar** y **Cancelar**. La API responde 409 `CONFLICTO_NEGOCIO` hasta recibir `confirmarReemplazo=true` |
| HU-P11: la buseta se desvía | Bot y app | «La buseta 1544 se desvió de su recorrido. Tu hora de llegada puede cambiar.» Una vez por episodio de desvío |

## 4. Simulador de GPS (comportamiento exigido)

- Corre dentro del backend cuando `MODO_DEMO=true`; una tarea asíncrona mueve cada buseta a lo largo del trazado de su turno vigente.
- Velocidad base configurable (`SIM_VELOCIDAD_KMH`, por defecto 35) con variación ±5 km/h; emite posición cada `SIM_INTERVALO_S` (por defecto 3 s). Reporta `velocidadKmh` y `rumbo` coherentes.
- Las busetas de **Serviturismo no emiten** salvo que el administrador active su GPS.
- Escenarios (Panel de demo): `perder_senal` (una buseta o una empresa), `restaurar_senal`, `desvio` (se aparta del trazado > `umbral_desvio_m` y vuelve), `fijar_hora` (reloj simulado), `acelerar`, `reiniciar_simulacion`, `activar_gps_empresa`.
- Dos busetas en la misma ruta deben distanciarse en el circuito (no salir pegadas).
- El escenario `desvio` debe provocar el aviso `alerta_desvio` a quien tenga una alerta activa en esa ruta (D-P14). Es la forma de mostrarlo en la demo.
- Si la hora simulada queda fuera del horario del servicio, el simulador no mueve esa buseta y el ETA responde "el servicio ya cerró" / "aún no inicia".

## 5. Cuentas de demostración

| Correo | Rol | Empresa |
|---|---|---|
| `admin@busetasapp.example` | administrador | — |
| `movilidad@alcaldia.example` | secretaria_movilidad | — |
| `jefe@sideral.example` | jefe_operaciones | Sideral |
| `jefe@socobuses.example` | jefe_operaciones | Socobuses |
| `pasajera@correo.example` | pasajero | — |

Se crean con `backend/scripts/crear_usuarios_demo.py` (API administrativa de Supabase Auth). Las contraseñas vienen de variables de entorno.

## 6. Supuestos pendientes de aprobación

1. Los recorridos de El Cable, Centro, La Enea y Villamaría son **ilustrativos**; no son los recorridos oficiales.
2. La frecuencia de domingos/festivos de Socobuses (15 min) y las franjas alta/valle de Villamaría son valores de ejemplo.
3. Un solo jefe por empresa en la demo (S-11); la cuenta de Socobuses sirve para mostrar el aislamiento entre empresas.
