# Actividad 7 — Calidad, pruebas y riesgos

> **Estado:** [PROPUESTO] para aprobación del equipo. El contexto fija RNF-01, RNF-02 y RNF-03 y dice que los valores medibles de cada SPEC los define el equipo (§12). Los valores de las SPEC se usan como **fuente**; donde el prototipo no puede cumplirlos tal cual, se propone un objetivo ajustado y se marca para aprobación.
> Notación: **[FUENTE]** viene de los documentos, **[PROPUESTO]** lo propone este diseño, **[SUPUESTO S-xx]** completa información faltante.

---

## 1. Requisitos no funcionales medibles

### 1.1 Requisitos fijos (todas las SPEC) [FUENTE: contexto §12]

| ID | Categoría | Requisito | Cómo se verifica | Criterio de aceptación |
|---|---|---|---|---|
| RNF-01 | Seguridad | Los datos viajan cifrados (HTTPS/TLS 1.2+) y no se registran credenciales ni datos personales en logs | PS-SEG-01 (escaneo del endpoint), PI-LOG-01 (revisión automática de logs) | El hosting rechaza TLS menor que 1.2 y HTTP sin cifrar redirige; cero apariciones de `authorization`, `x-clave-fuente`, correo o coordenadas de usuario en los logs de la suite |
| RNF-02 | Integridad | Las actualizaciones concurrentes del mismo recurso no pierden datos | PI-CON-01..04 | Con dos escritores simultáneos sobre la misma `version` exactamente uno tiene éxito y el otro recibe 409 `CONFLICTO_VERSION`; ningún dato se pierde |
| RNF-03 | Compatibilidad | La interfaz funciona en navegadores móviles y de escritorio modernos, desde pantallas de 320 px | PS-CMP-01..03 (prototipo y frontend) | Sin desplazamiento horizontal ni controles recortados a 320 px; flujos P01, P03, P06 y P07 completables en Chrome, Firefox, Safari y Edge en sus versiones estables vigentes |

### 1.2 Requisitos por SPEC: valor de la SPEC y objetivo del prototipo

"Carga definida" aparece en las SPEC sin valor. Se propone el **perfil de carga PC-1** (sección 4.5), que el equipo debe aprobar.

| SPEC | Módulo | Rendimiento (SPEC) | Objetivo del prototipo [PROPUESTO] | Disponibilidad (SPEC) | Objetivo del prototipo [PROPUESTO] | Actualización (SPEC) | Objetivo del prototipo [PROPUESTO] |
|---|---|---|---|---|---|---|---|
| 001 | Consulta de rutas | 1 s | p95 ≤ 1 s | 20 % | Best-effort; se mide durante la ventana de demo | 10 s | 10 s |
| 002 | Horarios | 1 s | p95 ≤ 1 s | 99.9 % | Best-effort; se mide | 5 s | Cambio visible ≤ 60 s (los horarios cambian poco) |
| 003 | GPS y ETA | 2 s | p95 ≤ 2 s | 99.5 % | Best-effort; se mide | 0.5 s | **5 s** (sondeo del cliente) — *cambia el valor de la SPEC; requiere aprobación* |
| 004 | Planificación | 2.5 s | p95 ≤ 2.5 s | 99 % | Best-effort; se mide | 1 s | Grafo con desfase ≤ 60 s respecto de la red |
| 005 | Búsqueda | 1 s | p95 ≤ 1 s | 99.9 % | Best-effort; se mide | 1 s | Resultados reflejan el catálogo vigente (consulta directa) |
| 006 | Jefe de operaciones | 2 s | p95 ≤ 2 s | 99.5 % | Best-effort; se mide | 10 s | 10 s |
| 007 | Secretaría | 1 s | p95 ≤ 1 s | 99.9 % | Best-effort; se mide | 0.2 s | **Cambio visible para el pasajero ≤ 10 s** — *cambia el valor de la SPEC; requiere aprobación* |
| 008 | Favoritas | 0.5 s | p95 ≤ 0.5 s | 99.9 % | Best-effort; se mide | 1 s | 1 s |
| 009 | Notificaciones | 1 s | Evaluación de alertas por posición recibida: p95 ≤ 1 s | 99.5 % | Best-effort; se mide | 1 s | Aviso generado ≤ 5 s después de que la buseta cruza la distancia (entrega push best-effort) |
| 010 | Uso sin cuenta | 1 s | p95 ≤ 1 s en la carga inicial | 99.5 % | Best-effort; se mide | 1 s | 1 s |
| 011 | Avisos | 1 s | p95 ≤ 1 s al publicar | 99.5 % | Best-effort; se mide | 5 s | Aviso visible ≤ 5 s tras publicar |
| 012 | Estadísticas | 2 s | p95 ≤ 2 s para un rango de 90 días | 99 % | Best-effort; se mide | 60 s | 60 s |
| 013 | Administrador | 1 s | p95 ≤ 1 s | 99.9 % | Best-effort; se mide | 1 s | 1 s |

Aclaraciones:
- "p95 ≤ X" significa: el 95 % de las peticiones, medidas en el servidor desde que llega hasta que termina de responder, bajo PC-1, **con el servicio caliente** (el arranque en frío del hosting gratuito queda fuera y se documenta como limitación).
- **Disponibilidad:** el plan gratuito de Supabase y los hostings gratuitos no ofrecen SLA. No se puede garantizar 99.9 % en un prototipo. El objetivo del prototipo es **medir y reportar**: un ping a `GET /api/v1/salud` cada 5 minutos durante la ventana de demo, con el porcentaje de éxitos reportado. Para producción el equipo debe fijar el objetivo real.
- Los valores de las SPEC-005 a SPEC-013 están marcados "Modelo LLM (propuesta)" y los de las SPEC-001 a SPEC-004 fueron confirmados por el equipo. Cualquier cambio a estos números lo aprueba el equipo, no esta documentación.

### 1.3 Requisitos adicionales propuestos

