# Diagramas reducidos del prototipo

> Versión pequeña para presentar. La base de datos completa del diseño tiene 28 tablas (`referencia/esquema.sql`); el prototipo usa 22 y este diagrama agrupa lo esencial en 16 entidades. Los diagramas completos están en `referencia/05-actividad-6-datos-api.md`.

## 1. Arquitectura (hexagonal)

```mermaid
flowchart TB
    subgraph ENT["Adaptadores de entrada"]
        http["Routers FastAPI + esquemas Pydantic"]
        wsin["WebSocket de posiciones"]
        bot["Bot de Telegram"]
        sim["Simulador de GPS (MODO_DEMO)"]
    end
    subgraph APP["Aplicacion: casos de uso"]
        ucc["Consulta: rutas, horarios, busquedas, avisos"]
        ucs["Seguimiento: registrar posiciones, ETA"]
        ucp["Pasajero: favoritos, alertas, planificar"]
        uco["Operacion: rodamiento"]
        ucm["Movilidad: rutas, paraderos"]
        uca["Administracion: usuarios, parametros, demo"]
    end
    subgraph DOM["Dominio"]
        ent["Entidades y reglas"]
        svc["CalculadorEta, DeductorDeRuta, EvaluadorAlertas, ValidadorRodamiento, CalculadorTipoDia"]
        pue["Puertos de salida: repositorios, autenticacion, reloj, eventos, notificador"]
    end
    subgraph SAL["Adaptadores de salida"]
        repo["Repositorios Supabase (SQL + PostGIS)"]
        aut["Supabase Auth"]
        clk["Reloj (real o simulado)"]
        evt["Emisor de eventos en memoria"]
        tgo["Notificador Telegram"]
        wso["Difusor WebSocket"]
    end
    http --> APP
    wsin --> ucs
    bot --> APP
    sim --> ucs
    APP --> DOM
    pue -.-> repo
    pue -.-> aut
    pue -.-> clk
    pue -.-> evt
    pue -.-> tgo
    pue -.-> wso
```

## 2. Modelo entidad-relación reducido (16 entidades)

```mermaid
erDiagram
    EMPRESA ||--o{ SERVICIO_RUTA : opera
    RUTA ||--o{ SERVICIO_RUTA : "es operada como"
    RUTA ||--|{ RUTA_PARADERO : recorre
    PARADERO ||--o{ RUTA_PARADERO : "aparece en"
    SERVICIO_RUTA ||--o{ HORARIO : tiene
    EMPRESA ||--o{ BUSETA : posee
    EMPRESA ||--o{ CONDUCTOR : emplea
    EMPRESA ||--o{ RODAMIENTO : planifica
    RODAMIENTO ||--|{ TURNO : contiene
    SERVICIO_RUTA ||--o{ TURNO : "se programa en"
    BUSETA ||--o{ TURNO : cumple
    CONDUCTOR ||--o{ TURNO : conduce
    BUSETA ||--o| POSICION_BUSETA : "ultima posicion"
    EMPRESA |o--o{ USUARIO : "tiene jefe"
    USUARIO ||--o{ FAVORITO : guarda
    USUARIO ||--o{ ALERTA_LLEGADA : crea
    RUTA ||--o{ ALERTA_LLEGADA : vigila
    PARADERO ||--o{ ALERTA_LLEGADA : vigila
    USUARIO ||--o{ AVISO : publica
    AVISO }o--o{ RUTA : afecta
    HITO }o--o{ RUTA : "cerca de"

    RUTA {
        uuid id PK
        text nombre
        text tipo_recorrido "circular"
        geography trazado
        int version
    }
    SERVICIO_RUTA {
        uuid id PK
        text codigo_publico "opcional"
        text estado
    }
    HORARIO {
        text tipo_dia
        time primera_salida
        time ultima_salida
        int frecuencia_min
    }
    TURNO {
        time hora_salida
        time hora_fin_estimada
    }
    POSICION_BUSETA {
        geography ubicacion
        real velocidad_kmh
        timestamptz reportada_en
    }
    USUARIO {
        uuid id PK
        text rol
    }
    AVISO {
        text origen "empresa | movilidad | aplicativo"
        text cuerpo
    }
```

