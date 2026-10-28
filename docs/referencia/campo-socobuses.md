Socobuses

1. Identificación y Planificación del Sistema de Rutas

1.1. Identificación Digital y Física de las Rutas

El sistema de transporte masivo de Socobuses fundamenta el diseño de su red en una codificación estandarizada basada en números para la totalidad de sus trayectos, garantizando que cada ruta cuente con un código único dentro del sistema general. Sin embargo, desde una perspectiva de diseño pedagógico y operacional, la empresa aplica una arquitectura de información dual para diferenciar la interfaz pública de la administración técnica:

Identificación Física (Externa): Orientada exclusivamente al usuario final en la vía pública, esta señalización utiliza solo números. Esto minimiza la carga cognitiva del pasajero y facilita la identificación rápida del vehículo en movimiento.

Identificación Interna: Destinada al control logístico y administrativo, la nomenclatura combina elementos alfanuméricos (números y letras). Esta estructura permite caracterizar variantes, ramales específicos o despachos especiales dentro del sistema central de gestión.

Propósito Operativo de la Dualidad: La diferenciación entre el código físico (solo números) y el código interno (alfanumérico) satisface dos necesidades operativas simultáneas: ofrece una interfaz de usuario limpia y accesible para la ciudadanía, al tiempo que proporciona una estructura de datos detallada y técnicamente rigurosa para la programación, el seguimiento y el control administrativo de la flota.

1.2. Asignación Tecnológica de Vehículos (Software de Rodamiento)

La programación de la flota no se realiza de forma empírica ni mediante asignaciones fijas. La compañía utiliza un software especializado de rodamiento que administra de manera automatizada la distribución operativa:

Proyección Temporal de la Programación: El sistema algorítmico programa y distribuye las rutas a los vehículos con una anticipación de 8 días (pudiendo extenderse hasta 15 días en la planificación general), optimizando la rotación del parque automotor.

Flexibilidad y Rotación Vehicular: El modelo operativo no vincula de forma rígida una buseta a un único recorrido; el software permite que una misma unidad opere múltiples rutas diferenciadas a lo largo de una sola jornada de trabajo.

La articulación entre la codificación de las rutas y la asignación algorítmica mediante el software de rodamiento constituye la fase teórica de la planificación operativa. Sin embargo, este diseño en gabinete debe trasladarse a la infraestructura vial urbana, donde se enfrenta a la demanda de los usuarios y a la variabilidad real del tráfico citadino.

2. Dinámica Operativa: Horarios, Frecuencias y Cobertura

2.1. Programación Horaria y Capacidad Operativa

La red de transporte opera bajo una ventana de servicio estandarizada para asegurar la cobertura urbana diaria:

Inicio de Despacho (Primera Salida): 5:30 AM en la totalidad de las rutas de la red.

Cierre de Despacho (Última Salida): 10:00 PM desde las terminales o puntos de origen.

Cierre Total de Recorrido: 11:00 PM, hora en que las últimas unidades completan su retorno a la base operativa.

Análisis Comparativo de Capacidad Operativa y Frecuencia: De lunes a sábado, el sistema opera a su capacidad plena programada. En contraste, los días domingos y festivos la empresa ajusta la oferta reduciendo el parque automotor en circulación y operando aproximadamente al 40% de su capacidad operativa (lo que representa la disposición de la mitad del personal habitual). Esta contracción deliberada en la oferta desplaza la curva de frecuencias, generando intervalos de paso más extendidos entre vehículos e incrementando los tiempos de espera del usuario en paradero.

2.2. Gestión de Frecuencias y Tiempos de Recorrido

Las frecuencias no son estáticas; están configuradas dentro del software de gestión y varían en función del comportamiento de la demanda y de la topología de la ruta.

Nota de integración en corredor: En el tronco común del sector de La Enea, la operación intercala la ruta directa (cada 6 minutos) con la variante Bosques de La Enea (que ingresa en el punto intermedio de los 3 minutos). Esto genera una frecuencia efectiva combinada de paso de cada 3 minutos, la cual se mantiene constante durante toda la jornada.

