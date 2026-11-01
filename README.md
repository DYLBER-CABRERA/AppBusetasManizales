# BusetasApp Manizales · Prototipo de clase

Prototipo con **datos simulados** (sin convenio con empresas): backend FastAPI, app móvil Flutter (APK), paneles web Next.js y chatbot de Telegram.

## Estructura

```
busetasapp/
├── CLAUDE.md                 # reglas globales para todos los agentes
├── .claude/agents/           # backend-dev, web-admin-dev, mobile-dev
├── .claude/skills/           # 4 skills (backend, telegram-bot, web-admin, mobile)
├── docs/                     # plan, alcance, diagramas, contrato, guía de ejecución y APK
│   └── referencia/           # material original (ver LEEME.md: qué sigue vigente)
├── contrato/                 # openapi.json exportado por el backend
├── backend/                  # FastAPI + simulador + bot de Telegram
├── web-admin/                # Next.js: Jefe, Secretaría, Administrador, Panel de demo
└── mobile/                   # Flutter (Android): pasajero
```

Un solo repositorio (monorepo) con tres proyectos. El bot de Telegram vive dentro de `backend/`.

## Ejecutar el backend (paso a paso)

Todo es gratuito. Los datos son simulados ("Datos de ejemplo · no son rutas oficiales").

### Requisitos

