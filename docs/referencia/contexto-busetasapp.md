# BusetasApp Manizales — Contexto del proyecto para agentes

> **Propósito del documento:** servir como contexto único para los agentes que construyen la aplicación (historias de usuario, especificaciones, diseño, desarrollo).
> Combina el alcance funcional del proyecto con la información real de operación levantada en tres empresas de busetas de Manizales: **Socobuses, Sideral y Serviturismo**.
> Las decisiones tecnológicas (plataforma, APIs, base de datos, arquitectura) **no se definen aquí**; se toman después de las historias de usuario.

---

## 1. Problema

El público desconoce las rutas, los horarios y los tiempos de llegada de las busetas en Manizales. No hay una forma sencilla de saber qué buseta pasa por dónde, a qué hora, ni cuánto falta para que llegue a una parada.

Hallazgos de campo que refuerzan el problema:
- Los usuarios locales conocen la red y se orientan por **hitos urbanos** (Catedral, El Cable, Carrera 23, Fundadores), no por paraderos formales.
- Las preguntas que los pasajeros hacen al conductor son casi exclusivamente sobre **cobertura de la ruta y horarios**.
- Cada empresa identifica sus rutas de forma distinta (ver sección 6), lo que dificulta una consulta unificada.

## 2. Solución

**BusetasApp** es una aplicación para consultar las rutas de las busetas de Manizales. Permite:
- Ver rutas y paradas en un mapa.
- Consultar horarios, frecuencias y días de operación.
- Ver la ubicación de las busetas y el tiempo estimado de llegada (ETA) (ver restricción en sección 9, OPEN-Q-003).
- Planificar un viaje indicando origen y destino.
- Buscar rutas por número, nombre, barrio o punto de interés.

Incluye módulos de gestión para el **jefe de operaciones** de cada empresa, para la **Secretaría de Movilidad** y para el **administrador** de la plataforma.

## 3. Objetivos

**General:** facilitar la movilidad de los pasajeros de buseta en Manizales.

**Específicos:**
- Dar a conocer las rutas de las busetas.
- Informar horarios de funcionamiento y días hábiles.
- Mostrar la ubicación de las busetas y el ETA.
- Ayudar a planificar un viaje con origen y destino.

## 4. Roles (4 en total)

> **Cambios respecto a la versión anterior:** el **módulo y rol de conductor se eliminan**. "Administrador de la empresa" pasa a llamarse **jefe de operaciones**. La **Secretaría de Movilidad** es un rol propio de la plataforma. Se agrega el **administrador** de la app.

| Rol | Descripción | Puede | No puede |
|-----|-------------|-------|----------|
| **Pasajero** | Usuario final. Puede usar la app sin cuenta. | Consultar rutas, horarios, mapa y ubicación; planificar viajes; buscar rutas. Con cuenta: guardar favoritas y recibir notificaciones. | Modificar información operativa. |
| **Jefe de operaciones** | Responsable operativo de una empresa de busetas (equivale al antiguo "administrador de la empresa"). | Asignar a los conductores/busetas las rutas ya registradas en la plataforma; definir el rodamiento del día; publicar avisos generales (cambios, suspensiones, horarios de festivos); consultar estadísticas básicas. | Crear, editar o eliminar rutas ni paraderos. |
| **Secretaría de Movilidad** | Autoridad que alimenta la base de datos de la plataforma. | Imponer/asignar rutas a cada empresa; agregar, editar y eliminar rutas; gestionar los paraderos de la ciudad; registrar cualquier cambio de movilidad en la ciudad (cierres, desvíos, obras, condiciones). | Definir rodamientos ni asignaciones diarias de las empresas. |
| **Administrador** | Dueño de la plataforma (el desarrollador). Control total de la app. | Todo lo anterior más gestión de usuarios, roles, empresas y configuración global. | — |

**Nota importante:** los **conductores ya no son usuarios** de la plataforma. Siguen existiendo como **datos** (nombre, asignación a buseta y ruta) dentro del rodamiento que define el jefe de operaciones.

## 5. Alcance funcional

