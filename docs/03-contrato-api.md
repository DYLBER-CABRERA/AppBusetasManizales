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

## 7. Precisiones del esqueleto (B0)

`contrato/openapi.json` se genera con `python backend/scripts/exportar_openapi.py` y una prueba (`test_openapi_json_publicado_esta_al_dia`) falla si se desactualiza. Todos los endpoints de este documento están declarados; **hasta que su bloque se implemente responden `501`** con `{ "error": { "codigo": "PENDIENTE", "mensaje": "...", "reintentable": false, "detalles": null } }`. Los endpoints protegidos ya responden `401 NO_AUTENTICADO` sin `Authorization`; con token responden 501 hasta que B4 verifique el JWT. Los WebSockets (`/ws/rutas/{rutaId}`, `/ws/notificaciones`) aceptan la conexión y solo contestan `"pong"` a `"ping"` (OpenAPI no describe WebSockets: el contrato es la §4).

Formas fijadas al declarar los esquemas (cuando este documento no las daba; las que vienen de `referencia/openapi.yaml` se marcan):
- `GET /salud` vive bajo el prefijo: `/api/v1/salud`. Los parámetros de ruta se llaman en el OpenAPI `ruta_id`, `paradero_id`, etc. (la URL no cambia).
- `GET /rutas/{id}` devuelve una forma plana (rutas circulares, D-P02): `id, nombre, tipoRecorrido, esVariante, servicios[], descripcion, rutaPrincipalId, longitudM, trazado` (GeoJSON `LineString`, `[lng, lat]`), `paraderos[{orden, paraderoId, nombre, lat, lng}]`, `avisos[]`, `version`. No usa `sentidos[]` del yaml de referencia.
- `POST /rutas` y `PUT /rutas/{id}` usan `paraderoIds` (no `sentidos[]`). `PUT` acepta `{nombre?, descripcion?, paraderoIds?, version}`.
- `DELETE /rutas/{id}`, `DELETE /servicios/{id}` y `DELETE /paraderos/{id}` reciben `version` (obligatoria) y `confirmar` como parámetros de consulta. *Supuesto:* el contrato solo nombraba `version` para rutas; se aplica la regla general de versión optimista.
- `GET /paraderos` (S/A) devuelve la lista de `Paradero`. `GET /empresas` (público) devuelve `[{id, nombre}]`.
- `GET /rutas/{id}/horarios` → `{tipoDiaHoy, servicios[{servicioId, empresaId, empresaNombre, codigoPublico, estado, horarios[], tiposDiaPendientes[], version}]}`; `GET …/frecuencias` → `{servicios[{…, frecuencias[{tipoDia, franjaInicio, franjaFin, minutosMin, minutosMax, nota}], version}]}` *(yaml de referencia)*.
- `GET /rutas/{id}/busetas` → `{seguimientoDisponible, unidadesEnServicio, calculadoEn, busetas[]}` con la forma de buseta en vivo de §3.
- `POST /viajes/planificar`: `Lugar` = `{lat, lng}` o `{hitoId}` (el texto libre queda fuera, D-P06). Opción: `{tipo:"directa", rutaId, servicioId, paraderoOrigen, paraderoDestino, caminataMin, esperaMin, busMin, totalMin}`.
- `POST /alertas-llegada` recibe `{rutaId, paraderoId, distanciaAvisoM?}`: no hay `sentido` porque todas las rutas son circulares (la BD guarda `circular`).
- `POST /avisos`: `{tipoCambio?, titulo, cuerpo, rutaIds[], paraderoIds[], desde?, hasta?}`; respuesta con `id, origen, empresaId, empresaNombre, titulo, cuerpo, desde, hasta, rutaIds, paraderoIds`.
- `GET /estadisticas/uso` → `{sinDatos, totalesPorTipo[], porRuta[], porDia[]}` *(yaml de referencia)*.
- Rodamiento: `{rodamientoId, fecha, estado, version, turnos[], advertencias[{codigo, mensaje, turnoIds}]}`; `PUT` acepta `confirmarReemplazo`; `publicar` y `anular` reciben `{version}`.
- `POST /admin/empresas/{id}/credenciales-gps` recibe `{nombre}` y devuelve la credencial más `clave` (única vez). `PUT /admin/parametros/{clave}` recibe `{valor, version}`.
- `POST /demo/escenarios` recibe `{tipo, numeroLateral?, empresaId?, duracionS?, hora?, factor?, activo?}` y devuelve el mismo `EstadoDemo` de `GET /demo/estado` (`{relojSimulado, factor, busetas[{numeroLateral, empresa, emitiendo, ultimaPosicion}]}`).

