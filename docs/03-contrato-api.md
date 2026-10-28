# Contrato de API del prototipo

> **Fuente de verdad para los tres proyectos.** Prefijo REST: `/api/v1`. JSON en `camelCase`. Errores y códigos: `CLAUDE.md` §6.
> Solo el agente de backend lo modifica, junto con el código. El archivo `contrato/openapi.json` lo genera FastAPI y debe coincidir con este documento.
> Los nombres y las formas siguen a `referencia/openapi.yaml`; aquí solo está lo que el prototipo implementa.

## 1. Autenticación

| Mecanismo | Quién | Cómo |
|---|---|---|
| Sin credencial | Cualquier persona | Endpoints marcados **público** (BR-01) |
| `Authorization: Bearer <JWT de Supabase Auth>` | pasajero, jefe, Secretaría, administrador | El backend valida el JWT con la configuración del proyecto Supabase (clave/JWKS vigente que indique su panel) y lee `rol` y `empresa_id` de `perfil_usuario`. Usuario inactivo → 401 |
| `X-Clave-Fuente: <clave>` | Fuente GPS de una empresa | Solo en `POST /ingesta/posiciones`. Se compara el hash SHA-256 |

El jefe **nunca** envía `empresaId`: sale del token. Un recurso de otra empresa responde **404**.

## 2. Endpoints REST

Leyenda de acceso: **P** público · **U** pasajero con sesión · **J** jefe · **S** Secretaría · **A** administrador. `A` es superconjunto de gestión, salvo ingesta y avisos (publica con origen `aplicativo`).

### 2.1 Consulta pública

| Método y ruta | Acceso | Descripción | HU |
|---|---|---|---|
| `GET /salud` | P | `{ "estado": "ok" }`, sin consultar la BD | — |
| `GET /rutas/cercanas?lat&lng&radioM?` | P | Rutas con trazado a menos de `radioM` (defecto: parámetro `radio_busqueda_m`). Si no hay: `rutas: []` + `paraderoMasCercano` | P01 |
| `GET /rutas` | P | Todas las rutas activas (resumen con servicios) | P01 |
| `GET /rutas/{rutaId}` | P | Detalle: trazado GeoJSON, paraderos ordenados, servicios, avisos vigentes | P02 |
| `GET /rutas/{rutaId}/horarios` | P | Horarios por servicio y tipo de día | P03 |
| `GET /rutas/{rutaId}/frecuencias` | P | Frecuencias por servicio, tipo de día y franja | P04 |
| `GET /rutas/{rutaId}/busetas` | P | Busetas activas de la ruta (respaldo REST del WebSocket) | P05 |
| `GET /paraderos/cercanos?lat&lng&radioM?&rutaId?` | P | Paraderos cercanos | P01 |
| `GET /paraderos/{paraderoId}/eta?rutaId&servicioId?` | P | ETA por servicio | P06 |
| `POST /viajes/planificar` | P | Opciones directas (máx. `max_opciones_viaje`) | P07 |
| `GET /busqueda/rutas?q` | P | Por nombre, código público o interno, sin tildes | P08 |
| `GET /busqueda/hitos?q` | P | Hitos, barrios y sectores con alias | P09 |
| `GET /hitos/{hitoId}/rutas` | P | Rutas a menos de `radio_hito_m`; sin cobertura → `cobertura:false` + paradero más cercano | P09 |
| `GET /avisos?rutaId?` | P | Avisos vigentes (empresa, movilidad, aplicativo) | J05, SM05, A05 |
| `GET /empresas` | P | Lista pública de empresas | — |

Cada consulta pública registra un `evento_uso` anónimo **sin bloquear** la respuesta (RD-17).

### 2.1.1 Perfil (cualquier usuario con sesión)

| Método y ruta | Descripción |
|---|---|
| `GET /yo` | `{ "usuarioId": "…", "correo": "…", "rol": "jefe_operaciones", "empresaId": "…", "empresaNombre": "Sideral" }` (`empresaId` y `empresaNombre` solo para el jefe). 401 si el token es inválido o el usuario está inactivo |

### 2.2 Pasajero con sesión (U)