- **Consulta de rutas:** catálogo con recorrido dibujado en mapa, paradas y sentido del trayecto.
- **Consulta de horarios:** hora de inicio y fin de operación por ruta, frecuencia y días de servicio (lunes a viernes, sábados, domingos y festivos).
- **Seguimiento en tiempo real y ETA:** ubicación de busetas activas y tiempo estimado de llegada a una parada (sujeto a OPEN-Q-003).
- **Planificación de viaje:** origen y destino; la app sugiere qué ruta o rutas tomar.
- **Búsqueda y filtros:** por número o nombre de ruta, barrio, sector o punto de interés (universidades, hospitales, terminal, hitos como Catedral, El Cable, Carrera 23, Fundadores). La búsqueda por hito urbano es prioritaria porque así se orientan los usuarios.
- **Favoritas:** guardar rutas o paradas frecuentes (requiere cuenta).
- **Notificaciones:** aviso cuando la buseta esté por llegar a una parada de interés (requiere cuenta).
- **Uso sin cuenta:** cualquier persona consulta sin registrarse.
- **Avisos generales:** publicados por el jefe de operaciones (cambios, suspensiones, horarios de festivos). Los cambios de movilidad de ciudad los registra la Secretaría.
- **Asignación operativa y rodamiento (jefe de operaciones):** asignar rutas existentes a conductores/busetas y definir el rodamiento del día.
- **Gestión de rutas, paraderos y cambios de ciudad (Secretaría de Movilidad):** asignar rutas a cada empresa, gestionar paraderos y registrar cambios de movilidad.
- **Estadísticas básicas:** de uso de la app, para el jefe de operaciones.
- **Administración global:** gestión de usuarios, roles y control total (administrador).

## 6. Fuera de alcance

- Pago de pasajes, tarjetas de recarga y cualquier manejo de dinero.
- Transporte fuera de Manizales: taxis, transporte informal y rutas intermunicipales.
- **Módulo y rol de conductor** (eliminado).
- Registro de planillas, control de nómina, recaudo y registradoras de pasajeros de las empresas (son procesos internos que la app no reemplaza).
- Definiciones tecnológicas (plataforma, APIs, base de datos, arquitectura).

## 7. Reglas de negocio

- **BR-01:** Cualquier persona puede consultar rutas, horarios y mapa sin crear cuenta.
- **BR-02:** Guardar favoritas y recibir notificaciones requiere usuario registrado.
- **BR-03:** El jefe de operaciones solo asigna a conductores/busetas las rutas ya registradas en la plataforma y define el rodamiento del día; no puede crear, editar ni eliminar rutas ni paraderos.
- **BR-04:** Solo la Secretaría de Movilidad puede agregar, editar o eliminar rutas, paraderos y cambios generales de movilidad de la ciudad, y es quien impone las rutas a cada empresa.
- **BR-05:** Solo el jefe de operaciones publica avisos generales de su empresa.
- **BR-06:** (reemplaza a la antigua BR-06 de conductores) Los conductores no tienen acceso a la plataforma; aparecen únicamente como datos del rodamiento.
- **BR-07:** El administrador tiene control total sobre la plataforma, incluida la gestión de usuarios y roles.
- **BR-08:** Los datos de rutas, paraderos y cambios de ciudad provienen de la información de la Secretaría de Movilidad; la base de datos se alimenta de esa fuente.

## 8. Realidad operativa de las empresas (insumo para modelo de datos y reglas)

### 8.1 Comparativo

