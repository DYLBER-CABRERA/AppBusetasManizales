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

## Ejecutar la app móvil desde cero (Flutter · Android)

La app del pasajero necesita el **backend corriendo** (la app no tiene datos propios) y un celular Android en la **misma red** que el computador. Sirve en Windows, macOS o Linux; los comandos muestran Windows (PowerShell) y, donde cambia, Linux/macOS.

### 1. Qué debe estar instalado

| Herramienta | Versión probada | Para qué | Cómo verificar |
|---|---|---|---|
| **Git** | cualquiera reciente | clonar el repositorio | `git --version` |
| **Flutter SDK** (incluye Dart) | Flutter 3.47.9 · Dart 3.13.7 (el `pubspec.yaml` fija `sdk: 3.13.7`) | compilar la app | `flutter --version` |
| **Android SDK** (Android Studio o *command-line tools*): plataforma Android, *build-tools*, *platform-tools* (`adb`) y *cmdline-tools* | el que pida Flutter | compilar y copiar el APK | `flutter doctor` |
| **JDK 17** (el que trae Android Studio sirve) | 17 | Gradle y Kotlin | `java -version` |
| **Python 3.12+** y `pip` | 3.12 | backend | `python --version` |
| **Cuenta gratuita de Supabase** con el proyecto del equipo | — | base de datos y autenticación | pedir las claves a quien administra el proyecto |
| **Celular Android** con «Opciones de desarrollador → Depuración USB» (o permiso para instalar apps desconocidas si se copia el APK) | Android 8+ | probar la app | — |

Notas de instalación:

- Agrega `flutter\bin` al `PATH`. En Windows, si `flutter` no se reconoce en la sesión actual: `$env:Path += ";C:\src\flutter\bin"` (ajusta la ruta donde lo descomprimiste).
- Acepta las licencias de Android una sola vez: `flutter doctor --android-licenses`. `flutter doctor` debe salir **sin errores en «Android toolchain»**.
- El proyecto pide un **NDK** concreto (`30.0.16248370`): Gradle lo descarga solo la primera vez (necesita internet y las licencias aceptadas).
- La primera compilación tarda varios minutos (descarga Gradle, dependencias y NDK). Las siguientes son rápidas.
- La app **no usa** `SUPABASE_SERVICE_ROLE_KEY`: nunca la pongas en `mobile/`. Solo la clave pública `anon`.

### 2. Descargar el proyecto

```bash
git clone https://github.com/DYLBER-CABRERA/AppBusetasManizales.git
cd AppBusetasManizales
```

### 3. Levantar el backend (en el computador)

Sigue **«Ejecutar el backend (paso a paso)»**, más arriba en este README (entorno, `backend/.env`, base de datos). Lo único que cambia para el celular es el arranque:

```bash
cd backend
uvicorn servidor:app --app-dir src --host 0.0.0.0 --port 8000 --loop servidor:fabrica_bucle --reload
```

- **`--host 0.0.0.0` es obligatorio**: con el valor por defecto (`127.0.0.1`) el celular no puede llegar al backend.
- Con `MODO_DEMO=true` el simulador mueve las busetas.
- Comprueba en el computador: <http://localhost:8000/api/v1/salud>.

### 4. Averiguar la IP del computador (lo que más falla)

El celular **no puede usar `localhost`**: necesita la IP del computador en la red local.

- Windows: `ipconfig` → «Dirección IPv4» del adaptador Wi-Fi (por ejemplo `192.168.0.10`).
- Linux: `ip addr` · macOS: `ipconfig getifaddr en0`.

Ten en cuenta:

1. **La IP cambia** si cambias de red o el router te asigna otra. Si la app deja de conectar, vuelve a mirarla.
2. **Computador y celular en la misma red.** Algunas redes (universidad, cafés) aíslan a los dispositivos entre sí y no funcionan: usa el **hotspot del celular** y conecta el computador a él.
3. **Firewall de Windows:** permite el puerto 8000 en red privada. En PowerShell **como administrador**:
   ```powershell
   New-NetFirewallRule -DisplayName "BusetasApp backend 8000" -Direction Inbound -Protocol TCP -LocalPort 8000 -Action Allow -Profile Private
   ```
   Si Windows clasificó la red como «Pública», cámbiala a «Privada».
4. **Prueba antes de abrir la app:** en el navegador **del celular** abre `http://<IP>:8000/salud`. Si responde, la red está bien. Si no, es red, firewall o `--host`.
5. **Emulador de Android** (en vez de un celular): el computador se ve como `http://10.0.2.2:8000` (es el valor por defecto de la app, no hace falta IP).

### 5. Configurar la app

```bash
cd mobile
copy .env.example .env      # Linux/macOS: cp .env.example .env
```