| Método y ruta | Descripción | HU |
|---|---|---|
| `GET /favoritos` · `POST /favoritos` · `DELETE /favoritos/{id}` | Ruta **o** paradero; repetido → 200 con el existente; ruta dada de baja → `disponible:false` | P10 |
| `GET /alertas-llegada` · `POST /alertas-llegada` · `DELETE /alertas-llegada/{id}` | `{rutaId, paraderoId, distanciaAvisoM?}`; repetida → 409 `CONFLICTO_NEGOCIO` | P11 |

Sin sesión → 401 `NO_AUTENTICADO` con mensaje "Inicia sesión para guardar".

### 2.3 Jefe de operaciones (J)

| Método y ruta | Descripción | HU |
|---|---|---|
| `GET /mis-servicios` | Servicios de ruta de su empresa (los asignó la Secretaría) | J01 |
| `GET /busetas` · `POST /busetas` · `PUT /busetas/{id}` | De su empresa. Número lateral único por empresa | J02 |
| `GET /conductores` · `POST /conductores` · `PUT /conductores/{id}` | Solo `nombre` y `codigo` | J02 |
| `PUT /servicios/{servicioId}/horarios` · `PUT /servicios/{servicioId}/frecuencias` | Reemplaza con `version`; valida cierre ≥ última salida y franjas sin solape | J02 |
| `GET /rodamientos?desde&hasta` · `POST /rodamientos` · `GET /rodamientos/{id}` · `PUT /rodamientos/{id}` | Borrador con `advertencias`; si la petición cambia la buseta o el conductor de un turno ya guardado (mismo `servicioId` + `horaSalida`) y no trae `confirmarReemplazo=true` → 409 `CONFLICTO_NEGOCIO` con la lista de turnos afectados (D-P15); fecha entre hoy y `dias_max_rodamiento_adelante`; uno por empresa y fecha | J01, J04 |
| `POST /rodamientos/{id}/publicar` · `POST /rodamientos/{id}/anular` | Publicar con solapamientos → 409 `CONFLICTO_NEGOCIO` con la lista | J04 |
| `POST /avisos` · `DELETE /avisos/{id}` | Origen `empresa`; retira solo los suyos | J05 |
| `GET /estadisticas/uso?desde&hasta` | Solo su empresa (ignora `empresaId`) | J06 |

### 2.4 Secretaría de Movilidad (S)

| Método y ruta | Descripción | HU |
|---|---|---|
| `POST /rutas` | `{nombre, tipoRecorrido:"circular", rutaPrincipalId?, paraderoIds:[…ordenados], servicios:[{empresaId, codigoPublico?, codigoInterno?}], confirmarCompartida?}`. Trazado = línea que une los paraderos. Ruta ya asignada a otra empresa y sin `confirmarCompartida` → 409 `CONFLICTO_NEGOCIO` | SM01 |
| `PUT /rutas/{id}` | Edita con `version` | SM02 |
| `DELETE /rutas/{id}?version&confirmar?` | Con turnos futuros y sin `confirmar=true` → 409 con la lista; con `confirmar=true`: baja lógica, cancela turnos futuros | SM03 |
| `POST /rutas/{id}/servicios` · `DELETE /servicios/{id}` | Asigna o retira la ruta a una empresa | SM01 |
| `GET /paraderos` · `POST /paraderos` · `PUT /paraderos/{id}` · `DELETE /paraderos/{id}` | `{nombre, lat, lng}`; duplicado (mismo nombre a < 20 m) → 409; baja de uno usado por rutas → advierte con la lista | SM04 |
| `POST /hitos` | Alta de hito/barrio | SM04 |
| `POST /avisos` | Origen `movilidad`; `{tipoCambio: cierre\|desvio\|obra\|condicion, titulo, cuerpo, rutaIds[], paraderoIds[], desde?, hasta?}` | SM05 |

### 2.5 Administrador (A)