Notas: `HORARIO` representa a las tablas `horario` + `frecuencia` (franjas) de la BD; `RUTA` incluye `ruta_trazado`; `AVISO` incluye `aviso_afecta`. Tablas de apoyo no dibujadas: `credencial_fuente_gps`, `parametro_global`, `evento_uso`.

## 3. Secuencia 1 — Seguimiento y ETA (pasajero, GPS simulado)

```mermaid
sequenceDiagram
    autonumber
    participant SIM as Simulador GPS
    participant SEG as Caso de uso registrar_posiciones
    participant ROD as Rodamiento (turno vigente)
    participant BD as Supabase (PostGIS)
    participant WS as WebSocket
    participant API as API REST
    actor APP as App del pasajero
    SIM->>SEG: posiciones por numero lateral
    SEG->>ROD: turno_vigente(empresa, lateral, ahora)
    ROD-->>SEG: servicio_ruta_id
    SEG->>BD: guardar_posicion (solo si es mas reciente)
    SEG->>WS: difundir a /ws/rutas/{rutaId}
    WS-->>APP: mensaje posiciones
    APP->>API: GET /paraderos/{id}/eta
    API->>BD: posiciones frescas y progreso sobre el circuito
    API-->>APP: ETA con fuente gps u horario
    Note over APP,BD: ETA = distancia restante por el circuito / velocidad. Sin posicion fresca: rango por frecuencia
```

## 4. Secuencia 2 — Jefe de operaciones arma y publica el rodamiento

```mermaid
sequenceDiagram
    autonumber
    actor J as Jefe de operaciones
    participant API as API
    participant UC as Casos de uso de rodamiento
    participant VAL as ValidadorRodamiento
    participant BD as Repositorio
    J->>API: PUT /rodamientos/{id} (turnos, version)
    API->>UC: actualizar_rodamiento(empresa del token)
    UC->>BD: verificar que servicio, buseta y conductor son de su empresa
    UC->>VAL: validar(turnos)
    VAL-->>UC: advertencias (solapamientos)
    UC->>BD: guardar borrador con control de version
    API-->>J: 200 + advertencias
    J->>API: POST /rodamientos/{id}/publicar (version)
    API->>UC: publicar_rodamiento
    UC->>VAL: validar de nuevo
    alt hay solapamientos
        API-->>J: 409 CONFLICTO_NEGOCIO + lista
    else version distinta
        API-->>J: 409 CONFLICTO_VERSION
    else correcto
        UC->>BD: estado = publicado
        API-->>J: 200
    end
```

## 5. Secuencia 3 — Alerta de llegada por Telegram

```mermaid
sequenceDiagram
    autonumber
    actor P as Pasajero (Telegram)
    participant BOT as Bot de Telegram
    participant UC as Casos de uso
    participant BD as Repositorio
    participant SEG as registrar_posiciones
    participant EVA as EvaluadorAlertas
    P->>BOT: "Avisarme cuando este cerca" (ruta, paradero)
    BOT->>UC: crear_alerta_llegada(chat_id, ruta, paradero, 300 m)
    UC->>BD: guardar alerta activa
    BOT-->>P: "Listo, te aviso a 300 m"
    SEG->>EVA: evaluar(servicio, nueva posicion)
    EVA->>BD: alertas activas de la ruta y paradero
    EVA-->>SEG: alertas disparadas (respeta enfriamiento)
    SEG->>BOT: notificar(chat_id, mensaje)
    BOT-->>P: "La Sideral esta a 300 m de tu paradero"
```

## 6. Flujo de navegación del pasajero

Ver `referencia/03-actividad-4-ux-prototipos.md` §2.1 y la diapositiva "Flujo de Navegación" de la presentación: Mapa → Buscar / Viajar / Guardados / Avisos → Ficha de ruta (Recorrido, Horarios, Frecuencia, En vivo) → ETA de la parada → (Avisarme → sesión).
