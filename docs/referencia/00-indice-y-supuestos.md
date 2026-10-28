# BusetasApp — Entregables de diseño (Actividades 2 a 7)

Prototipo gratuito para consultar rutas de buses de Manizales. Este documento es el punto de entrada: índice, leyenda de etiquetas y lista de supuestos.

## 1. Índice de entregables

| Actividad | Archivo | Contenido |
|---|---|---|
| 2. Modelo de dominio | `01-actividad-2-dominio.md` | Entidades, relaciones, cardinalidades, estados y transiciones, diagrama conceptual |
| 3. Casos de uso y flujos | `02-actividad-3-casos-de-uso.md` | UC por rol, flujos principal/alterno/error, datos faltantes y fallas externas, diagramas de secuencia y actividad |
| 4. UX y prototipos | `03-actividad-4-ux-prototipos.md` + `prototipo.html` | Flujos, pantallas, wireframes, componentes, estados de UI; prototipo de alta fidelidad navegable |
| 5. Arquitectura | `04-actividad-5-arquitectura.md` | Módulos, puertos y adaptadores, integraciones, ADR, diagramas |
| 6. Datos y API | `05-actividad-6-datos-api.md` + `esquema.sql` + `openapi.yaml` | Modelo ER, restricciones e índices, contratos, formatos, autenticación, GPS y mapas, datos inválidos/desactualizados |
| 7. Calidad y pruebas | `06-actividad-7-calidad-pruebas.md` | RNF medibles, seguridad/privacidad/disponibilidad, pruebas (incluye GPS y ETA), plan de calidad, matriz de riesgos |

Orden de lectura sugerido: 2 → 3 → 5 → 6 → 4 → 7.

## 2. Leyenda de etiquetas

- **[FUENTE]**: dato tomado de los documentos del proyecto.
- **[PROPUESTO]**: decisión técnica o de diseño propuesta; no está aprobada.
- **[SUPUESTO S-xx]**: vacío de información completado con una propuesta razonable (lista abajo).
- Único par de decisiones confirmadas: **Supabase (Postgres + PostGIS + Auth)** como base de datos y uso de **tecnologías gratuitas** en un prototipo.

Ninguna propuesta sustituye algo ya aprobado.

## 3. Supuestos

| ID | Supuesto | Dónde impacta |
|---|---|---|
| S-01 | La posición GPS llega por una fuente configurable por empresa (HTTP con clave `X-Clave-Fuente`) y existe un simulador para la demostración | Arq., API, Pruebas |
| S-02 | Las HU del jefe de operación (HU-J02/J03) se limitan a datos operativos (horarios, frecuencias, conductores, busetas, turnos, Excel); nunca rutas ni paraderos (BR-03/04) | Casos de uso, API |
| S-03 | Una ruta puede ser compartida por varias empresas mediante `ServicioRuta` (ruta × empresa), con horario y frecuencia propios y códigos público/interno opcionales | Dominio, Datos |
| S-04 | Una asignación es (servicio, buseta, conductor); si la misma buseta y servicio ya tiene otro conductor, se pide `confirmarCambio` | Dominio, API |
| S-05 | `tipo_recorrido` puede ser lineal o circular (sentidos ida/vuelta/circular) | Dominio, Datos |
| S-06 | La buseta se identifica por número lateral; la placa es opcional; una buseta puede tener varias asignaciones/turnos por día | Dominio, Datos |
| S-07 | Villamaría es dato (zona/caja geográfica), no código | Datos |
| S-08 | El seguimiento usa sondeo (polling) cada 5 s | Arq., RNF |
| S-09 | Notificaciones por Web Push más bandeja interna | Arq., UX |
| S-10 | Distancia de aviso de llegada por defecto 300 m, configurable | Datos, RNF |
| S-11 | Un jefe pertenece a una sola empresa; el administrador puede publicar avisos (origen aplicativo) y ver estadísticas globales | Casos de uso, API |
| S-12 | Los eventos de uso son anónimos | Privacidad |
| S-13 | Las cuentas las crea el administrador; el pasajero se autorregistra | Seguridad, API |
| S-14 | El calendario de festivos lo mantiene el administrador | Dominio, Datos |
| S-15 | Metas de RNF del prototipo (p95, polling 5 s, cambio de Secretaría visible ≤10 s) en lugar de las de producción; requieren aprobación | Calidad |
| S-16 | La ubicación del usuario no se almacena | Privacidad |
| S-17 | Borrado lógico en entidades principales | Datos |
| S-18 | Importación de Excel por fila: las filas válidas se conservan y los errores se listan | Casos de uso, API |
| S-19 | Si no hay GPS, el ETA usa horario/frecuencia (fuente `gps` \| `horario` \| `no_disponible`) | Casos de uso, Calidad |
| S-20 | Planificación de viaje: máximo 1 transbordo, 3 opciones y radio de caminata configurable | API, Pruebas |
| S-21 | La ruta de una buseta se deduce del rodamiento publicado (`turno_vigente`) cuando la fuente GPS no la informa | Arq., Pruebas |

## 4. Datos del prototipo

Los datos de `prototipo.html` son ilustrativos. Provienen del contexto del proyecto: horarios y frecuencias de Sideral, Socobuses (primer/último servicio) y Serviturismo, hitos y laterales 2683 y 2676. Son ficticios: el código 18 de Socobuses, los demás laterales, nombres de paraderos y conductores.