| ID | Categoría | Requisito | Medida | Verificación |
|---|---|---|---|---|
| RNF-Q-01 | Exactitud del ETA | Con una posición fresca válida, el ETA por GPS difiere en menos de 1 s del cálculo teórico (distancia/velocidad) | |Δ| ≤ 1 s | ET-01..ET-08 |
| RNF-Q-02 | Frescura de la posición | Una posición con edad mayor que `umbral_posicion_obsoleta_s` nunca se presenta como activa | 0 casos | GP-09, PS-GPS-02 |
| RNF-Q-03 | Idempotencia de la ingesta | Reenviar el mismo lote no cambia el estado ni duplica notificaciones | 0 cambios | GP-07 |
| RNF-Q-04 | Importación | Una importación de 5000 filas termina en 30 s o menos y reporta fila, columna y motivo de cada error | ≤ 30 s | PS-XLS-02 |
| RNF-Q-05 | Aislamiento por empresa | Un jefe no puede leer ni escribir datos de otra empresa | 0 fugas | PI-AUT-05..08 |
| RNF-Q-06 | Degradación controlada | Si falla un servicio externo, las consultas públicas siguen respondiendo | 100 % de consultas públicas disponibles con GPS, geocodificador y push caídos | FA-01..FA-06 |
| RNF-Q-07 | Cobertura de pruebas | Cobertura de líneas en `dominio` y `aplicacion` | ≥ 80 % | Informe de `vitest --coverage` |
| RNF-Q-08 | Accesibilidad de la interfaz | Contraste de texto mínimo 4.5:1, objetivos táctiles de al menos 44×44 px, la información no depende solo del color | Revisión del prototipo | PS-CMP-03 |

---

## 2. Seguridad

### 2.1 Controles

| ID | Control | Implementación propuesta | Verificación |
|---|---|---|---|
| SEG-01 | Cifrado en tránsito | HTTPS del hosting; `helmet` con HSTS | PS-SEG-01 |
| SEG-02 | Autenticación | JWT de Supabase Auth validado en cada petición protegida; usuario inactivo → 401 | PI-AUT-01..04 |
| SEG-03 | Autorización por rol y empresa | En el caso de uso, no solo en el middleware; la empresa sale del token | PI-AUT-05..12 |
| SEG-04 | Clave de la fuente GPS | Se genera aleatoria, se muestra una vez, se guarda su hash SHA-256; revocable | PI-AUT-13..15 |
| SEG-05 | Validación de entrada | `zod` en todos los controladores; consultas SQL solo con parámetros (`rpc` o consultas parametrizadas) | PU-VAL-*, PS-SEG-03 |
| SEG-06 | Carga de archivos | Solo `.xlsx`, tamaño y filas limitados, se comprueba la firma del archivo (ZIP), se lee en memoria, nunca se ejecuta contenido | PS-XLS-03..05 |
| SEG-07 | Inyección en Excel | Los textos que empiezan con `=`, `+`, `-`, `@` se almacenan como texto y se escapan en cualquier exportación | PS-XLS-06 |
| SEG-08 | Límite de peticiones | `express-rate-limit`: general por IP; ingesta por clave (un lote cada 2 s); autenticación más estricta | PI-LIM-01..03 |
| SEG-09 | CORS | Lista blanca de orígenes por variable de entorno | PS-SEG-02 |
| SEG-10 | Secretos | `service_role` y claves VAPID solo en variables de entorno del servidor; `.env` fuera del repositorio; el frontend nunca recibe `service_role` | Revisión de repositorio |
| SEG-11 | Base de datos | RLS activada sin políticas; funciones sin permiso de ejecución para `anon` y `authenticated` | PS-SEG-04 (consulta directa con clave anónima devuelve vacío o error) |
| SEG-12 | Dependencias | `npm audit` en cada integración continua; bloquear altas y críticas | CI |
| SEG-13 | Errores | El cliente no recibe trazas ni mensajes internos; `ERROR_INTERNO` genérico con `X-Id-Peticion` | PI-ERR-01 |
| SEG-14 | Registro de auditoría | Se registran quién publicó el rodamiento y los avisos (`publicado_por`, `autor_id`); cambios de rol de usuario | PI-AUD-01 |

### 2.2 Privacidad [PROPUESTO]

| ID | Criterio |
|---|---|
| PRI-01 | **No se almacena la ubicación del pasajero.** Se usa solo dentro de la petición (rutas cercanas, planificación) y no se escribe en base ni en logs (S-16). |
| PRI-02 | Las estadísticas usan eventos sin identificador de usuario ni coordenadas (RD-17). |
| PRI-03 | Del conductor se guarda solo nombre y código interno opcional. No se guarda documento de identidad ni teléfono (BR-06: es un dato del rodamiento). |
| PRI-04 | Del pasajero registrado se guarda correo y sus favoritos y alertas. El correo no sale en logs. |
| PRI-05 | Los eventos de uso se eliminan a los `retencion_eventos_dias` (180 por defecto) con `limpiar_eventos_uso`. |
| PRI-06 | El usuario puede borrar sus alertas, favoritos y suscripciones; la baja de cuenta elimina esos datos (cascada). |
| PRI-07 | El equipo debe revisar con asesoría el cumplimiento de la normativa colombiana de protección de datos personales (Ley 1581 de 2012) antes de salir del prototipo. |

### 2.3 Disponibilidad y continuidad [PROPUESTO]

| ID | Criterio |
|---|---|
| DIS-01 | `GET /salud` responde en menos de 200 ms sin consultar la base. |
| DIS-02 | Con la base caída, `salud` sigue en `ok` pero las demás rutas devuelven 503 reintentable; el cliente conserva lo ya cargado. |
| DIS-03 | Degradación: sin fuente GPS → ETA por horario; sin geocodificador → planificación por coordenadas e hitos; sin push → bandeja interna. |
| DIS-04 | El esquema y las semillas se versionan en el repositorio (`esquema.sql` y migraciones) para reconstruir la base. El equipo debe verificar la política de copias de seguridad del plan de Supabase que use. |
| DIS-05 | Un solo proceso (limitación documentada). Reinicio: el grafo y los parámetros se reconstruyen al arrancar; las alertas se leen de la base. |

### 2.4 Rendimiento: técnicas

- Todas las lecturas públicas usan índices (sección 2.3 de la Actividad 6). Sin `select *` en listados.
- Caché en memoria de parámetros y grafo (60 s). Caché de horarios por servicio (60 s) invalidada al escribir.
- La posición se actualiza con un `upsert` por buseta; no crece el historial.
- Consultas de busetas en vivo y ETA: máximo una consulta SQL por solicitud más el cálculo en memoria.

---

## 3. Estrategia de pruebas

