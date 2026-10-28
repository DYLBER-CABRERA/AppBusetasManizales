# Trazabilidad con las SPECs y desviaciones aceptadas

Resultado de revisar las 13 SPECs (SPEC-001 a SPEC-013) contra el prototipo. Léelo para saber **qué se cumple, qué cambió y qué se desvía a propósito**. La falta de GPS real no impide cumplir ninguna SPEC: el simulador entra por el mismo caso de uso que usaría un GPS real y el ETA por horario responde a OPEN-Q-001 («sistema de respaldo si falla el GPS»).

## 1. Trazabilidad SPEC → prototipo

| SPEC | Historias | Estado en el prototipo | Notas |
|---|---|---|---|
| 001 Consulta de rutas | P01, P02 | ✅ | Sin rutas cerca → paradero más cercano. Ruta inexistente → rutas cercanas (doc 01 §3.1) |
| 002 Horarios | P03, P04 | ✅ | Sábado de Sideral = «Información pendiente de actualización». Frecuencia variable → rango |
| 003 Seguimiento y ETA | P05, P06 | ✅ | Posiciones simuladas. Sin señal → ETA por horario. Sin busetas → «No hay busetas en servicio…» |
| 004 Planificación | P07 | 🟡 | Solo rutas directas. **Transbordos fuera** (D-P07) |
| 005 Búsqueda y filtros | P08, P09 | ✅ | Por número, nombre, barrio e hito; sin tildes |
| 006 Jefe de operaciones | J01–J04 | 🟡 | **J03 (Excel) fuera**, botón desactivado. **J02:** el jefe no crea rutas (D-P13). **J01:** confirma al reemplazar (D-P15) |
| 007 Secretaría | SM01–SM05 | ✅ | SM01 con trazado simplificado (línea entre paraderos) |
| 008 Favoritas | P10 | ✅ | Requiere sesión (BR-02) |
| 009 Notificaciones | P11 | 🟡 | Telegram y app abierta; **sin push con la app cerrada**. Avisa también si la buseta se desvía (D-P14). En Telegram el `chat_id` hace de identidad (D-P08) |
| 010 Uso sin cuenta | P12 | ✅ | Todo lo público sin token |
| 011 Avisos generales | J05 | ✅ | Límite de longitud por parámetro |
| 012 Estadísticas | J06 | 🟡 | Con 14 días de uso simulado (doc 01 §2.9) |
| 013 Administrador | A01–A05 | 🟡 | A02 (roles) en solo lectura: los 4 roles son fijos |

Estado de aprobación de las SPECs: la 001 a la 004 figuran como aprobadas (2026-10-06); de la 005 a la 013 figuran como borrador o «aprobación humana». Para la clase no afecta, pero conviene aprobarlas antes de la entrega formal.

## 2. Requisitos no funcionales: qué se cumple y qué se desvía

| Requisito (SPECs) | Prototipo | Decisión |
|---|---|---|
| **RNF-01** HTTPS/TLS 1.2+ y sin datos personales en logs | La demo corre por **HTTP en la red local**. Supabase y los mapas sí usan HTTPS. Los logs no guardan tokens ni ubicación | **Desviación aceptada** para la demo. En un despliegue real va detrás de HTTPS |
| **RNF-02** Concurrencia sin perder datos | Campo `version` y 409 `CONFLICTO_VERSION` | Se cumple |
| **RNF-03** Funciona en navegadores móviles (001–005, 008–013) y desde 320 px | El pasajero usa **APK Android y Telegram**, no el navegador. Los paneles web son de escritorio (≥ 1024 px) | **Desviación aceptada**: la presentación define Flutter. SPEC-006 y 007 dicen «escritorio… desde 320 px», que parece un error de redacción |
| Rendimiento 0,5–2,5 s (todas) | Objetivo local. Se mide con `curl -s -o /dev/null -w "%{time_total}\n" <url>` | Se cumple como objetivo; no hay prueba de carga (D-P06) |
| Actualización 0,5 s (SPEC-003) | El simulador emite cada 3 s y la app anima el movimiento entre posiciones. El respaldo REST refresca cada 5 s | **Desviación aceptada**: 0,5 s exigiría emisión continua que ningún GPS real hace |
| Actualización 0,2 s (SPEC-007) | Los paneles de gestión muestran el dato al guardar | **No aplica** a una pantalla de gestión; parece un valor propuesto por el modelo sin revisar |
| Disponibilidad 99–99,9 % (la mayoría) y **20 % en SPEC-001** | El backend corre en tu portátil durante la demo | **No se mide.** El 20 % de SPEC-001 parece un error de digitación; confírmalo con el equipo |

## 3. Decisiones tomadas en esta revisión

| ID | Decisión |
|---|---|
| D-P13 | El jefe no crea rutas: manda BR-03 sobre el texto de HU-J02 |
| D-P14 | Alerta de desvío por Telegram y por WebSocket |
| D-P15 | Reemplazar una asignación exige confirmación (`confirmarReemplazo=true`) |
| D-P16 | Villamaría es obligatoria en el demo |

Detalle de textos y flujos alternativos: `docs/01-alcance-y-datos-simulados.md` §2.9 y §3.1. Contrato: `docs/03-contrato-api.md`.