| Aspecto | Socobuses | Sideral | Serviturismo |
|---------|-----------|---------|--------------|
| **Rutas** | Villamaría, La Enea (directa), Bosques de La Enea (variante) y otras | El Cable (Ruta 39, primordial), Centro (Ruta 22), San Sebastián / Ansebas | Solo dos: Villamaría y La Enea |
| **Identificación** | Código numérico único por ruta. Externo (en la vía): solo números. Interno: alfanumérico (variantes, ramales, despachos especiales) | Números y códigos específicos (39, 22) | **Sin código de ruta**: se identifica por el **número lateral** de la buseta (ej. 2676 → Villamaría, 2683 → La Enea) |
| **Asignación** | Software de rodamiento automático, con 8 días de anticipación (hasta 15). Una buseta opera varias rutas en el día | Rodamiento diario en Excel enviado el día anterior (hora de salida, conductor, número lateral) | Tabla de rodamiento en Excel. La buseta intercala Villamaría y La Enea (rutas circulares) |
| **Horario L–V** | Primera salida 5:30 AM; última salida 10:00 PM; cierre total 11:00 PM | 4:45 AM – 9:30 PM | L–S: 4:40 AM – 10:00 PM |
| **Domingos y festivos** | Opera ~40% de capacidad (menos busetas, esperas más largas) | 6:00 AM – 9:00 PM | 4:40 AM – 9:00 PM |
| **Sábados** | Capacidad plena (L–S) | No especificado en la fuente | Mismo horario que L–V |
| **Frecuencias** | Villamaría: 10 min en hora alta, 15 min en valle. La Enea directa: cada 6 min. Bosques de La Enea: cada 6 min. En el tramo común de La Enea la frecuencia combinada es cada 3 min | Cable: 8–10 min fijos. Centro: ~15 min. San Sebastián/Ansebas: cada hora | Cada 4 min |
| **Duración del recorrido** | Estándar 50 min (30–45 en trayectos cortos). Tope máximo de 1 hora | No especificada | Vuelta completa hasta ~2 h con congestión. Meta: 10 vueltas diarias por buseta |
| **Horas pico** | Congestión en Av. Centro, Av. Santander y Av. Paralela a la altura de la Calle 55 | Tarde 5:00–6:30/7:00 PM. Críticos: Centro, Terminal, La Fuente | Mañana 6:00–10:00 AM y tarde 4:30–8:00 PM. Críticos: entrada a Villamaría y Av. Santander (Parque del Agua, Batallón, Expoferias, San Marcel) |
| **GPS / monitoreo** | GPS integrado en todas las busetas, rastreado desde la oficina central y cruzado con la hora de salida del rodamiento | La mayoría tiene GPS y cámaras. El rastreo completo lo gestiona el área de sistemas; la sede de despacho verifica llegadas a puntos clave (ej. Parque de Caldas) | Algunas unidades con GPS, gestionado por un área técnica externa al despacho. El seguimiento es principalmente por planilla física |
| **Control en campo** | Controladores en cabecera (planilla: placa, número lateral, conductor, documento) y supervisores intermedios (cinturón y sobrecupo) | "Recorredores" en La Autónoma, Berlón, Calle 22 y San Sebastián; evitan el "enganche" (competir pegados por pasajeros) | Único punto de control de tiempo: central de despacho, con tarjeta de operación obligatoria |
| **Desvíos** | El conductor puede desviarse por decisión propia ante bloqueos repentinos y debe notificar de inmediato. En casos de gran escala decide el Jefe de Personal | Requiere autorización previa del jefe inmediato (llamada o WhatsApp). Sin autorización puede haber multa | Requiere autorización del despacho. No puede tomar alternativas por su cuenta |
| **Varadas** | Se reporta por grupos de WhatsApp; se envía una buseta de refresco | Grupo de WhatsApp; mantenimiento envía otra buseta para transbordo. Si una ruta prioritaria queda sin servicio, se toman busetas de la ruta del Centro | Se reporta al coordinador operativo para su registro |
| **Paraderos** | La norma exige parar solo en paraderos; el conductor puede parar fuera para adultos mayores o personas con discapacidad | En la práctica se para fuera de paraderos para no dejar pasajeros | Paradas estrictas en paraderos definidos |
| **Capacidad** | — | — | 19 puestos sentados, sin pasajeros de pie |
| **Otros** | Supervisión de la Secretaría de Movilidad: rutas, estado mecánico/higiénico y documentación. Talleres propios y revisión diaria | Oficinas en Campo Hermoso (llegando a Berlón). Exclusividad en las rutas Cable y San Sebastián. Competencia en Centro con Territurismo, Gran Caldas y Socobuses | La Secretaría de Movilidad capacita conductores e inspecciona la flota |

### 8.2 Implicaciones para el producto

1. **Una ruta no tiene un único esquema de identificación.** El modelo debe soportar: nombre de ruta, código público numérico (opcional, Serviturismo no lo tiene), código interno alfanumérico (opcional) y empresa propietaria.
2. **Hay rutas compartidas entre empresas** (Villamaría y La Enea las operan Socobuses y Serviturismo). La app debe permitir que una misma ruta/corredor tenga varias empresas, cada una con su propio horario y frecuencia.
3. **Los horarios dependen de empresa, ruta y tipo de día** (L–V, sábado, domingo/festivo), con inicio, última salida y cierre. El caso de Sideral los sábados está sin definir.
4. **Las frecuencias son variables** (hora alta vs. valle, frecuencia combinada por variantes) y no un valor fijo único.
5. **Existen variantes de una ruta** (ej. Bosques de La Enea sobre el tronco de La Enea) que comparten tramo.
6. **El rodamiento es el eje de la operación del jefe de operaciones:** vincula ruta, hora de salida, buseta (número lateral) y conductor. Una misma buseta puede cambiar de ruta durante el día.
7. **Los desvíos y varadas son frecuentes**, y las empresas los gestionan por WhatsApp. En la app deben reflejarse como avisos del jefe de operaciones o cambios registrados por la Secretaría.
8. **Los tiempos reales difieren del programado** por congestión; el ETA no puede basarse solo en la tabla.
9. **La paradas reales no siempre coinciden con los paraderos formales**; conviene priorizar la búsqueda por hito urbano y cobertura de ruta sobre el detalle de paraderos.

## 9. Preguntas abiertas

