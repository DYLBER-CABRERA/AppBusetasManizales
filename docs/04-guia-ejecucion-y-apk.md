# Guía de ejecución local y APK gratuito

> Los comandos son la ruta esperada; el agente que implemente cada proyecto debe verificarlos al crear el proyecto y **corregir esta guía** si algo difiere. Marcado **(verificar)** donde depende de versiones.

## 1. ¿Se puede instalar la app en el celular gratis sin servidor ni tienda?

**Sí.** Flutter genera un archivo **APK** que se instala directamente en un celular Android, sin Google Play y sin pagar nada. Para la demo basta con que el celular y el portátil estén en la misma red.

| Opción | Costo | Cuándo usarla |
|---|---|---|
| **APK de release** (`flutter build apk --release`) | Gratis | Principal. Se instala copiando el archivo al celular (cable USB, Drive, WhatsApp, Telegram) |
| `flutter run` con el celular por cable (depuración USB) | Gratis | Durante el desarrollo |
| Flutter Web en el navegador | Gratis | Plan B, o si el celular es iPhone |
| Publicar en Google Play | Pago único de cuenta de desarrollador | **No necesario** |
| App de iPhone | Requiere Mac y cuenta de Apple de pago | **Fuera del alcance** |

La app **no necesita que el backend esté desplegado**: el APK se apunta al portátil. Por eso la app tiene una pantalla de **Ajustes de servidor** donde se escribe la dirección del backend (`http://192.168.x.x:8000`) sin recompilar.

## 2. Requisitos en el portátil de desarrollo

- Python 3.12 o superior y `pip` (o `uv`).
- Node.js LTS y `npm`.
- Flutter SDK estable y Android SDK (Android Studio o *command-line tools*); `flutter doctor` debe salir sin errores para Android.
- Git.
- Cuenta gratuita de **Supabase** (un proyecto).
- Un bot de Telegram (gratis): hablar con **@BotFather**, comando `/newbot`, copiar el token.
- Un celular Android con "Instalar apps desconocidas" permitido para el origen del archivo.

## 3. Supabase

1. Crear el proyecto y copiar: URL del proyecto, clave `anon`, clave `service_role` y la cadena de conexión de Postgres (**verificar** en el panel cuál usar: conexión directa o *session pooler*; si se usa el *transaction pooler*, desactivar las sentencias preparadas en el driver).
2. Aplicar las migraciones de `backend/supabase/migraciones/` en orden (SQL Editor o `psql`). Verificar: `select postgis_version();` y que `select * from rutas_cercanas(5.07, -75.51, 800);` no falle.
3. Los proyectos gratuitos se pausan tras un período sin actividad: **abrirlo y comprobar que está activo el día antes de la demo**.
4. `service_role` solo va en el backend.

## 4. Variables de entorno

`backend/.env` (plantilla `.env.example`; nunca se sube):

| Variable | Ejemplo / nota |
|---|---|
| `DATABASE_URL` | Cadena de conexión de Supabase |
| `SUPABASE_URL`, `SUPABASE_ANON_KEY`, `SUPABASE_SERVICE_ROLE_KEY` | Del panel |
| `MODO_DEMO` | `true` activa simulador y `/demo/*` |
| `SIM_VELOCIDAD_KMH`, `SIM_INTERVALO_S` | `35`, `3` |
| `TELEGRAM_BOT_TOKEN` | Si falta, el bot queda desactivado (el resto funciona) |
| `CORS_ORIGENES` | `http://localhost:3000` |
| `PUERTO` | `8000` |
| `FESTIVOS` | Lista corta de fechas `AAAA-MM-DD` |
| `DEMO_PASSWORD_ADMIN`, `DEMO_PASSWORD_MOVILIDAD`, `DEMO_PASSWORD_JEFE`, `DEMO_PASSWORD_PASAJERO` | Para `crear_usuarios_demo.py` |

`web-admin/.env.local`: `NEXT_PUBLIC_API_URL=http://localhost:8000/api/v1`, `NEXT_PUBLIC_WS_URL=ws://localhost:8000`, `NEXT_PUBLIC_SUPABASE_URL`, `NEXT_PUBLIC_SUPABASE_ANON_KEY`, `NEXT_PUBLIC_MAP_TILE_URL`.

`mobile`: valores por `--dart-define` (`API_BASE_URL`, `SUPABASE_URL`, `SUPABASE_ANON_KEY`, `MAP_TILE_URL`) y la dirección del servidor editable en Ajustes.