| Nivel | Qué prueba | Herramienta (gratuita) | Dónde corre | Criterio de salida |
|---|---|---|---|---|
| Unitarias (PU) | Reglas del dominio y casos de uso con puertos simulados (`PuertoReloj` fijo) | `vitest` | Local y CI | Cobertura ≥ 80 % en dominio y aplicación; 0 fallos |
| Integración (PI) | Controladores + repositorios contra una base real con PostGIS | `vitest` + `supertest` + Postgres/PostGIS local (contenedor o instancia de prueba, como la usada para validar `esquema.sql`) | Local y CI | 100 % de endpoints de `openapi.yaml` con al menos un caso feliz y uno de error |
| Contrato (PC) | Que las respuestas cumplen `openapi.yaml` | Validador del esquema (ej. `openapi-response-validator` o `schemathesis`) | CI | 0 incumplimientos |
| Sistema (PS) | Flujos completos con el simulador GPS, Excel reales y los 4 roles | `vitest` + simulador; navegador automatizado para el prototipo (Playwright) | Entorno de prueba con Supabase de pruebas | Todos los escenarios críticos pasan |
| Aceptación (PA) | Un escenario por criterio de aceptación AC de las SPEC | Los mismos, escritos en formato Dado/Cuando/Entonces | Revisión con el equipo | 28/28 AC aprobados por el equipo |
| No funcional (PN) | Rendimiento, seguridad, compatibilidad | `autocannon`, `npm audit`, Playwright a 320 px | Entorno de prueba | Sección 1 |

Datos de prueba: un conjunto semilla pequeño y **marcado como ficticio** (2 empresas, 3 rutas incluida una compartida, una variante, una circular, 12 paraderos, 6 hitos, 6 busetas, rodamiento del día). Los nombres reales de hitos del contexto (Catedral, El Cable, Carrera 23, Fundadores) pueden usarse como nombres de hitos; las coordenadas de prueba son sintéticas.

---

## 4. Escenarios de prueba

### 4.1 Pruebas unitarias (PU)

| ID | Componente | Escenario | Resultado esperado |
|---|---|---|---|
| PU-ETA-01 | `CalculadorEta` | Buseta a 1000 m del paradero, 20 km/h | 180 s, fuente `gps` |
| PU-ETA-02 | `CalculadorEta` | Velocidad reportada 0 km/h | Usa `velocidad_default_kmh`; ETA coherente con 20 km/h |
| PU-ETA-03 | `CalculadorEta` | Dos busetas, a 1000 m y a 400 m | ETA de la más cercana (72 s a 20 km/h) |
| PU-ETA-04 | `CalculadorEta` | Una buseta ya pasó el paradero (lineal) | Se ignora; si no hay otra, respaldo por horario |
| PU-ETA-05 | `CalculadorEta` | Circular: longitud 10 000 m, buseta en 9 500 m, paradero en 500 m | Distancia 1000 m → 180 s |
| PU-ETA-06 | `CalculadorEta` | Posición más vieja que el umbral | No cuenta; respaldo por horario y mensaje "esté pendiente de la siguiente buseta" |
| PU-ETA-07 | `CalculadorEta` | Sin posiciones, dentro del horario, frecuencia 10–15 min | `fuente=horario`, rango 0–900 s |
| PU-ETA-08 | `CalculadorEta` | Sin posiciones, fuera de horario | `no_disponible`, "el servicio ya cerró" / "aún no inicia" |
| PU-ETA-09 | `CalculadorEta` | Sin posiciones, sin frecuencia | `no_disponible`, "frecuencia no informada" |
| PU-ETA-10 | `CalculadorEta` | Servicio suspendido | `no_disponible` con motivo |
| PU-TD-01..04 | `CalculadorTipoDia` | Lunes, sábado, domingo, festivo entre semana | `lun_vie`, `sabado`, `dom_festivo`, `dom_festivo` |
| PU-DED-01 | `DeductorDeRuta` | Buseta con turno vigente | Devuelve el servicio |
| PU-DED-02 | `DeductorDeRuta` | Buseta con dos turnos en el día, instante en el segundo | Devuelve el segundo servicio (cambia de ruta) |
| PU-DED-03 | `DeductorDeRuta` | Fuera de cualquier turno | `null` |
| PU-DED-04 | `DeductorDeRuta` | Turno sin `hora_fin`; pasa la duración estándar | `null` tras la duración |
| PU-ALE-01 | `EvaluadorAlertas` | Buseta entra a la distancia de aviso | Genera aviso |
| PU-ALE-02 | `EvaluadorAlertas` | Segunda posición dentro del enfriamiento | No repite |
| PU-ALE-03 | `EvaluadorAlertas` | Pasa el enfriamiento y llega otra buseta | Nuevo aviso |
| PU-ALE-04 | `EvaluadorAlertas` | Desvío mayor que `umbral_desvio_m` | Aviso de cambio de estado |
| PU-ALE-05 | `EvaluadorAlertas` | Buseta que ya pasó el paradero | No avisa |
| PU-ROD-01 | `ValidadorRodamiento` | Misma buseta con dos turnos solapados | Advertencia `solapamiento_buseta` |
| PU-ROD-02 | `ValidadorRodamiento` | Mismo conductor en dos busetas a la vez | Advertencia `solapamiento_conductor` |
| PU-ROD-03 | `ValidadorRodamiento` | Buseta con turnos consecutivos sin solapar en rutas distintas | Sin advertencias |
| PU-ROD-04 | `ValidadorRodamiento` | Turno de buseta sin asignación a ese servicio | Advertencia `buseta_sin_asignacion` |
| PU-PLA-01 | `PlanificadorViaje` | Origen y destino sobre la misma ruta, destino adelante | Opción directa |
| PU-PLA-02 | `PlanificadorViaje` | Destino atrás del origen en ruta lineal | Se usa el otro sentido si existe; si no, sin opción directa |
| PU-PLA-03 | `PlanificadorViaje` | Sin directa, hay transbordo a menos de `radio_transbordo_m` | Opción `con_transbordo` |
| PU-PLA-04 | `PlanificadorViaje` | Más de 3 opciones posibles | Devuelve `max_opciones_viaje` ordenadas por tiempo |
| PU-PLA-05 | `PlanificadorViaje` | Ruta compartida por dos empresas | Dos opciones, una por empresa, con la espera de cada frecuencia |
| PU-PLA-06 | `PlanificadorViaje` | Servicio fuera de horario | Se descarta |
| PU-AVI-01..03 | `PoliticaDeAvisos` | Rol jefe / Secretaría / administrador | Origen `empresa` / `movilidad` / `aplicativo` |
| PU-AVI-04 | `PoliticaDeAvisos` | Cuerpo vacío | `ErrorValidacion` |
| PU-AVI-05 | `PoliticaDeAvisos` | Cuerpo más largo que `longitud_max_aviso` | `ErrorValidacion` con el límite |
| PU-VER-01 | Control de versión | Versión distinta | `ErrorConflictoVersion` con la versión actual |
| PU-VAL-01..10 | Esquemas `zod` | Coordenadas, horas, UUID, textos, enums y rangos fuera de rango | `ErrorValidacion` con el campo |