`tipoCambio` de los avisos (`cierre|desvio|obra|condicion`, opcional) se persiste en la columna `aviso.tipo_cambio` (text, nullable, con restricción a esos valores) y se devuelve en la respuesta del aviso. El caso de uso que lo escribe llega en B4/B5; en B0 el endpoint solo declara el campo.

## 8. Precisiones de B2 (consulta pública implementada)

Ya responden con lógica real (el resto sigue en `501` hasta su bloque): `GET /rutas/cercanas`, `GET /rutas`, `GET /rutas/{id}`, `GET /paraderos/cercanos`, `GET /empresas`, `GET /rutas/{id}/horarios`, `GET /rutas/{id}/frecuencias`, `GET /busqueda/rutas`, `GET /busqueda/hitos`, `GET /hitos/{id}/rutas`, `GET /avisos`.

- **Sin `DATABASE_URL` configurado** estos endpoints responden `503 SERVICIO_EXTERNO_NO_DISPONIBLE`; si la BD no contesta (tiempo de espera del pool), también `503` con `reintentable: true`. `GET /salud` nunca consulta la BD.
- **Eventos de uso (RD-17):** `rutas/cercanas`, `rutas` y `paraderos/cercanos` registran `mapa`; `rutas/{id}` → `detalle_ruta`; `…/horarios` → `horarios`; `…/frecuencias` → `frecuencias`; las tres búsquedas → `busqueda`. Se insertan después de responder, sin usuario ni coordenadas, y un fallo al registrar nunca afecta la respuesta. Una consulta con error (404, 400) no registra evento. `GET /empresas` y `GET /avisos` no registran.
- **`GET /rutas/cercanas`:** `distanciaM` de cada ruta es la distancia mínima del punto al trazado; orden ascendente. Sin rutas en el radio: `rutas: []` y `paraderoMasCercano` (el paradero activo más cercano de toda la red).
- **`GET /rutas` y `GET /rutas/{id}`** solo devuelven rutas `activo`; una ruta dada de baja responde `404`. `distanciaM` es `null` en estos dos. `avisos` del detalle son los vigentes que afectan la ruta o alguno de sus paraderos.
- **`GET /avisos`:** avisos con `estado = activo`, `desde ≤ ahora` y `hasta` vacío o futuro (según `PuertoReloj`, así respeta el reloj simulado). Con `rutaId`: los que afectan esa ruta o alguno de sus paraderos. Incluye `tipoCambio`, `rutaIds` y `paraderoIds`.
- **Horarios:** `version` de cada servicio es `servicio_ruta.version` (supuesto: la edición de B4 reemplaza horarios o frecuencias con ese número y lo incrementa). `estado`: `completo` (los 3 tipos de día), `parcial`, `pendiente_actualizacion` (ninguno); `tiposDiaPendientes` lista los tipos sin dato en orden `lun_vie, sabado, dom_festivo`. `tipoDiaHoy` sale del reloj y de `FESTIVOS` (D-P11). La franja que termina a medianoche se devuelve como `"24:00"`.
- **Búsqueda:** el texto se normaliza (minúsculas, sin tildes, espacios colapsados) y se busca por *contiene*; rutas por nombre, código público o interno (el código exacto va primero), hitos por nombre o alias. Máximo 20 resultados. Texto vacío o solo espacios → `400 VALIDACION`.
- **`GET /hitos/{id}/rutas`:** rutas dentro de `radio_hito_m`, ordenadas por cercanía (`distanciaM` = distancia al hito); sin ninguna: `cobertura: false` y `paraderoMasCercano` respecto del hito. Hito inexistente o dado de baja → `404`.
- **Windows:** psycopg asíncrono no funciona con el bucle `Proactor` que uvicorn usa por defecto en Windows. Arranque: `uvicorn servidor:app --app-dir src --loop servidor:fabrica_bucle` (con `--reload` no hace falta, pero no estorba).