| Método y ruta | Descripción | HU |
|---|---|---|
| `GET /admin/usuarios?correo?` · `POST /admin/usuarios` · `PUT /admin/usuarios/{id}` | Crear en Supabase Auth + `perfil_usuario`; jefe exige `empresaId`; no se puede quitar el rol al último administrador | A01 |
| `GET /admin/roles` | Solo lectura (4 roles fijos) | A02 |
| `GET /admin/empresas` · `POST /admin/empresas` · `PUT /admin/empresas/{id}` | Con `version` | A03 |
| `GET /admin/empresas/{id}/credenciales-gps` · `POST …/credenciales-gps` · `DELETE /admin/credenciales-gps/{id}` | La clave se devuelve **una sola vez** al crearla; en BD solo el hash | A03 |
| `GET /admin/parametros` · `PUT /admin/parametros/{clave}` | Con mínimo y máximo; caché ≤ 60 s | A04 |
| `POST /avisos` | Origen `aplicativo` | A05 |
| `GET /estadisticas/uso?desde&hasta&empresaId?` | Todas las empresas | J06 |
| `GET /demo/estado` · `POST /demo/escenarios` | **Solo con `MODO_DEMO=true`** (si no, 404). Ver §4 | — |

### 2.6 Ingesta de posiciones (fuente GPS)

`POST /ingesta/posiciones` con `X-Clave-Fuente`. Cuerpo:

```json
{ "posiciones": [ { "numeroLateral": "2676", "lat": 5.07, "lng": -75.51, "velocidadKmh": 24.5, "rumbo": 130, "reportadaEn": "2026-10-27T07:15:02-05:00" } ] }
```

Respuesta `202`: `{ "aceptadas": 1, "descartadas": 0, "rechazadas": [ { "indice": 0, "motivo": "fuera_de_zona" } ] }`. Máximo 100 por lote. Motivos de rechazo: `coordenadas_invalidas`, `fuera_de_zona`, `fecha_futura` (> 60 s), `fecha_invalida`, `buseta_desconocida`. Una posición más antigua que la guardada se cuenta en `descartadas` (no es error). Una buseta sin turno vigente se guarda sin servicio y no aparece en ninguna ruta.

## 3. Formas de respuesta clave

**ETA** — `GET /paraderos/{id}/eta?rutaId=…` devuelve un resultado por servicio:

```json
{
  "paraderoId": "…", "rutaId": "…", "calculadoEn": "2026-10-27T08:05:10-05:00",
  "resultados": [
    { "servicioId": "…", "empresa": "Sideral", "codigoPublico": "39",
      "fuente": "gps", "etaSegundos": 240, "busetaNumeroLateral": "1544",
      "ultimaSenalHaceS": 3, "mensaje": null },
    { "servicioId": "…", "empresa": "Serviturismo", "codigoPublico": null,
      "fuente": "horario", "rango": { "minSegundos": 0, "maxSegundos": 240 },
      "mensaje": "Sin ubicación de busetas. Estimación por horario: cada 4 min. Esté pendiente de la siguiente buseta." },
    { "servicioId": "…", "empresa": "Socobuses", "fuente": "no_disponible",
      "mensaje": "El servicio ya cerró." }
  ]
}
```

`fuente` ∈ `gps` | `horario` | `no_disponible`. Reglas en `referencia/02-actividad-3-casos-de-uso.md` (diagrama D2) adaptadas a rutas circulares: distancia restante = `(progresoParadero − progresoBuseta) mod longitudCircuito`. Velocidad efectiva = velocidad reportada si ≥ 5 km/h; si no, `velocidad_default_kmh`.

**Buseta en vivo:**

```json
{ "busetaId": "…", "numeroLateral": "1544", "empresa": "Sideral", "servicioId": "…",
  "estado": "activa", "lat": 5.06, "lng": -75.51, "velocidadKmh": 33.2, "rumbo": 91,
  "reportadaEn": "2026-10-27T08:05:07-05:00" }
```

`estado` ∈ `activa` | `sin_senal` (posición más vieja que `umbral_posicion_obsoleta_s`) — la `sin_senal` va con `mensaje: "Ubicación no disponible. Última señal hace más de 60 s."`. `GET /rutas/{id}/busetas` agrega `seguimientoDisponible` y `unidadesEnServicio`.

**Horarios** (`GET /rutas/{id}/horarios`): por servicio `estado` ∈ `completo` | `parcial` | `pendiente_actualizacion` y `tiposDiaPendientes: ["sabado"]`. Nunca se inventa un dato faltante.

**Rodamiento** (`POST|PUT /rodamientos`):

```json
{ "fecha": "2026-10-28",
  "turnos": [ { "servicioId": "…", "busetaId": "…", "conductorId": "…", "horaSalida": "06:00", "horaFinEstimada": "06:50" } ] }
```