Tiempos de Recorrido, Congestión Urbana y Restricción de Tiempo de Ciclo Fijo: El tiempo promedio estándar estipulado para completar un recorrido en la red es de 50 minutos, existiendo trayectos más cortos proyectados entre 30 y 45 minutos. No obstante, la matriz de despacho impone un límite máximo estricto e infranqueable de 1 hora para alcanzar la meta o punto final.

Esta discrepancia entre el tiempo estándar y el techo de 1 hora configura una restricción de tiempo de ciclo fijo. La presión sobre los conductores se intensifica severamente durante las horas pico debido a cuellos de botella viales localizados en corredores críticos de la ciudad: la Avenida Centro, la Avenida Santander y, de manera muy marcada, la Avenida Paralela a la altura de la Calle 55 (donde un ciclo semafórico prolongado retarda la circulación). Al absorber estos retrasos del tráfico sin que el límite máximo de 1 hora se modifique, los conductores se ven obligados a acelerar el ritmo de marcha para evitar penalizaciones por incumplimiento en la tabla de tiempos.

Para garantizar que esta programación teórica y el cumplimiento de las frecuencias se mantengan bajo control frente a las fricciones del tráfico urbano, la empresa despliega una infraestructura mixta de supervisión tecnológica y control de campo.

3. Sistema Integrado de Monitoreo, Control y Registro

3.1. Localización Tecnológica (GPS)

La flota de busetas cuenta con dispositivos de geolocalización GPS integrados directamente en la estructura física del vehículo.

Monitoreo Centralizado: La posición espacial exacta de cada unidad es rastreada continuamente desde la oficina central de la compañía.

Validación Cruzada Espacio-Tiempo: El centro de control cruza la ubicación geográfica emitida por el GPS en tiempo real con la hora exacta de salida asignada en la tabla de rodamiento. Este cruce telemático permite determinar si la buseta mantiene el promedio de velocidad requerido para no exceder la restricción máxima de 1 hora de llegada al destino final.

3.2. Control Presencial en Campo: Controladores y Planillas

El seguimiento por telemetría se complementa con la supervisión humana en vía, la cual opera bajo una división funcional de roles:

Controladores de Punto (Inicio y Fin): Personal ubicado fijamente en las cabeceras de ruta. Tienen la función de registrar manualmente en la planilla física la hora exacta de llegada y autorizar formalmente el horario y código de la siguiente salida.

Supervisores Intermedios: Agentes desplegados en puntos estratégicos del trayecto. Realizan inspecciones visuales dinámicas ("a vista", sin detener la marcha del vehículo ni interrumpir el flujo operativo) para verificar dos condiciones críticas de seguridad: el uso obligatorio del cinturón de seguridad por parte del conductor y la ausencia de sobrecupo de pasajeros.

Al iniciar la jornada de trabajo durante la mañana, el controlador de cabecera abre el registro operativo capturando obligatoriamente cuatro (4) datos críticos en la planilla física de control:

Placa del vehículo.

Número lateral del vehículo.

Nombre completo del conductor.

Documento de identidad del conductor.

(Nota de asignación de flota: Aproximadamente el 10% del parque automotor cuenta con una estructura operativa de dos conductores asignados por vehículo para cubrir los turnos).

La secuencia del dato fluye progresivamente: el software proyecta la salida, el controlador de cabecera valida la planilla al inicio y al final, los supervisores intermedios inspeccionan la marcha y la central de GPS audita la posición en tiempo real.

3.3. Propósito Integrado de los Datos

La información recolectada de forma manual en las planillas físicas de vía, al ser consolidada con los reportes digitales del software de rodamiento y los datos del GPS, satisface dos propósitos administrativos y logísticos fundamentales:

Indicadores de Gestión y Cumplimiento: Permite auditar la disciplina operativa verificando el cumplimiento estricto de las frecuencias, las horas de paso y el trazado autorizado de las rutas.

