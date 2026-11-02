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

Resumen de `docs/04-guia-ejecucion-y-apk.md` §3–§5 (ahí está el detalle de variables y de Supabase):

```bash
cd backend
python -m venv .venv
.venv\Scripts\activate            # Linux/macOS: source .venv/bin/activate
pip install -e ".[dev]"
copy .env.example .env            # Linux/macOS: cp .env.example .env  → rellena las claves de Supabase
python scripts/cargar_semillas.py       # solo la primera vez en una base nueva
python scripts/crear_usuarios_demo.py   # solo la primera vez
uvicorn servidor:app --app-dir src --host 0.0.0.0 --port 8000 --loop servidor:fabrica_bucle --reload
```

- **`--host 0.0.0.0` es obligatorio**: con el valor por defecto (`127.0.0.1`) el celular no puede llegar al backend.
- Con `MODO_DEMO=true` el simulador mueve las busetas. Si el proyecto de Supabase ya tiene los datos cargados, no repitas los dos scripts.
- Comprueba en el computador: <http://localhost:8000/docs>.

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
4. **Prueba antes de abrir la app:** en el navegador **del celular** abre `http://<IP>:8000/api/v1/salud`. Si responde, la red está bien. Si no, es red, firewall o `--host`.
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
| Banner de error de conexión en todas las pantallas | IP equivocada o cambió, backend sin `--host 0.0.0.0`, firewall o redes distintas. Repite la prueba `http://<IP>:8000/api/v1/salud` desde el navegador del celular. |
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