## 9. Precisiones de B3a (seguimiento, ETA e ingesta)

Ya responden con lógica real: `GET /rutas/{id}/busetas`, `GET /paraderos/{id}/eta`, `POST /ingesta/posiciones`. Siguen en `501`: WebSockets con difusión, `/demo/*`, `/yo` y el resto de B3b en adelante.

- **`GET /rutas/{id}/busetas`:** lista las busetas que tienen **turno publicado vigente** en esa ruta en este instante (según `PuertoReloj`) y una posición guardada para ese servicio. `estado = sin_senal` si la posición supera `umbral_posicion_obsoleta_s`, con `mensaje: "Ubicación no disponible. Última señal hace más de N s."`. `unidadesEnServicio` cuenta las busetas con turno vigente en la ruta (con o sin GPS); `seguimientoDisponible` es `true` si hay al menos una buseta con posición en la lista (Serviturismo, sin GPS, da `false`). Ruta inexistente o de baja → `404`. Registra evento `busetas_vivo`.
- **`GET /paraderos/{id}/eta?rutaId&servicioId?`:** un resultado por servicio no dado de baja de la ruta, en orden alfabético de empresa. `rutaId` es obligatorio (si falta → `400`). Paradero que no pertenece a la ruta, ruta inexistente o `servicioId` ajeno a la ruta → `404`. Con `fuente: horario`, `rango` es `{minSegundos: 0, maxSegundos: minutos_max × 60}` y `mensaje` sigue el patrón `«Sin ubicación de busetas.|Sin señal GPS en este momento.» Estimación por horario: cada N min|cada A a B min. Esté pendiente de la siguiente buseta.` Mensajes de `no_disponible`: «El servicio está suspendido.», «Información pendiente de actualización.», «Aún no inicia el servicio.», «El servicio ya cerró.», «Frecuencia no informada por la empresa.». Registra evento `eta`.
- **`POST /ingesta/posiciones`:** sin `X-Clave-Fuente`, o con una clave desconocida o revocada → `401 NO_AUTENTICADO`. La clave se compara por su hash SHA-256 y se actualiza `ultimo_uso`. Las coordenadas fuera de rango ya no producen `400` del lote entero: la posición se rechaza con `coordenadas_invalidas` y su `indice`. `fecha_invalida` = hora sin zona horaria. `fuera_de_zona` usa el parámetro `caja_ciudad`. Un lote vacío o de más de 100 posiciones → `400`.
- **Evento interno `posicion.aceptada`:** cada posición guardada se emite una vez (la consumirán el difusor WebSocket y el evaluador de alertas).
- **Limitación conocida (PENDIENTE):** el avance de una buseta se calcula proyectando su punto sobre el trazado; en un tramo que el circuito recorre dos veces (Villamaría, ida y vuelta por la misma vía) la proyección es ambigua y el ETA puede tomar el tramo equivocado.

## 10. Precisiones de B3b (tiempo real, simulador, demo, autenticación y perfil)

Ya responden con lógica real: `GET /yo`, `GET /demo/estado`, `POST /demo/escenarios`, `WS /ws/rutas/{rutaId}`. Todos los endpoints protegidos verifican ahora el token (ver abajo): sin token `401`, token inválido `401`, rol no permitido `403`; con el rol correcto responden su lógica o `501` si su bloque aún no existe.