### 4.2 Pruebas de integración (PI)

| ID | Endpoint / flujo | Escenario | Esperado |
|---|---|---|---|
| PI-RED-01 | `GET /rutas/cercanas` | Punto sobre una ruta | Incluye la ruta y paraderos cercanos |
| PI-RED-02 | `GET /rutas/cercanas` | Punto sin rutas a 800 m | `rutas: []` y `paraderoMasCercano` |
| PI-RED-03 | `GET /rutas/{id}` | Ruta existente | Trazados por sentido y paraderos ordenados |
| PI-RED-04 | `GET /rutas/{id}` | Ruta inexistente o dada de baja | 404 |
| PI-RED-05 | `GET /rutas/{id}` | Circular | Un solo sentido `circular` |
| PI-RED-06 | `GET /rutas/{id}` | Ruta con variantes | `variantes` informadas |
| PI-HOR-01 | `GET /rutas/{id}/horarios` | Servicio con los tres tipos de día | Los tres horarios |
| PI-HOR-02 | `GET /rutas/{id}/horarios` | Servicio sin sábado | `tiposDiaPendientes: [sabado]`, estado `parcial` |
| PI-HOR-03 | `GET /rutas/{id}/horarios` | Servicio sin horarios | `pendiente_actualizacion` |
| PI-HOR-04 | `GET /rutas/{id}/horarios` | Ruta compartida | Un elemento por empresa |
| PI-HOR-05 | `GET /rutas/{id}/frecuencias` | Frecuencia fija y variable | `minutosMin = minutosMax` y rango |
| PI-HOR-06 | `PUT /servicios/{id}/frecuencias` | Franjas solapadas | 400 |
| PI-SEG-01 | `GET /rutas/{id}/busetas` | Dos busetas con turno y posición fresca | Dos `activa` |
| PI-SEG-02 | `GET /rutas/{id}/busetas` | Una con posición vieja | `sin_senal` con mensaje |
| PI-SEG-03 | `GET /rutas/{id}/busetas` | Ninguna | `busetas: []`, `unidadesEnServicio: 0` |
| PI-SEG-04 | `GET /paraderos/{id}/eta` | Buseta con posición fresca | `gps` |
| PI-SEG-05 | `GET /paraderos/{id}/eta` | Sin posiciones | `horario` o `no_disponible` |
| PI-SEG-06 | `GET /paraderos/{id}/eta` | Paradero que no está en la ruta | 404 |
| PI-BUS-01 | `GET /busqueda/rutas` | `q=39` | Ruta con código público 39 |
| PI-BUS-02 | `GET /busqueda/rutas` | Nombre con tildes distintas | Coincide (normalizado) |
| PI-BUS-03 | `GET /busqueda/rutas` | Ruta sin código (Serviturismo) | Solo por nombre |
| PI-BUS-04 | `GET /busqueda/hitos` / `GET /hitos/{id}/rutas` | Hito con cobertura | Lista de rutas a menos de `radio_hito_m` |
| PI-BUS-05 | `GET /hitos/{id}/rutas` | Hito sin cobertura | `cobertura: false` y paradero más cercano |
| PI-PLA-01 | `POST /viajes/planificar` | Origen y destino con directa | `directa` |
| PI-PLA-02 | `POST /viajes/planificar` | Sin directa | `con_transbordo` |
| PI-PLA-03 | `POST /viajes/planificar` | Texto no geocodificable | 404 o 503 según el caso |
| PI-PLA-04 | `POST /viajes/planificar` | Formato con dos formas de lugar a la vez | 400 |
| PI-FAV-01 | `POST /favoritos` | Con sesión | 201 |
| PI-FAV-02 | `POST /favoritos` | Sin sesión | 401 con "Inicia sesión para guardar" |
| PI-FAV-03 | `POST /favoritos` | Repetido | 200 con el existente |
| PI-FAV-04 | `GET /favoritos` | Ruta dada de baja | `disponible: false` |
| PI-ALE-01 | `POST /alertas-llegada` | Valores por defecto | `distanciaAvisoM` = parámetro |
| PI-ALE-02 | `POST /alertas-llegada` | Repetida | 409 |
| PI-ALE-03 | Posición → notificación | Posición dentro de la distancia | Notificación `push` o `bandeja` |
| PI-ALE-04 | Posición → notificación | Push falla | Notificación `bandeja`, estado `fallida` registrado |
| PI-OPE-01 | `POST /asignaciones` | Nueva asignación | 201 |
| PI-OPE-02 | `POST /asignaciones` | Misma buseta y servicio con otro conductor, sin confirmar | 409 con la actual |
| PI-OPE-03 | `POST /asignaciones` | Con `confirmarCambio=true` | 201, reemplaza |
| PI-OPE-04 | `POST /asignaciones` | Buseta con dos servicios distintos | Ambas válidas |
| PI-OPE-05 | `POST /rodamientos` | Turnos con solapamiento | 201 con advertencias, estado `borrador` |
| PI-OPE-06 | `POST /rodamientos/{id}/publicar` | Con solapamientos | 409 con la lista |
| PI-OPE-07 | `POST /rodamientos/{id}/publicar` | Sin solapamientos | 200, `publicado` |
| PI-OPE-08 | `POST /rodamientos` | Fecha anterior a hoy o más allá del límite | 400 |
| PI-OPE-09 | `POST /rodamientos` | Segundo rodamiento para la misma fecha | 409 |
| PI-OPE-10 | `PUT /servicios/{id}/datos-operativos` | Servicio de otra empresa | 404 |
| PI-SEC-01 | `POST /rutas` | Ruta nueva con una empresa | 201 |
| PI-SEC-02 | `POST /rutas` | Equivalente ya asignada a otra empresa, sin confirmar | 409 |
| PI-SEC-03 | `POST /rutas` | Con `confirmarCompartida=true` | 201, dos servicios |
| PI-SEC-04 | `POST /rutas` | Circular con dos sentidos | 400 |
| PI-SEC-05 | `PUT /rutas/{id}` | Ruta inexistente | 404 |
| PI-SEC-06 | `DELETE /rutas/{id}` | Con asignaciones, sin confirmar | 409 con la lista |
| PI-SEC-07 | `DELETE /rutas/{id}?confirmar=true` | Con asignaciones | 204; asignaciones cerradas; turnos futuros cancelados |
| PI-SEC-08 | `POST /paraderos` | Duplicado a menos de 20 m con el mismo nombre | 409 |
| PI-SEC-09 | `POST /avisos` (movilidad) | Datos incompletos | 400 |
| PI-AVI-01 | `POST /avisos` | Cuerpo vacío / demasiado largo | 400 con el límite |
| PI-AVI-02 | `GET /avisos` | Aviso vencido | No aparece |
| PI-AVI-03 | `GET /avisos` | Aviso de empresa A | Aparece en rutas de A y en el listado general |
| PI-EST-01 | `GET /estadisticas/uso` | Con eventos | Totales por tipo, ruta y día |
| PI-EST-02 | `GET /estadisticas/uso` | Sin eventos | `sinDatos: true` |
| PI-EST-03 | `GET /estadisticas/uso` | Jefe pidiendo otra empresa | Se ignora `empresaId`; solo la suya |
| PI-ADM-01 | `POST /admin/usuarios` | Jefe sin empresa | 400 |
| PI-ADM-02 | `PUT /admin/usuarios/{id}` | Quitar rol al último administrador | 409 |
| PI-ADM-03 | `PUT /admin/roles/{rol}/permisos` | Rol fuera de los cuatro | 400 |
| PI-ADM-04 | `PUT /admin/parametros/{clave}` | Fuera de rango / clave inexistente | 400 / 404 |
| PI-ADM-05 | `POST /admin/empresas/{id}/credenciales-gps` | Crear | La clave se muestra una vez; en base solo el hash |
| PI-CON-01 | Actualización concurrente | Dos `PUT` con la misma `version` en paralelo | Uno 200, otro 409 `CONFLICTO_VERSION` |
| PI-CON-02 | Rodamiento | Dos publicaciones a la vez | Una gana, la otra 409 |
| PI-CON-03 | Asignación | Dos asignaciones simultáneas de la misma buseta y servicio | Una crea; la otra 409 (índice único) |
| PI-CON-04 | Posición | Dos posiciones del mismo instante | Una guardada; no hay error |
| PI-AUT-01..04 | Autenticación | Sin token, token inválido, token vencido, usuario inactivo | 401 |
| PI-AUT-05..08 | Aislamiento | Jefe A lee/escribe conductores, busetas, rodamientos y servicios de B | 404, sin cambios |
| PI-AUT-09..12 | Rol | Pasajero en rutas de jefe; jefe en rutas de Secretaría; Secretaría en rodamientos; jefe en `/admin` | 403 |
| PI-AUT-13..15 | Clave de fuente | Clave inválida, revocada, de otra empresa con buseta ajena | 401, 401, buseta rechazada |
| PI-LIM-01..03 | Límites | Exceso general, ingesta cada <2 s, inicio de sesión | 429 con `Retry-After` |
| PI-ERR-01 | Errores | Excepción interna forzada | 500 `ERROR_INTERNO` sin trazas |
| PI-LOG-01 | Logs | Ejecutar la suite y buscar secretos | Cero coincidencias |
| PI-AUD-01 | Auditoría | Publicar rodamiento y aviso | `publicado_por` y `autor_id` registrados |
| PI-BD-01 | Base | Aplicar `esquema.sql` en base vacía | Sin errores |
| PI-BD-02 | Base | Violar cada restricción de la sección 2.2 de la Actividad 6 | Error esperado en cada caso |
| PI-BD-03 | Base | Probar funciones `rutas_cercanas`, `progreso_en_ruta`, `turno_vigente`, `guardar_posicion` | Valores del ejemplo (se ejecutaron en la validación del esquema) |