| ID | Pregunta | Responsable | Estado |
|----|----------|-------------|--------|
| OPEN-Q-001 | ¿Las notificaciones salen fuera de la app o son avisos dentro de ella? | Equipo | Pendiente |
| OPEN-Q-002 | ¿Qué ocurre con el ETA cuando una buseta no reporta su posición? | Equipo | Pendiente |
| OPEN-Q-003 | **Con el módulo de conductor eliminado, ¿de dónde sale la ubicación en tiempo real?** Las empresas tienen GPS propio con rastreo interno (Serviturismo casi no lo usa). ¿Se integrará con esos sistemas, se usará solo ETA programado por frecuencias/horarios, o se pospone el tiempo real? | Equipo | Pendiente |
| OPEN-Q-004 | ¿El jefe de operaciones pertenece a una sola empresa y solo ve/gestiona los datos de esa empresa? | Equipo | Pendiente |
| OPEN-Q-005 | ¿El administrador también puede publicar avisos y consultar estadísticas globales? | Equipo | Pendiente |
| OPEN-Q-006 | ¿Las rutas de Villamaría (municipio vecino, operadas por Socobuses y Serviturismo) entran en el alcance o siguen como "ampliación opcional"? | Equipo | Pendiente |
| OPEN-Q-007 | ¿Cómo se maneja el rodamiento: carga manual en la app, carga de Excel, o integración con el software de cada empresa? | Equipo | Pendiente |

## 10. Priorización

| Prioridad | Funcionalidades |
|-----------|-----------------|
| **Imprescindible** | Consulta de rutas, horarios, seguimiento/ETA (según OPEN-Q-003), planificación de viaje, búsqueda y filtros, módulo del jefe de operaciones, módulo de la Secretaría de Movilidad, módulo del administrador |
| **Deseable** | Favoritas, avisos generales, estadísticas básicas |
| **Opcional** | Notificaciones, ampliación a Villamaría (ver OPEN-Q-006) |

## 11. Entregables y criterios de éxito

- Aplicación funcional con todas las funcionalidades **Imprescindibles** demostrables.
- Historias de usuario bien construidas (formato estándar, INVEST) para los **cuatro roles**: pasajero, jefe de operaciones, Secretaría de Movilidad y administrador.

## 12. Requisitos no funcionales (fijos)

Los RNF medibles (tiempos, porcentajes, cadencias) se generan por SPEC y sus valores los define el equipo; el agente no inventa cifras. Los siguientes aplican a todas las SPEC:

| ID | Categoría | Requisito verificable |
|----|-----------|----------------------|
| RNF-01 | Seguridad | Los datos viajan cifrados (HTTPS/TLS 1.2+) y no se registran credenciales ni datos personales en logs |
| RNF-02 | Integridad | Las actualizaciones concurrentes del mismo recurso no pierden datos (control de versiones o bloqueo) |
| RNF-03 | Compatibilidad | La interfaz funciona en navegadores móviles y de escritorio modernos, desde pantallas de 320 px |

## 13. Contexto para el generador de historias

> Párrafo listo para pegar en el campo **"Contexto del proyecto"** de la app.

```
BusetasApp es una aplicación para consultar las rutas de las busetas de Manizales, operadas por empresas como Socobuses, Sideral y Serviturismo: catálogo de rutas con recorrido en mapa y paradas, horarios y días de operación (lunes a viernes, sábados, domingos y festivos), frecuencias variables por franja horaria, ubicación de las busetas con tiempo estimado de llegada (ETA) a una parada, planificación de viaje con origen y destino, y búsqueda por número o nombre de ruta, barrio o punto de interés (los usuarios se orientan por hitos como la Catedral, El Cable, la Carrera 23 o Fundadores). Las rutas no se identifican igual en todas las empresas: pueden tener código numérico público, código interno alfanumérico, o ninguno (se identifican por número lateral de la buseta); una misma ruta puede ser operada por varias empresas y tener variantes. Hay cuatro roles. Pasajero: consulta sin cuenta; guardar favoritas y recibir notificaciones requiere usuario registrado. Jefe de operaciones: responsable operativo de una empresa; asigna a los conductores las rutas ya registradas en la plataforma, define el rodamiento del día (ruta, hora de salida, número lateral de la buseta y conductor), publica avisos generales (cambios, suspensiones, horarios de festivos) y consulta estadísticas básicas; no puede crear, editar ni eliminar rutas. Secretaría de Movilidad: alimenta la base de datos; impone las rutas a cada empresa, gestiona los paraderos de la ciudad y registra cualquier cambio de movilidad (cierres, desvíos, obras, condiciones). Administrador: dueño de la plataforma, con control total (usuarios, roles, empresas y configuración). Los conductores no son usuarios de la plataforma; solo aparecen como datos del rodamiento. Fuera de alcance: pagos, tarjetas de recarga, transporte fuera de Manizales, módulo de conductor, y procesos internos de las empresas (planillas, nómina, recaudo).
```