Respuesta: `{ "rodamientoId": "…", "estado": "borrador", "version": 1, "turnos": [...], "advertencias": [ { "codigo": "solapamiento_buseta", "mensaje": "La buseta 1520 sale a las 06:40 y todavía está en el turno de las 06:00 a las 06:50.", "turnoIds": ["…","…"] } ] }`. Códigos de advertencia: `solapamiento_buseta`, `solapamiento_conductor`.

**Planificación** (`POST /viajes/planificar`): entrada `{ "origen": {"lat":…, "lng":…} | {"hitoId":"…"}, "destino": {…} }`; salida `{ "opciones": [ { "tipo":"directa", "rutaId":"…", "servicioId":"…", "paraderoOrigen":{…}, "paraderoDestino":{…}, "caminataMin":4, "esperaMin":6, "busMin":12, "totalMin":22 } ], "motivo": null, "paraderoMasCercano": null }`. Sin opciones: `opciones: []`, `motivo`, `paraderoMasCercano`.

## 4. WebSockets

| Ruta | Quién | Mensajes servidor → cliente |
|---|---|---|
| `/ws/rutas/{rutaId}` | P (sin token) | `{"tipo":"posiciones","rutaId":"…","calculadoEn":"…","busetas":[…forma de buseta en vivo…]}` en cada ciclo del simulador/ingesta; `{"tipo":"senal_perdida","numeroLateral":"…"}`; `{"tipo":"aviso_nuevo","avisoId":"…"}` |
| `/ws/notificaciones?token=<JWT>` | U | `{"tipo":"alerta_llegada","alertaId":"…","rutaId":"…","paraderoId":"…","distanciaM":300,"mensaje":"La buseta 1544 está a 300 m de tu paradero."}` |
| `/ws/notificaciones?token=<JWT>` | U | `{"tipo":"alerta_desvio","alertaId":"…","rutaId":"…","paraderoId":"…","busetaNumero":"1544","mensaje":"La buseta 1544 se desvió de su recorrido. Tu llegada puede cambiar."}` — una vez por episodio de desvío (D-P14) |

El cliente reconecta con espera creciente (1, 2, 4, 8 s, máx. 15 s) y, mientras no haya conexión, usa `GET /rutas/{id}/busetas` cada `intervalo_refresco_cliente_s`. Si pasan más de 3 intervalos sin datos, marca la información como desactualizada (CT-08). El cliente puede enviar `"ping"`; el servidor responde `"pong"`.

## 5. Demo (solo `MODO_DEMO=true`, rol A)

`POST /demo/escenarios`:

| `tipo` | Parámetros | Efecto |
|---|---|---|
| `perder_senal` | `numeroLateral` o `empresaId` | Deja de emitir; tras el umbral pasa a `sin_senal` |
| `restaurar_senal` | igual | Vuelve a emitir |
| `desvio` | `numeroLateral`, `duracionS` | Se aparta del trazado más de `umbral_desvio_m` y regresa |
| `fijar_hora` | `hora: "HH:MM"` o `null` | Reloj simulado (`PuertoReloj`); `null` vuelve al reloj real |
| `acelerar` | `factor` (0.5–5) | Multiplica la velocidad simulada |
| `activar_gps_empresa` | `empresaId`, `activo` | Enciende/apaga a todas las busetas de la empresa |
| `reiniciar_simulacion` | — | Coloca las busetas en posiciones iniciales repartidas |

`GET /demo/estado` devuelve el reloj simulado, el factor, y por buseta: `emitiendo`, `ultimaPosicion`, `empresa`.

## 6. Parámetros globales usados (tabla `parametro_global`)

`radio_busqueda_m` (800), `radio_caminata_m` (500), `radio_hito_m` (300), `velocidad_default_kmh` (20), `umbral_posicion_obsoleta_s` (60), `intervalo_refresco_cliente_s` (5), `distancia_aviso_llegada_m` (300), `enfriamiento_alerta_min` (10), `umbral_desvio_m` (100), `longitud_max_aviso` (500), `max_opciones_viaje` (3), `dias_max_rodamiento_adelante` (15), `rango_max_estadisticas_dias` (365), `caja_ciudad` (provisional, validar con el mapa). Se eliminan `max_filas_excel`, `tamano_max_excel_mb`, `radio_transbordo_m` y `retencion_eventos_dias` (se descartan con el recorte de BD).