### 4.3 Pruebas de GPS (GP) — posiciones

| ID | Entrada | Esperado |
|---|---|---|
| GP-01 | Posición válida de una buseta con turno | Aceptada; `posicion_buseta` actualizada |
| GP-02 | `lat` = 95 | Rechazada `coordenadas_invalidas` |
| GP-03 | Coordenadas (0, 0) | Rechazada `fuera_de_zona` |
| GP-04 | `reportadaEn` 5 minutos en el futuro | Rechazada `fecha_futura` |
| GP-05 | `reportadaEn` con formato inválido | Rechazada `fecha_invalida` |
| GP-06 | Número lateral desconocido | Rechazada `buseta_desconocida` |
| GP-07 | Mismo lote enviado dos veces | La segunda: `descartadas` = n; sin cambios ni notificaciones nuevas |
| GP-08 | Posición más antigua que la guardada (fuera de orden) | Descartada; la guardada no cambia |
| GP-09 | Posición con edad mayor que el umbral | Al consultar: `sin_senal` |
| GP-10 | Buseta sin turno vigente | Guardada sin servicio; no aparece en ninguna ruta |
| GP-11 | Buseta cambia de ruta a mitad del día (dos turnos) | Primer reporte → servicio 1; segundo → servicio 2; ETA de cada ruta correcto |
| GP-12 | Salto de 5 km en 5 s | Se acepta; el ETA usa la velocidad por defecto y no la implícita |
| GP-13 | Lote de 101 posiciones | 400 |
| GP-14 | Lote con 99 válidas y 1 inválida | 202 con 99 aceptadas y 1 rechazada |
| GP-15 | Reloj de la fuente 40 s adelantado | Aceptada (tolerancia 60 s) |
| GP-16 | La fuente deja de enviar durante 90 s | Buseta `sin_senal`, ETA por horario |
| GP-17 | Buseta se sale del trazado más de `umbral_desvio_m` | Alerta de desvío a quienes tengan una alerta activa |
| GP-18 | Número lateral de otra empresa con la clave de la empresa A | Rechazada `buseta_desconocida` |
| GP-19 | 20 busetas × 1 lote cada 5 s durante 10 min | Sin crecimiento de tablas; p95 de ingesta ≤ 500 ms |

### 4.4 Pruebas de falla (FA)

