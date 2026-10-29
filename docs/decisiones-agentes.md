# Decisiones de los agentes

Registra aquí cada decisión que cambie el contrato o el alcance (fecha, agente, qué, por qué).

## 2026-10-27 · backend-dev · B0 y B1

- **Dependencias y versiones fijadas** (`backend/pyproject.toml`; todas gratuitas y de código abierto): fastapi 0.162.0, uvicorn 0.54.0, pydantic 2.14.1, pydantic-settings 2.16.1, psycopg 3.3.6 (+pool), httpx 0.28.1, PyJWT 2.15.1, python-telegram-bot 22.8, pytest 9.2.0, pytest-asyncio 1.4.1, ruff 0.17.3. Son las del `CLAUDE.md` de backend; no se agregó ninguna otra.
- **Contrato en B0:** forma plana de `GET /rutas/{id}` y `paraderoIds` en `POST /rutas` (rutas circulares, D-P02). Detalle en `docs/03-contrato-api.md` §7.
- **`GET /salud` bajo `/api/v1`** y `501 PENDIENTE` como respuesta de los endpoints sin lógica (código `PENDIENTE` fuera de la lista de códigos de CLAUDE.md §6; temporal hasta cerrar B8).
- **Scripts con simulacro por defecto:** `cargar_semillas.py` y `crear_usuarios_demo.py` no tocan ninguna base sin `--aplicar`; `verificar_bd.py` revierte todo (ROLLBACK) y `--aplicar-migraciones` aborta si ya existe `public.empresa`.
- **Hitos adicionales:** además de los 6 de docs/01 §2.3 se geocodifican `La Enea` (barrio) y `Villamaría` (sector), necesarios como puntos de paso y para el ejemplo del bot. Coordenadas marcadas `validado:false` hasta que el equipo las revise en un mapa.
- **Paraderos ficticios:** la tabla `paradero` no tiene columna `ficticio`; se marca con `direccion = 'Paradero de ejemplo (ficticio)'` y con `ficticio:true` en los GeoJSON.
- **Uso histórico:** `evento_uso` no distingue simulado de real y no se modificó la tabla (`PENDIENTE(decisión)` según docs/01 §2.9). Tipos usados: ruta→`detalle_ruta`, horario→`horarios`, ETA→`eta`, paradero→`mapa`.

## 2026-10-27 · backend-dev · decisiones del equipo aplicadas a B1

- **`aviso.tipo_cambio`** (text, nullable, restringido a cierre/desvio/obra/condicion) agregado en `0002_tablas.sql`; la semilla del aviso de movilidad usa `obra`. Resuelve el `PENDIENTE` de `tipoCambio`.
- **Buseta 3102 también en Villamaría:** turno de hoy 04:30–14:00 en Villamaría y 14:00–23:30 en La Enea (supuesto: partir el día como la 1520, porque una buseta no puede estar en dos rutas a la vez). Actualizados `docs/01` §2.6 y `datos.json`. Resuelve el `PENDIENTE` de Socobuses · Villamaría sin buseta.
- **`evento_uso` queda como está:** sin columna que distinga simulado de real (`docs/01` §2.9).
- **Extensiones `with schema public`** (postgis, pg_trgm, unaccent, btree_gist) en `0001`, para que `normalizar_texto` (`public.unaccent`) funcione. `verificar_bd.py` ahora comprueba que estén en `public` y que exista `aviso.tipo_cambio`.

## 2026-10-28 · backend-dev · verificar_bd y progreso en tramos repetidos