- **Verificación del token:** el backend llama a `GET {SUPABASE_URL}/auth/v1/user` con el token del usuario y la clave `anon` (así sirve con claves de firma simétricas o asimétricas del proyecto) y lee `rol` y `empresa_id` de `perfil_usuario`. Perfil inexistente o `activo = false` → `401`. Si Supabase Auth no responde → `503`. El resultado se guarda en memoria 30 s (por huella SHA-256 del token). Requiere `SUPABASE_URL` y `SUPABASE_ANON_KEY` en `.env`.
- **`GET /yo`:** `empresaId` y `empresaNombre` solo vienen para el jefe; para los demás roles son `null`.
- **`/demo/*`:** solo rol administrador. Con `MODO_DEMO=false`, o sin base de datos, responden `404`. `POST /demo/escenarios` valida: `perder_senal`/`restaurar_senal` necesitan `numeroLateral` o `empresaId`; `desvio` necesita `numeroLateral` y `duracionS`; `acelerar` necesita `factor` (0.5 a 5; fuera de rango `400`); `activar_gps_empresa` necesita `empresaId` y `activo`; una buseta o empresa sin coincidencias → `404`. `fijar_hora` salta a esa hora **de hoy** y el reloj sigue corriendo desde ahí; también borra las posiciones guardadas (quedaban en otro "tiempo"). `reiniciar_simulacion` también las borra y reparte de nuevo las busetas. `GET /demo/estado` ordena las busetas por empresa y número lateral; `relojSimulado` es `null` con el reloj real.
- **Simulador (`MODO_DEMO=true` y BD configurada):** al arrancar crea, **si faltan**, el rodamiento publicado de hoy de cada empresa y el borrador de mañana de Sideral (lee `backend/supabase/semillas/datos.json`; docs/01 §2.7) y carga las busetas activas. Cada `SIM_INTERVALO_S` mueve cada buseta con turno vigente por el trazado (velocidad `SIM_VELOCIDAD_KMH` ± 5 km/h × factor, tope reportado 150) y llama a `registrar_posiciones`. Serviturismo no emite hasta `activar_gps_empresa`. Una buseta sin turno vigente no se mueve. `desvio` la desplaza `umbral_desvio_m + 60 m` de forma lateral durante `duracionS` y luego regresa.
- **`WS /ws/rutas/{rutaId}`:** al conectar envía una foto inicial `{"tipo":"posiciones","rutaId","calculadoEn","busetas":[…]}` (si la BD responde) y luego un mensaje del mismo tipo por cada ciclo con posiciones aceptadas en esa ruta (las posiciones de un mismo ciclo se agrupan en un solo mensaje). Un cliente caído o lento se descarta sin frenar el ciclo. `"ping"` → `"pong"`.
- **Siguen PENDIENTES en el WebSocket:** `senal_perdida` y `/ws/notificaciones` con token (`alerta_llegada` y `alerta_desvio`, B6): hoy ese socket solo responde ping/pong.

## 11. Precisiones de B4 (operación del jefe y avisos por rol)

Ya responden con lógica real: `GET /mis-servicios`, `GET|POST /busetas`, `PUT /busetas/{id}`, `GET|POST /conductores`, `PUT /conductores/{id}`, `PUT /servicios/{id}/horarios`, `PUT /servicios/{id}/frecuencias`, `GET|POST /rodamientos`, `GET|PUT /rodamientos/{id}`, `POST /rodamientos/{id}/publicar|anular`, `POST /avisos` y `DELETE /avisos/{id}`. Solo el rol jefe llega a la lógica de operación (los demás roles reciben `403`; sin token `401`). **Todo recurso de otra empresa responde `404`** (nunca `403`), incluidos los recursos referenciados dentro de un turno.