| ID | Falla simulada | Comportamiento esperado |
|---|---|---|
| FA-01 | Base de datos no responde | Públicos → 503 reintentable; `salud` ok; sin caída del proceso |
| FA-02 | Fuente GPS sin datos | `seguimientoDisponible: false` o `sin_senal`; ETA por horario |
| FA-03 | Geocodificador no responde | Planificación por coordenadas/hito funciona; por texto → 503 con sugerencia |
| FA-04 | Web Push devuelve error | Bandeja interna; notificación `fallida` registrada; sin reintento infinito |
| FA-05 | Supabase Auth no responde | Públicos funcionan; protegidos → 503 |
| FA-06 | Reinicio del proceso | Grafo y parámetros se reconstruyen; alertas persisten |
| FA-07 | Excel corrupto | 400, sin cambios |
| FA-08 | Excel con filas inválidas | 200 `parcial` con detalle; filas válidas guardadas |
| FA-09 | Conexión cortada a mitad de una publicación de rodamiento | Todo o nada: no queda en estado intermedio (transacción) |
| FA-10 | Dos jefes editan el mismo rodamiento | Uno recibe 409 y debe recargar |

### 4.5 Pruebas no funcionales

**Perfil de carga PC-1** [PROPUESTO, sustituye a "carga definida" de las SPEC]:
- 50 usuarios concurrentes con la mezcla: 40 % mapa/rutas cercanas, 20 % horarios/frecuencias, 15 % busetas en vivo y ETA (sondeo cada 5 s), 10 % búsqueda, 10 % planificación, 5 % favoritos.
- 20 busetas enviando posición cada 5 s.
- Duración: 10 min, con 1 min de calentamiento. Base con el conjunto semilla ampliado a 30 rutas y 300 paraderos.

| ID | Prueba | Criterio |
|---|---|---|
| PN-REN-01 | PC-1 con `autocannon` | p95 de cada endpoint según la sección 1.2; 0 errores 5xx |
| PN-REN-02 | Pico 3× PC-1 por 2 min | Sin errores 5xx; los 429 se limitan a ingesta e inicio de sesión |
| PN-REN-03 | Importación de 5000 filas | ≤ 30 s |
| PN-REN-04 | `rutas_cercanas` con 300 paraderos y 30 rutas | p95 ≤ 100 ms en la base |
| PS-SEG-01 | Verificación TLS | Solo TLS 1.2+ |
| PS-SEG-02 | CORS | Origen no listado rechazado |
| PS-SEG-03 | Intentos de inyección en parámetros de texto | Sin efecto; respuesta 400 o resultados vacíos |
| PS-SEG-04 | Acceso directo a tablas con la clave anónima | Sin datos |
| PS-SEG-05 | `npm audit` | Sin vulnerabilidades altas ni críticas |
| PS-CMP-01 | Prototipo a 320, 375, 768 y 1280 px | Sin desplazamiento horizontal; controles accesibles |
| PS-CMP-02 | Chrome, Firefox, Safari, Edge | Flujos P01, P03, P06 y P07 completables |
| PS-CMP-03 | Contraste y objetivos táctiles | RNF-Q-08 |

### 4.6 Pruebas de sistema (PS) — flujos de punta a punta

| ID | Flujo | Pasos clave | Resultado |
|---|---|---|---|
| PS-FLU-01 | Secretaría → jefe → pasajero | Secretaría registra ruta y la asigna a empresa → jefe asigna buseta y publica rodamiento → simulador envía posiciones → pasajero ve la buseta y el ETA | La buseta aparece en el mapa de la ruta; ETA `gps` |
| PS-FLU-02 | Ruta compartida | Secretaría asigna la misma ruta a dos empresas con horarios distintos | El pasajero ve ambos horarios y las busetas de ambas |
| PS-FLU-03 | Cambio de ruta de una buseta | Rodamiento con dos turnos de la misma buseta en rutas distintas | Aparece en cada ruta solo durante su turno |
| PS-FLU-04 | Alerta de llegada | Pasajero registrado crea alerta → simulador acerca la buseta | Notificación una sola vez; segunda buseta tras el enfriamiento |
| PS-FLU-05 | Pérdida de señal | El simulador deja de enviar | `sin_senal` y mensaje; ETA pasa a `horario` |
| PS-FLU-06 | Aviso | Jefe publica aviso → pasajero lo ve en ≤ 5 s | Visible en el listado y en las rutas afectadas |
| PS-FLU-07 | Baja de ruta | Secretaría elimina una ruta con asignaciones | Advertencia; al confirmar: favoritos marcados "ya no disponible", turnos futuros cancelados |
| PS-FLU-08 | Estadísticas | 100 consultas de pasajeros a una ruta | El jefe ve el total por ruta y día |
| PS-FLU-09 | Administración | Admin crea jefe con empresa, cambia parámetro de distancia de aviso | El nuevo valor se aplica a alertas nuevas ≤ 60 s después |
| PS-GPS-02 | Frescura | Dejar pasar el umbral sin posición | Nunca se presenta como activa |
| PS-XLS-01..06 | Excel | Plantilla válida, 5000 filas, extensión falsa, ZIP corrupto, columnas faltantes, celdas con `=` | Según la sección 3.2 de la Actividad 6 |

---

## 5. Aceptación: un escenario por criterio de las SPEC