URL de teselas por defecto: `https://tile.openstreetmap.org/{z}/{x}/{y}.png` con la atribución "© OpenStreetMap contributors" visible. Es para uso ligero (una demo); si hace falta más, cambiar el proveedor con la variable.

## 5. Arranque (orden)

```bash
# 1) Backend  (desde backend/)
python -m venv .venv && source .venv/bin/activate      # Windows: .venv\Scripts\activate
pip install -e ".[dev]"
python scripts/generar_trazados.py        # solo la primera vez; revisar los GeoJSON
python scripts/cargar_semillas.py         # carga empresas, rutas, paraderos, horarios, busetas, rodamientos
python scripts/crear_usuarios_demo.py
uvicorn servidor:app --app-dir src --host 0.0.0.0 --port 8000 --loop servidor:fabrica_bucle --reload
# Documentación interactiva: http://localhost:8000/docs

# 2) Paneles web  (desde web-admin/)
npm install
npm run dev                                # http://localhost:3000

# 3) App móvil  (desde mobile/)
flutter pub get
flutter run --dart-define=API_BASE_URL=http://<IP-del-portatil>:8000
```

`--host 0.0.0.0` es necesario para que el celular alcance al backend. El bot de Telegram arranca con el backend (modo *polling*, no requiere URL pública).

## 6. Conectar el celular al portátil

1. Misma red WiFi (o hotspot del celular al que se conecta el portátil).
2. IP del portátil (`ipconfig` en Windows, `ip addr`/`ifconfig` en Linux/Mac).
3. Permitir el puerto 8000 en el firewall del portátil (red privada).
4. En la app: Ajustes → Servidor → `http://<IP>:8000`. Probar con el botón "Probar conexión" (llama a `/salud`).
5. **Android bloquea `http://` por defecto en release.** El agente móvil debe habilitar tráfico en claro hacia la red local (`android:usesCleartextTraffic="true"` o una *network security config* limitada a IPs privadas) y declarar el permiso `INTERNET` en el manifiesto principal (los *builds* de release no lo heredan del de depuración).
6. **Plan B sin red local:** un túnel gratuito, por ejemplo `cloudflared tunnel --url http://localhost:8000` **(verificar)**, que entrega una URL `https://…` para escribir en Ajustes.

## 7. Generar el APK

```bash
cd mobile
flutter build apk --release --dart-define=API_BASE_URL=http://192.168.0.10:8000 \
  --dart-define=SUPABASE_URL=… --dart-define=SUPABASE_ANON_KEY=… --dart-define=MAP_TILE_URL=…
# Resultado: build/app/outputs/flutter-apk/app-release.apk
```

- Para un archivo más liviano: `--split-per-abi` (genera uno por arquitectura; el celular moderno usa `arm64-v8a`).
- Sin configuración de firma propia, Flutter firma el release con la clave de depuración. **Sirve para la demo**; no sirve para Google Play.
- Instalar: copiar `app-release.apk` al celular (cable, Drive, Telegram), abrirlo y aceptar "instalar apps desconocidas". Con cable y depuración USB: `adb install -r app-release.apk`.
- Permisos que debe pedir la app: ubicación aproximada/precisa (solo para "cerca de mí", nunca se guarda) e internet.
- Opcional: compilar en la nube con GitHub Actions (gratis en repos públicos) para no depender del portátil. No es necesario.

## 8. Telegram

1. Crear el bot con @BotFather y poner el token en `TELEGRAM_BOT_TOKEN`.
2. Opcional en BotFather: `/setcommands` con `start`, `ayuda`, `cercanas`, `llegada`, `horarios`, `avisos`.
3. Al iniciar el backend, escribir `/start` al bot desde Telegram.

## 9. Lista de verificación del día antes

- [ ] Supabase activo y datos presentes (rutas, paraderos, rodamiento de hoy).
- [ ] `python scripts/crear_usuarios_demo.py` ejecutado; las 4 cuentas inician sesión.
- [ ] Trazados revisados sobre un mapa por una persona del equipo.
- [ ] APK instalado en 2 celulares; ajustes de servidor probados en la red de la clase (o hotspot).
- [ ] Bot de Telegram responde y el aviso "a 300 m" llega.
- [ ] Panel de demo: "perder señal", "fijar hora" y "reiniciar simulación" funcionan.
- [ ] Banner "Datos de ejemplo" visible en las tres interfaces.
- [ ] Video de respaldo de 2 minutos grabado.
- [ ] Portátil cargado, adaptador y hotspot probados.