- **Busetas y conductores:** número lateral único por empresa (repetido → `409 CONFLICTO_NEGOCIO`); código de conductor único por empresa entre los activos. `PUT` con `version` desfasada → `409 CONFLICTO_VERSION` con `detalles.versionActual`. En los `PUT`, un campo omitido o `null` **no se modifica** (no hay forma de borrar la placa o el código; supuesto). Las busetas y conductores en `baja` no se listan. Cada `GET` lista solo lo de la empresa del token.
- **Horarios y frecuencias:** `version` es la de `servicio_ruta`; **cada `PUT` (de horarios o de frecuencias) la incrementa** y la devuelve, así que el panel debe usar la `version` de la última respuesta. Cada `PUT` **reemplaza todo** el conjunto del servicio. Validación (`400`): tipo de día repetido, primera salida posterior a la última, cierre anterior a la última salida; franjas con fin ≤ inicio, `minutosMax < minutosMin` o solapadas en un mismo tipo de día. Servicio inexistente, de baja o de otra empresa → `404`.
- **Rodamientos:** `fecha` entre hoy y `dias_max_rodamiento_adelante` (según `PuertoReloj`); formato inválido o fuera de rango → `400`; ya hay uno no anulado de la empresa para esa fecha → `409 CONFLICTO_NEGOCIO` (una fecha anulada puede volver a crearse). `horaFinEstimada` debe ser posterior a `horaSalida`; sin ella el solapamiento usa `duracion_estandar_min` del servicio (o 120 min). `advertencias` se calcula siempre al responder (turnos consecutivos, fin = salida, no se solapan; se evalúa buseta y conductor). **Solo un borrador se edita** (`PUT`) o se publica; una versión desfasada → `409 CONFLICTO_VERSION`. `PUT` reemplaza todos los turnos. Cambiar la buseta o el conductor de un turno ya guardado (mismo `servicioId` + `horaSalida`) sin `confirmarReemplazo=true` → `409 CONFLICTO_NEGOCIO` con `detalles.turnosAfectados[{turnoId, servicioId, horaSalida, busetaActual, busetaNueva, conductorActual, conductorNuevo}]` y el mensaje «La ruta ya tiene asignada la buseta N a las HH:MM. ¿Reemplazarla por la M?». `publicar` con solapamientos → `409 CONFLICTO_NEGOCIO` con `detalles.advertencias[{codigo, mensaje, turnoIds}]`. `anular` funciona desde borrador o publicado; un anulado → `409`. `GET /rodamientos?desde&hasta` acepta `AAAA-MM-DD` (otro formato → `400`) y ordena por fecha descendente.
- **`POST /avisos`:** J → `origen = empresa` con su empresa (solo `rutaIds` de rutas que su empresa opera, si no `404`; `paraderoIds` no permitidos → `400`); S → `movilidad`; A → `aplicativo` (puede ir sin rutas). `tipoCambio` solo se guarda con origen `movilidad`. `titulo` y `cuerpo` no vacíos; `cuerpo` ≤ `longitud_max_aviso`; `hasta` posterior a `desde`; `desde` por omisión es ahora; rutas o paraderos inexistentes → `404`; J y S deben indicar al menos una ruta (o paradero, S). Al publicar se difunde `{"tipo":"aviso_nuevo","avisoId"}` por `/ws/rutas/{rutaId}` de cada ruta afectada.
- **`DELETE /avisos/{id}`** (retirar = `estado: retirado`): J solo los de su empresa (otro aviso o de otra empresa → `404`); S solo los `movilidad` (otro → `403`); A cualquiera; ya retirado o inexistente → `404`.

## 12. Precisión: `empresaId` en los endpoints del jefe

Todos los endpoints de §11 (operación del jefe y edición de horarios/frecuencias) aceptan el parámetro de consulta opcional `empresaId`. El **jefe lo ignora** (siempre se usa la empresa de su token). El **administrador** (BR-07) debe indicarlo (si falta: `400`) y actúa como jefe de esa empresa; un recurso de otra empresa sigue dando `404`. Los roles pasajero y Secretaría reciben `403`. Los avisos no usan este parámetro (el administrador publica con origen `aplicativo`).