| AC | HU | Escenario Dado / Cuando / Entonces (de la SPEC) | Pruebas que lo cubren |
|---|---|---|---|
| AC-001-01 | P01 | La app abierta, el usuario accede al mapa → rutas y paradas disponibles | PI-RED-01, PI-RED-02, PS-FLU-01 |
| AC-001-02 | P02 | El usuario selecciona una ruta → el recorrido se dibuja | PI-RED-03..06 |
| AC-002-01 | P03 | El usuario consulta una ruta → días y horas de operación | PI-HOR-01..04 |
| AC-002-02 | P04 | El usuario consulta una ruta → frecuencia por franja | PI-HOR-05, PI-HOR-06 |
| AC-003-01 | P05 | El usuario visualiza una ruta y llegan datos GPS → busetas en el mapa | PI-SEG-01..03, GP-01..19, PS-FLU-01, PS-FLU-05 |
| AC-003-02 | P06 | El usuario selecciona una parada → se muestra el ETA | PU-ETA-01..10, PI-SEG-04..06 |
| AC-004-01 | P07 | El usuario ingresa origen y destino → opciones de viaje | PU-PLA-01..06, PI-PLA-01..04 |
| AC-005-01 | P08 | El usuario escribe → rutas coincidentes | PI-BUS-01..03 |
| AC-005-02 | P09 | El usuario selecciona un hito → rutas que pasan por él | PI-BUS-04, PI-BUS-05 |
| AC-006-01 | J01 | El jefe asigna un conductor → la asignación queda registrada | PI-OPE-01..04 |
| AC-006-02 | J02 | El jefe ingresa datos y guarda → quedan registrados | PI-OPE-10, PI-HOR-06 |
| AC-006-03 | J03 | El jefe carga un archivo → los datos se actualizan | PS-XLS-01..06, FA-07, FA-08 |
| AC-006-04 | J04 | El jefe define el rodamiento y guarda → queda activo para el día | PU-ROD-01..04, PI-OPE-05..09, PS-FLU-01 |
| AC-007-01 | SM01 | La Secretaría registra una ruta → queda asignada a la empresa | PI-SEC-01..04, PS-FLU-02 |
| AC-007-02 | SM02 | La Secretaría edita → los datos se actualizan | PI-SEC-05, PI-CON-01 |
| AC-007-03 | SM03 | La Secretaría elimina una ruta → se elimina | PI-SEC-06, PI-SEC-07, PS-FLU-07 |
| AC-007-04 | SM04 | La Secretaría gestiona paraderos → se actualizan | PI-SEC-08 |
| AC-007-05 | SM05 | La Secretaría publica un cambio → el aviso es visible | PI-SEC-09, PI-AVI-01..03 |
| AC-008-01 | P10 | Usuario registrado marca favorita → aparece en su lista | PI-FAV-01..04 |
| AC-009-01 | P11 | El usuario activa la notificación y la buseta llega a la distancia → recibe aviso | PU-ALE-01..05, PI-ALE-01..04, PS-FLU-04 |
| AC-010-01 | P12 | Sin cuenta, accede → consulta toda la información pública | Todos los PI públicos sin token; PS-FLU-01 |
| AC-011-01 | J05 | El jefe redacta y publica → el aviso es visible | PU-AVI-01..05, PI-AVI-01..03, PS-FLU-06 |
| AC-012-01 | J06 | El jefe consulta estadísticas → ve los datos | PI-EST-01..03, PS-FLU-08 |
| AC-013-01 | A01 | El admin gestiona un usuario → se actualiza | PI-ADM-01, PI-ADM-02 |
| AC-013-02 | A02 | El admin configura roles → permisos actualizados | PI-ADM-03 |
| AC-013-03 | A03 | El admin gestiona una empresa → se actualiza | PI-ADM-05 |
| AC-013-04 | A04 | El admin ajusta parámetros → cambia la configuración | PI-ADM-04, PS-FLU-09 |
| AC-013-05 | A05 | El admin publica un aviso → es visible | PU-AVI-03, PI-AVI-03 |

Cobertura: los 28 criterios de aceptación tienen al menos una prueba de integración o de sistema. Los flujos alternativos y de excepción de cada HU (sección 3 de la Actividad 3) están cubiertos por las pruebas `PI-*`, `FA-*` y `GP-*` de las tablas anteriores.

---

## 6. Plan de calidad

### 6.1 Objetivos
1. Cumplir los 28 criterios de aceptación.
2. Cumplir RNF-01..03 y los objetivos de la sección 1.2 una vez aprobados por el equipo.
3. Llegar a la demo con un conjunto de datos de ejemplo, un simulador y un guion de pruebas repetible.

### 6.2 Entornos

| Entorno | Base de datos | GPS | Uso |
|---|---|---|---|
| Local | PostgreSQL con PostGIS en contenedor o instalado | Simulador | Desarrollo y pruebas unitarias/integración |
| Pruebas | Proyecto Supabase de pruebas (gratuito) | Simulador | Sistema, no funcionales, aceptación |
| Demo | Proyecto Supabase de demo | Simulador (o fuente real si hay acuerdo) | Presentación |

### 6.3 Actividades y criterios

| Etapa | Entrada | Actividad | Criterio de salida |
|---|---|---|---|
| Diseño | Actividades 2–6 aprobadas | Revisión cruzada de coherencia | Sin contradicciones abiertas entre modelo, casos de uso, API y datos |
| Construcción | Historias priorizadas (orden: imprescindibles primero, contexto §10) | Desarrollo con pruebas unitarias | Cobertura ≥ 80 %; sin errores de lint |
| Integración | Módulo terminado | Pruebas de integración y de contrato | 100 % de endpoints del módulo con caso feliz y de error |
| Sistema | Todos los imprescindibles | Flujos PS y de falla FA | Sin defectos críticos ni altos abiertos |
| Aceptación | Sistema estable | Revisión de los 28 AC con el equipo | 28/28 aprobados |
| Cierre de demo | Aceptación | Ensayo con simulador y plan de contingencia | Guion ejecutado dos veces sin fallos |

Orden de construcción [PROPUESTO], alineado con la prioridad del contexto (§10): (1) Red y horarios (P01–P04, SM01–SM04); (2) Búsqueda (P08, P09); (3) Operación: asignación, rodamiento, Excel (J01–J04); (4) Seguimiento y ETA (P05, P06) con simulador; (5) Planificación (P07); (6) Administración (A01–A04); (7) Deseables: avisos (J05, SM05, A05), favoritas (P10), estadísticas (J06); (8) Opcional: notificaciones (P11).

### 6.4 Definición de terminado (por historia)
- Código revisado por otra persona del equipo.
- Pruebas unitarias e integración de la historia pasando en CI.
- Endpoint documentado en `openapi.yaml` y validado por el contrato.
- Errores y mensajes de los flujos alternativo y de excepción implementados.
- Sin datos personales en logs.
- Trazabilidad HU → RF → AC → prueba actualizada.

### 6.5 Gestión de defectos

| Severidad | Definición | Plazo de corrección antes de la demo |
|---|---|---|
| Crítica | Pérdida de datos, fuga entre empresas, caída del servicio | Inmediato |
| Alta | Un flujo imprescindible no se puede completar | Antes de cerrar la etapa |
| Media | Flujo alternativo incorrecto, mensaje errado | Antes de aceptación |
| Baja | Cosmético | Si hay tiempo |

### 6.6 Métricas
Cobertura por módulo, endpoints con prueba / total, AC aprobados / 28, defectos abiertos por severidad, p95 por endpoint bajo PC-1, disponibilidad medida en la ventana de demo.