- **`verificar_bd.py` independiente de las semillas y de la fecha de hoy:** `turno_vigente`, `guardar_posicion` y las violaciones intencionales crean sus propias empresas, rutas, servicios y busetas (`zz …`) con fechas fijas 2099-01-05/06, y cada verificación corre en un savepoint que siempre se revierte, así no chocan con `ux_rodamiento_empresa_fecha` ni entre sí. Solo `rutas_cercanas`, `progreso` y el sábado de Sideral usan la semilla.
- **Progreso en trazados que repiten calles: opción B (secuencial) con ayuda de A.** Una ruta circular que vuelve por la misma vía (Villamaría es ida y vuelta por la misma carretera) no se puede arreglar solo con puntos de paso: la geometría repite el tramo. Se añade en `0003` la función `progresos_paraderos_ruta(ruta, sentido)` (CTE recursiva: cada paradero se proyecta solo desde el progreso del anterior) y `progreso_paradero` la usa (si el paradero no está en la ruta, cae en la proyección más cercana). `progreso_en_ruta` no cambia. `generar_trazados.py` ahora ubica cada hito en orden de recorrido (primer vértice cercano a partir del anterior) y guarda `avance_m` por paradero; los 4 GeoJSON se regeneraron con OSRM.
- **PENDIENTE (B3):** la posición de una **buseta** sobre un tramo repetido sigue siendo ambigua con `progreso_en_ruta`; el simulador conoce su propio avance y el ingreso real podrá usar el último progreso conocido como pista.

## 2026-10-28 · backend-dev · actualizar_bd.py

- **`backend/scripts/actualizar_bd.py`** (no estaba en la lista de scripts de `backend/CLAUDE.md` §3): actualiza una BD ya migrada y sembrada cuando cambian las funciones de `0003` o los GeoJSON. Simulacro sin conexión por defecto; `--comparar` abre una conexión de solo lectura; `--aplicar` ejecuta todo en una transacción. Reemplaza funciones con `create or replace`, agrega `aviso.tipo_cambio` si falta, actualiza `ruta_trazado` con UPDATE, mueve/crea paraderos por nombre y da de baja (lógica) solo los paraderos ficticios sin ninguna referencia. No toca usuarios, perfiles, rodamientos, avisos, favoritos, alertas ni busetas.

## 2026-10-28 · web-admin-dev · W0

- **Versiones fijadas** (`web-admin/package.json`, todas gratuitas/código abierto): next 16.4.3, react 19.3.1, tailwindcss 4.3.3, @supabase/supabase-js 2.118.0, @supabase/ssr 0.12.7, @tanstack/react-query 5.105.0, openapi-typescript 7.13.0, openapi-fetch 0.17.0, react-hook-form 7.91.0, zod 4.6.7, leaflet 1.9.4, react-leaflet 5.0.0, recharts 3.10.1, eslint 9.39.5.
- **TypeScript 5.9.3, no 7.x:** `openapi-typescript` 7.13 declara `peer typescript@^5` y `npm install` falla con 7.0.2.
- **Dependencias fuera de la lista de `web-admin/CLAUDE.md` §2** (necesarias, licencia MIT): `@hookform/resolvers` 6.0.2 (conecta `zod` con `react-hook-form`); `@tailwindcss/postcss` 4.3.3 y `postcss` 8.5.32 (Tailwind 4 con Next); `eslint-config-next` 16.4.3; tipos de desarrollo `@types/node` 20, `@types/react`, `@types/react-dom`, `@types/leaflet`.
- **`src/proxy.ts` en vez de `src/middleware.ts`:** Next 16 renombró el archivo. Solo exige que exista sesión (cookie de Supabase); el rol lo decide el backend vía `GET /yo` y lo aplica el layout `(panel)`.
- **Modo de ejemplo (PENDIENTE, quitar al integrar):** con `NEXT_PUBLIC_USAR_MOCKS=true` el cliente de API devuelve datos de `src/lib/mocks.ts` (doc 01 §2 y §5) cuando el backend responde 501 o no hay red; sin variables de Supabase el login acepta las cuentas del doc 01 §5 sin verificar contraseña (cookie `busetas_sesion_ejemplo`, solo en el navegador; el backend nunca la reconoce).
- **Tipos:** `src/lib/tipos-api.d.ts` se genera con `npm run tipos` desde `contrato/openapi.json`; no se edita a mano.
