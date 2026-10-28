---
name: busetasapp-mobile
description: Guía para construir la app móvil del pasajero de BusetasApp en Flutter (mapa, rutas, ETA, tiempo real por WebSocket, favoritos, alertas) y generar el APK gratuito. Úsala al crear o modificar código en mobile/.
---

# App móvil de BusetasApp (Flutter, Android)

Documentos fuente: `CLAUDE.md`, `mobile/CLAUDE.md`, `docs/03-contrato-api.md`, `docs/04-guia-ejecucion-y-apk.md`, y el diseño en `docs/referencia/prototipo-movil.html` (ábrelo en un navegador).

## Receta para una pantalla

1. Ubícala en `mobile/CLAUDE.md` §4 (qué hace, endpoints). Si no está, `PENDIENTE(decisión)`.
2. Estructura por característica: `datos/` (API), `dominio/` (modelos), `presentacion/` (pantallas y *providers* Riverpod). Nada de lógica de negocio en los *widgets*.
3. Implementa los estados: cargando (esqueletos), vacío, error de conexión (**Reintentar** conservando lo cargado), desactualizado, sin señal, sin sesión.
4. Textos exactos de `docs/referencia/03-actividad-4-ux-prototipos.md` §7.

## Reglas rápidas

- Se usa **sin cuenta**; la sesión (Supabase Auth) solo para Guardados y alertas.
- Tiempo real: WebSocket `/ws/rutas/{id}` con reconexión (1, 2, 4, 8 s, máx. 15 s) y respaldo REST periódico; cerrar el socket al salir; interpolar posiciones para animar.
- ETA: tres fuentes (`gps`, `horario`, `no_disponible`); siempre mostrar la fuente.
- Mapa: `flutter_map` + teselas de `MAP_TILE_URL` + atribución visible. Busetas amarillas con número lateral; sin señal en gris con texto.
- Ubicación solo para "cerca de ti"; no se guarda ni se registra. Si se niega: centro de Manizales.
- Servidor editable en Ajustes con "Probar conexión" (`/salud`). `--dart-define` para `API_BASE_URL`, `SUPABASE_URL`, `SUPABASE_ANON_KEY`, `MAP_TILE_URL`.
- Android release: permiso `INTERNET`, ubicación y tráfico en claro hacia la red local.
- Accesibilidad: objetivos ≥ 44 dp, `Semantics`, contraste ≥ 4.5:1; modo oscuro automático.

## Comprobaciones antes de entregar

`flutter analyze`, `flutter test`, y el recorrido en un celular real (sección 8 de `mobile/CLAUDE.md`). APK: `flutter build apk --release …` (ver guía).

## Ajustes por la revisión de las SPECs

- Textos de «sin busetas en servicio» y «ruta inexistente → rutas cercanas»: doc 01 §3.1.
- Maneja el evento `alerta_desvio` de `/ws/notificaciones`.
- Villamaría es una ruta más del catálogo.