### 6.7 Roles [PROPUESTO]
Responsable de calidad (revisa el cumplimiento de la definición de terminado), desarrolladores (pruebas unitarias e integración), responsable de datos de prueba y simulador, y el equipo completo para la aceptación.

---

## 7. Matriz de riesgos

Probabilidad (P) e impacto (I) en escala 1 a 5. Exposición = P × I. Nivel: 1–6 bajo, 7–12 medio, 13–25 alto.

| ID | Riesgo | P | I | Exp. | Nivel | Mitigación | Disparador / señal | Fuente |
|---|---|---|---|---|---|---|---|---|
| R-01 | No hay acuerdo con las empresas para obtener sus posiciones GPS | 4 | 5 | 20 | Alto | ETA por horario y frecuencia (ADR-005); fuente detrás de un puerto; simulador para la demo | Sin respuesta de las empresas antes de integración | OPEN-Q-003 |
| R-02 | El formato de datos GPS de cada empresa es distinto del canónico | 4 | 3 | 12 | Medio | Adaptadores de entrada por empresa; el dominio no cambia | Primera muestra real de datos | contexto §8.1 |
| R-03 | Los datos de rutas y paraderos de la Secretaría llegan incompletos o tarde (BR-08) | 4 | 4 | 16 | Alto | Importación por Excel con reporte de errores; datos de ejemplo marcados como ficticios; estados `pendiente_actualizacion` | Falta de trazados para más del 30 % de las rutas | BR-08 |
| R-04 | El rodamiento no se carga o se carga tarde → no hay busetas visibles | 4 | 4 | 16 | Alto | Plantilla Excel; mensajes claros "sin rodamiento publicado"; ETA por horario | Rodamientos publicados menos del 50 % de los días | OPEN-Q-007 |
| R-05 | Límites del hosting y de Supabase gratuitos (arranque en frío, pausa por inactividad, cuotas) | 4 | 3 | 12 | Medio | Ping a `/salud`; verificar límites vigentes antes de la demo; esquema reproducible | Primera respuesta mayor que 3 s | Prototipo con tecnologías gratuitas |
| R-06 | Valores de RNF de las SPEC no alcanzables o ambiguos (0.5 s, 0.2 s, 99.9 %, "carga definida") | 4 | 3 | 12 | Medio | Objetivos ajustados del prototipo (sección 1.2) y perfil PC-1 sujetos a aprobación del equipo | Sin aprobación antes de pruebas no funcionales | SPEC-003, 007 |
| R-07 | Modelo de rutas compartidas, variantes y circulares complejo de implementar | 3 | 3 | 9 | Medio | Modelo ya soporta los casos; pruebas PS-FLU-02 y 03; implementar primero lineales y agregar circulares después | Retraso en el módulo Red | contexto §8.2 |
| R-08 | Privacidad de la ubicación y de datos personales | 3 | 4 | 12 | Medio | No guardar ubicación del pasajero; eventos anónimos; datos mínimos de conductor; revisión normativa (PRI-07) | Pedido de guardar historial de viajes | RNF-01 |
| R-09 | Estado de las decisiones: partes del diseño siguen siendo propuestas sin aprobar | 3 | 4 | 12 | Medio | Etiquetas [PROPUESTO] en todos los documentos; el equipo aprueba por actividad | Desarrollo iniciado sin aprobación | Instrucciones del proyecto |
| R-10 | Observer en memoria y caché de grafo no escalan a varias instancias | 2 | 3 | 6 | Bajo | Una instancia (documentado); si crece, mover a cola o a Realtime | Segunda instancia | ADR-012 |
| R-11 | Límites de Nominatim (1 petición por segundo, política de uso) | 3 | 2 | 6 | Bajo | Caché 24 h; planificación por coordenadas e hitos como alternativa | Respuestas 429 del geocodificador | ADR |
| R-12 | Datos GPS de baja calidad (saltos, retrasos, relojes desfasados) | 3 | 3 | 9 | Medio | Validación de zona, tolerancia de 60 s, velocidad por defecto, umbral de obsolescencia | Quejas por busetas "saltando" | GP-12, GP-15 |
| R-13 | Web Push con soporte desigual entre navegadores y sistemas | 3 | 3 | 9 | Medio | Bandeja interna siempre disponible; notificaciones son prioridad opcional | Usuarios sin recibir avisos | OPEN-Q-001 |
| R-14 | Archivo Excel malicioso o con fórmulas (inyección) | 2 | 4 | 8 | Medio | Validación de firma, límites, tratamiento de texto como texto | Archivo con macros o fórmulas | SEG-06, SEG-07 |
| R-15 | Concurrencia: dos jefes o la Secretaría y el jefe editan lo mismo | 2 | 3 | 6 | Bajo | Control de versión (RNF-02); mensaje de recarga | Informes de "mis cambios desaparecieron" | RNF-02 |
| R-16 | Preguntas abiertas del contexto (OPEN-Q-001..007) se responden de forma distinta a los supuestos S-xx | 3 | 3 | 9 | Medio | Los supuestos están aislados (S-xx) y el modelo los absorbe: p. ej. jefe de varias empresas requeriría una tabla de pertenencia, no un rediseño | Respuesta del equipo que contradiga un supuesto | contexto §9 |
| R-17 | Alcance de Villamaría sin definir (OPEN-Q-006) | 3 | 2 | 6 | Bajo | Villamaría es contenido (rutas/paraderos), no código; se puede incluir u omitir sin cambiar el sistema | Decisión del equipo | OPEN-Q-006 |
| R-18 | El frontend no esté listo para la demo | 3 | 3 | 9 | Medio | Prototipo de la Actividad 4 como referencia; contrato OpenAPI para trabajo en paralelo; datos semilla | Retraso del frontend | — |

---

## 8. Trazabilidad de la Actividad 7

| Elemento | Se relaciona con |
|---|---|
| RNF-01 / RNF-02 / RNF-03 | SEG-01, PI-LOG-01 / PI-CON-01..04 / PS-CMP-01..03 |
| RNF por SPEC | Sección 1.2 → PN-REN-01 |
| Escenarios de GPS | HU-P05, HU-P06, HU-P11 → GP-01..19 |
| Escenarios de ETA | HU-P06 → PU-ETA-01..10, PI-SEG-04..06 |
| Fallas | CT-01..CT-08 (Actividad 3) → FA-01..FA-10 |
| 28 AC | Sección 5 |
| Riesgos | Sección 7 → decisiones ADR de la Actividad 5 |