- Git y **Python 3.12 o superior**.
- Una cuenta gratuita de [Supabase](https://supabase.com) con un proyecto **nuevo y vacío**.
- Opcional: un bot de Telegram (BotFather, `/newbot`). Sin token, el bot queda desactivado y el resto funciona.

### 1. Descargar el proyecto

```bash
git clone https://github.com/DYLBER-CABRERA/AppBusetasManizales.git
cd AppBusetasManizales/backend
```

### 2. Crear el entorno e instalar dependencias

Windows (PowerShell):

```powershell
python -m venv .venv
.venv\Scripts\Activate.ps1
pip install -e ".[dev]"
```

Linux / macOS:

```bash
python -m venv .venv && source .venv/bin/activate
pip install -e ".[dev]"
```

### 3. Configurar `backend/.env`

Copia la plantilla y complétala (el `.env` real **nunca** se sube al repositorio):

```bash
cp .env.example .env        # Windows: copy .env.example .env
```

Del panel de Supabase (Project Settings):

| Variable | De dónde sale |
|---|---|
| `DATABASE_URL` | Database > Connection string (URI). Prueba la conexión directa o el *session pooler* |
| `SUPABASE_URL` | API > Project URL |
| `SUPABASE_ANON_KEY` | API > clave `anon` / publishable |
| `SUPABASE_SERVICE_ROLE_KEY` | API > clave `service_role`. **Solo backend**, nunca en web ni móvil |
| `DEMO_PASSWORD_ADMIN`, `_MOVILIDAD`, `_JEFE`, `_PASAJERO` | Las eliges tú: son las contraseñas de las 4 cuentas demo |
| `TELEGRAM_BOT_TOKEN` | Opcional (vacío = bot desactivado) |
| `MODO_DEMO` | `true` activa el simulador de GPS y el panel de demo (¡escribe en la BD al arrancar!) |

### 4. Preparar la base de datos (una sola vez)

Los scripts de `backend/scripts/` **simulan** y no tocan nada hasta que les pases `--aplicar` (cada uno imprime el host destino antes de actuar). Con el entorno activado, desde `backend/`:

```bash
# 4.1 Crea el esquema (migraciones 0001 a 0007). Solo en una base VACÍA: aborta si ya existe la tabla `empresa`.
python scripts/verificar_bd.py --aplicar-migraciones

# 4.2 Carga empresas, rutas, trazados, paraderos, horarios, busetas y rodamientos de ejemplo
python scripts/cargar_semillas.py --aplicar

# 4.3 Crea las 5 cuentas demo en Supabase Auth (necesita 4.2 hecho)
python scripts/crear_usuarios_demo.py --aplicar

# 4.4 Repite 4.2: los avisos necesitan los perfiles creados en 4.3 como autores
python scripts/cargar_semillas.py --aplicar

# 4.5 Verificación final (solo lee y revierte)
python scripts/verificar_bd.py
```

Si tu base ya tenía una versión anterior del esquema, no vuelvas a correr 4.1: usa `python scripts/actualizar_bd.py --comparar` y luego `--aplicar`, o una migración suelta con `python scripts/aplicar_migracion.py <archivo.sql> --aplicar`.

### 5. Arrancar el servidor

```bash
python -m uvicorn servidor:app --app-dir src --loop servidor:fabrica_bucle --port 8000
```

- **`--loop servidor:fabrica_bucle` es obligatorio en Windows** (sin él, psycopg asíncrono falla).
- Para que un celular de la misma red lo alcance, agrega `--host 0.0.0.0` y permite el puerto 8000 en el firewall.
- Con `MODO_DEMO=true` el arranque crea el rodamiento de hoy y el borrador de mañana si faltan, y guarda posiciones simuladas cada 3 s. Para probar solo lectura, pon `MODO_DEMO=false`.

### 6. Comprobar que funciona

- Salud: <http://localhost:8000/api/v1/salud> debe responder `{"estado":"ok"}`.
- Documentación interactiva: <http://localhost:8000/docs>.
- Rutas: <http://localhost:8000/api/v1/rutas>.
- Contrato completo: `contrato/openapi.json` y `docs/03-contrato-api.md`.
- Para endpoints con sesión, pide un token a Supabase Auth: `POST {SUPABASE_URL}/auth/v1/token?grant_type=password`, cabecera `apikey: <SUPABASE_ANON_KEY>`, cuerpo `{"email":"admin@busetasapp.example","password":"<DEMO_PASSWORD_ADMIN>"}`, y envía `Authorization: Bearer <access_token>`. Cuentas demo: `admin@busetasapp.example`, `movilidad@alcaldia.example`, `jefe@sideral.example`, `jefe@socobuses.example`, `pasajera@correo.example`.

### 7. Pruebas

```bash
python -m pytest -q          # unitarias, no tocan la base de datos
python -m ruff check .
```

Las de integración (`$env:PRUEBAS_INTEGRACION="1"; python -m pytest -m integracion -q`) sí usan la base y escriben filas.

### Problemas frecuentes

- **`PoolTimeout` / 503 en Windows:** falta `--loop servidor:fabrica_bucle`.
- **No conecta a la base:** revisa `DATABASE_URL` (conexión directa vs. *session pooler*) y que el proyecto Supabase no esté pausado (los gratuitos se pausan por inactividad).
- **`POST /yo` responde 500:** falta la migración `0006_perfil_pasajero.sql`.
- **El administrador no puede crear usuarios:** falta `SUPABASE_SERVICE_ROLE_KEY` en `.env`.

Guía completa (web, móvil y APK): `docs/04-guia-ejecucion-y-apk.md`.

## Cómo arrancar con Claude Code

1. `git init` en esta carpeta y primer commit.
2. Crea el proyecto en Supabase y el bot en BotFather (ver `docs/04-guia-ejecucion-y-apk.md`).
3. Abre **tres sesiones de Claude Code** (idealmente un *worktree* por agente) y pega el prompt correspondiente.

### Prompt: backend

> Eres el agente `backend-dev`. Lee `CLAUDE.md`, `backend/CLAUDE.md`, `docs/01-alcance-y-datos-simulados.md` y `docs/03-contrato-api.md`. Construye el backend siguiendo el orden B0…B8. Empieza por B0 y B1 (esqueleto, contrato con 501 y `contrato/openapi.json`) y avísame cuando esté listo para que los otros agentes arranquen. Reporta al final de cada bloque.

### Prompt: web-admin

> Eres el agente `web-admin-dev`. Lee `CLAUDE.md`, `web-admin/CLAUDE.md`, `docs/03-contrato-api.md` y los mockups de `docs/referencia/`. Construye los paneles siguiendo W0…W5. Mientras el backend no esté listo usa datos de ejemplo detrás de la misma interfaz del cliente tipado. Reporta al final de cada bloque.

### Prompt: mobile

> Eres el agente `mobile-dev`. Lee `CLAUDE.md`, `mobile/CLAUDE.md`, `docs/03-contrato-api.md`, `docs/04-guia-ejecucion-y-apk.md` y abre `docs/referencia/prototipo-movil.html`. Construye la app siguiendo M0…M5 y genera el APK al final. Reporta al final de cada bloque.

## Coordinación entre agentes

- Cambios al contrato: solo `backend-dev`, y avisa en `docs/decisiones-agentes.md`.
- Un frontend que necesite algo nuevo lo escribe en `docs/solicitudes-entre-agentes.md`.
- Nadie edita la carpeta de otro agente.

## Para la clase

Guion de demo, qué es real y qué es simulado, y plan B: `docs/00-plan-prototipo-demo.md`.