Procesamiento y Liquidación de Nómina: Constituye el insumo primario y verificado para certificar las horas trabajadas y calcular el pago correspondiente a los conductores.

A pesar de la rigurosidad de esta arquitectura de monitoreo y control, la operación en calle está expuesta a imprevistos viales, interacciones dinámicas con los pasajeros y regulaciones estatales, lo que exige capacidad de adaptación y protocolos claros de respuesta.

4. Gestión de Contingencias, Criterio Humano y Marco Regulatorio

4.1. Protocolo de Desvíos e Incidencias

Frente a bloqueos de vía, obras públicas o fallas mecánicas ("varazones"), la organización aplica una estructura jerárquica de toma de decisiones:

Autonomía Operativa Inmediata: Si la obstrucción es repentina e imprevista, el conductor cuenta con la facultad de tomar una decisión autónoma de desvío en el sitio para mantener la circulación, con la obligación estricta de notificar la novedad a la central inmediatamente.

Decisión Centralizada en Novedades Complejas: Ante cierres prolongados de barrios o imprevistos de gran escala que impidan cumplir el trazado original, la toma de decisiones se centraliza en el Jefe de Personal ("Don Jorge"), quien define e instruye la ruta alternativa que deben seguir las unidades.

Canal Oficial de Comunicación y Cobertura de Varazones: La coordinación operativa en tiempo real y el reporte de varazones mecánicas se efectúan mediante grupos oficiales de WhatsApp. Cuando una buseta queda fuera de servicio por falla técnica, el controlador o despachador redistribuye la cobertura en vía asignando otro vehículo de refresco para suplir de inmediato el servicio desatendido.

4.2. Interacción con el Usuario y Flexibilidad del Servicio

En el plano normativo, el marco legal exige la parada exclusiva en los paraderos oficialmente demarcados. Sin embargo, el sistema contempla el uso del criterio discrecional del conductor por razones de accesibilidad e inclusión:

Criterio Discrecional y Auxilio de Movilidad: El conductor está autorizado para detener la unidad y permitir el ascenso o descenso fuera de las paradas reglamentarias cuando atiende a adultos mayores o personas con discapacidad.

Perfil del Usuario y Referenciación Urbana: El usuario local en Manizales posee un alto conocimiento de la red de transporte y se orienta mediante hitos geográficos de la ciudad (como la Catedral, El Cable, la Carrera 23 o el sector de Fundadores).

Patrón de Consultas: Las dudas informativas de los pasajeros hacia el conductor se concentran casi exclusivamente en la cobertura de la ruta y los horarios, mostrando un desinterés generalizado por la ubicación técnica de los paraderos formales.

4.3. Supervisión Estatal y Mantenimiento de Flota

La operación de Socobuses está fiscalizada de forma permanente por la Secretaría de Movilidad, autoridad gubernamental encargada de auditar tres ejes operativos:

El cumplimiento riguroso de las rutas autorizadas en la concesión.

El estado mecánico e higiénico de los vehículos.

La validez y vigencia de la documentación legal y técnica de la flota.

Para dar cumplimiento continuo a estas exigencias regulatorias y prevenir contingencias en vía, la empresa cuenta con una infraestructura interna constituida por talleres propios, programas de mantenimiento preventivo y personal dedicado exclusivamente a ejecutar una revisión mecánica diaria a cada vehículo antes de autorizar su salida a prestar servicio a la ciudad.



| Nombre / Tipo de Ruta | Frecuencia (Minutos) | Patrón Operativo / Variante |

| --- | --- | --- |

| Ruta Villamaría | 10 a 15 min | Dinámica y ajustable según la franja horaria (10 minutos en horas de alta demanda, elevándose a 15 minutos en horas valle). |

| Ruta La Enea (Directa) | Cada 6 min | Recorrido directo a través del corredor o avenida principal. |

| Ruta Bosques de La Enea | Cada 6 min | Variante espacial que se desvía e ingresa a la urbanización Bosques de La Enea. |