Edita `mobile/.env` (Flutter **no** lee este archivo solo; se pasa con `--dart-define-from-file`). El archivo está en `.gitignore`, no se sube:

| Variable | Valor |
|---|---|
| `API_BASE_URL` | `http://<IP-del-computador>:8000` (la del paso 4) |
| `SUPABASE_URL` | URL del proyecto de Supabase |
| `SUPABASE_ANON_KEY` | clave `anon` (pública) del proyecto |
| `MAP_TILE_URL` | `https://tile.openstreetmap.org/{z}/{x}/{y}.png` (sin cuenta ni token) |

Sin `SUPABASE_URL` y `SUPABASE_ANON_KEY` la app funciona pero **sin cuenta** (no hay Guardados, «Avisarme» ni crear cuenta).

### 6. Ejecutarla en el celular

**Opción A: con cable (depuración)**

```bash
cd mobile
flutter pub get
flutter devices                              # el celular debe aparecer en la lista
flutter run --dart-define-from-file=.env
```

Si el celular no aparece: usa un cable de datos (no solo de carga), activa «Depuración USB» y acepta el aviso de confianza en el celular.

**Opción B: instalar un APK**

```bash
cd mobile
flutter pub get
flutter build apk --release --dart-define-from-file=.env
# Resultado: mobile/build/app/outputs/flutter-apk/app-release.apk
adb install -r build/app/outputs/flutter-apk/app-release.apk
```

Sin `adb`, copia el `.apk` al celular (Drive, Telegram, cable), ábrelo y permite «instalar apps desconocidas». El APK de release usa la firma de depuración: sirve para la demo, no para Google Play. **La IP queda grabada en el APK**, pero se puede cambiar en la app sin recompilar (paso 7).

### 7. Primera vez en la app

1. Concede el permiso de **ubicación** (solo para «rutas cerca de ti»; no se guarda) y el de **notificaciones**.
2. Si la app no carga datos: **Ajustes** (icono de engranaje en el Mapa) → **Servidor** → escribe `http://<IP>:8000` → **Probar conexión** (llama a `/salud`). Esto sobrescribe `API_BASE_URL` sin recompilar.
3. Recorrido de comprobación: Mapa (la buseta amarilla se mueve) → una ruta → un paradero (ETA) → Viajar (origen y destino) → Guardados (pide iniciar sesión o crear cuenta).
4. Cuenta de prueba: las cuentas de demostración las crea `crear_usuarios_demo.py` con las contraseñas de `backend/.env`. También puedes usar **Crear cuenta** (nombre, apellido, celular, correo y contraseña). Si el proyecto de Supabase exige confirmar el correo, confírmalo y luego inicia sesión.

### 8. Problemas frecuentes

| Síntoma | Causa y solución |
|---|---|
| Banner de error de conexión en todas las pantallas | IP equivocada o cambió, backend sin `--host 0.0.0.0`, firewall o redes distintas. Repite la prueba `http://<IP>:8000/salud` desde el navegador del celular. |
| Funciona en el computador pero no en el celular | Casi siempre el firewall o una red que aísla dispositivos. Prueba con el hotspot del celular. |
| El mapa se ve gris sin teselas | El celular no tiene internet (las teselas vienen de OpenStreetMap) o `MAP_TILE_URL` está mal. |
| `flutter` no se reconoce | Falta agregar `flutter\bin` al `PATH` (ver paso 1). |
| `flutter doctor` marca licencias de Android | `flutter doctor --android-licenses` y aceptar todas. |
| Falla la compilación por el NDK o Gradle | Primera compilación sin internet o licencias sin aceptar. Con internet, vuelve a ejecutar el comando. |
| Las busetas no se mueven | El backend no está con `MODO_DEMO=true`, o el simulador se detuvo (reinícialo desde el Panel de demo de la web). |
| Crear cuenta o iniciar sesión falla | Faltan `SUPABASE_URL` / `SUPABASE_ANON_KEY` en `mobile/.env` (hay que recompilar tras cambiarlos), o el backend aún no tiene el endpoint `POST /yo`. |

> Después de cambiar `mobile/.env` hay que volver a ejecutar `flutter run` o `flutter build apk`: los valores se graban al compilar. Solo la dirección del servidor se puede cambiar en Ajustes sin recompilar.

Verificación del código antes de entregar: `cd mobile && flutter analyze && flutter test`.

## Coordinación entre agentes

- Cambios al contrato: solo `backend-dev`, y avisa en `docs/decisiones-agentes.md`.
- Un frontend que necesite algo nuevo lo escribe en `docs/solicitudes-entre-agentes.md`.
- Nadie edita la carpeta de otro agente.

## Para la clase

Guion de demo, qué es real y qué es simulado, y plan B: `docs/00-plan-prototipo-demo.md`.
