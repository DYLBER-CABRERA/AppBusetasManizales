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

## Ejecutar los paneles web (`web-admin/`) en tu PC

Los paneles (Jefe de operaciones, Secretaría de Movilidad, Administrador y Panel de demo) son una app Next.js que **necesita el backend corriendo** y un proyecto de Supabase para iniciar sesión.

### 1. Requisitos

- **Git** y **Node.js 20 o superior** (recomendado 22 LTS) con `npm`. Comprueba con `node -v`.
- **Python 3.12 o superior**, para el backend.
- Un proyecto gratuito de **Supabase** con las migraciones aplicadas (guía en `docs/04-guia-ejecucion-y-apk.md`, sección 3).

### 2. Descargar el proyecto

```bash
git clone https://github.com/DYLBER-CABRERA/AppBusetasManizales.git
cd AppBusetasManizales
git checkout feat/web-base      # hasta que la rama se fusione en main
```

### 3. Levantar el backend (terminal 1)

Los paneles consumen su API. Todo el detalle está en `docs/04-guia-ejecucion-y-apk.md`; en resumen, desde `backend/`:

```bash
cp .env.example .env            # Windows (PowerShell): Copy-Item .env.example .env
# Edita .env: DATABASE_URL, SUPABASE_URL, SUPABASE_ANON_KEY, SUPABASE_SERVICE_ROLE_KEY,
# las contraseñas DEMO_PASSWORD_* y MODO_DEMO=true (para el Panel de demo).
# CORS_ORIGENES debe incluir http://localhost:3000 (ya viene así).

python -m venv .venv
source .venv/bin/activate       # Windows: .venv\Scripts\activate
pip install -e ".[dev]"
python scripts/cargar_semillas.py
python scripts/crear_usuarios_demo.py
uvicorn servidor:app --app-dir src --host 0.0.0.0 --port 8000 --loop servidor:fabrica_bucle
```

Comprueba que `http://localhost:8000/docs` abre. `SUPABASE_SERVICE_ROLE_KEY` es **solo del backend**: nunca va en `web-admin/`.

### 4. Configurar y arrancar los paneles (terminal 2)

```bash
cd web-admin
cp .env.example .env.local      # Windows (PowerShell): Copy-Item .env.example .env.local
```

Edita `web-admin/.env.local`:

| Variable | Valor |
|---|---|
| `NEXT_PUBLIC_SUPABASE_URL` | URL de tu proyecto Supabase |
| `NEXT_PUBLIC_SUPABASE_ANON_KEY` | clave **anon** (pública) del mismo proyecto |
| `NEXT_PUBLIC_API_URL` | `http://localhost:8000/api/v1` |
| `NEXT_PUBLIC_WS_URL` | `ws://localhost:8000` |
| `NEXT_PUBLIC_MAP_TILE_URL` | `https://tile.openstreetmap.org/{z}/{x}/{y}.png` (ya viene así) |

Luego:

```bash
npm install
npm run dev
```

Abre **http://localhost:3000**. Si cambias `.env.local`, detén `npm run dev` (Ctrl+C) y arráncalo de nuevo.

### 5. Iniciar sesión

Usa las cuentas de demostración (las crea `crear_usuarios_demo.py`; las contraseñas son las `DEMO_PASSWORD_*` de `backend/.env`):

| Correo | Rol | Entra a |
|---|---|---|
| `jefe@sideral.example` | Jefe de operaciones | `/jefe/rodamiento` |
| `movilidad@alcaldia.example` | Secretaría de Movilidad | `/secretaria/rutas` |
| `admin@busetasapp.example` | Administrador | `/admin/*` y, con selector de empresa, `/jefe/*` |

El menú lateral cambia según el rol. El Panel de demo solo aparece si el backend corre con `MODO_DEMO=true`.

### 6. Comandos útiles (desde `web-admin/`)

| Comando | Para qué |
|---|---|
| `npm run dev` | Servidor de desarrollo en el puerto 3000 |
| `npm run build` y `npm start` | Versión de producción local |
| `npm run lint` | Revisión de estilo y errores |
| `npm test` | Pruebas (vitest) |
| `npm run tipos` | Regenera los tipos desde `contrato/openapi.json` (solo si el backend cambia el contrato) |

### 7. Problemas frecuentes

- **Pantalla de error o «No se pudo conectar con el servidor»:** el backend no está corriendo o `NEXT_PUBLIC_API_URL` está mal. Abre `http://localhost:8000/docs`.
- **Error de CORS en la consola del navegador:** agrega `http://localhost:3000` a `CORS_ORIGENES` en `backend/.env` y reinicia el backend.
- **El login falla:** revisa que la URL y la clave `anon` de `.env.local` sean del mismo proyecto Supabase del backend y que ejecutaste `crear_usuarios_demo.py`.
- **En Windows el backend falla con un error del bucle de eventos:** arráncalo con `--loop servidor:fabrica_bucle`, como arriba.
- **No aparece «Panel de demo»:** pon `MODO_DEMO=true` en `backend/.env` y reinicia el backend.
- **Aviso de Node.js 20 deprecado:** es de Supabase y no impide ejecutar; con Node 22 desaparece.

## Coordinación entre agentes

- Cambios al contrato: solo `backend-dev`, y avisa en `docs/decisiones-agentes.md`.
- Un frontend que necesite algo nuevo lo escribe en `docs/solicitudes-entre-agentes.md`.
- Nadie edita la carpeta de otro agente.

## Para la clase

Guion de demo, qué es real y qué es simulado, y plan B: `docs/00-plan-prototipo-demo.md`.
