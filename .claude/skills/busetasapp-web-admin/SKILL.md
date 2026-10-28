---
name: busetasapp-web-admin
description: Guía para construir los paneles web de BusetasApp en Next.js (Jefe de operaciones, Secretaría de Movilidad, Administrador y Panel de demo). Úsala al crear o modificar páginas, formularios, tablas o el cliente de API en web-admin/.
---

# Paneles web de BusetasApp

Documentos fuente: `CLAUDE.md`, `web-admin/CLAUDE.md`, `docs/03-contrato-api.md`, mockups `docs/referencia/presentacion-mockup-*.png`, textos en `docs/referencia/03-actividad-4-ux-prototipos.md` §7.

## Receta para una pantalla

1. Ubícala en `web-admin/CLAUDE.md` §5 (ruta, contenido, reglas). Si no está, `PENDIENTE(decisión)`.
2. Usa el cliente tipado de `src/lib/api.ts` (tipos generados con `npx openapi-typescript ../contrato/openapi.json -o src/lib/tipos-api.d.ts`). No escribas a mano tipos del contrato.
3. Datos con TanStack Query; formularios con `react-hook-form` + `zod`; errores del contrato mostrados bajo el campo (400) o en banner (503).
4. Cuatro estados siempre: cargando (esqueleto), vacío (título + causa + acción), error de red (banner rojo con **Reintentar**), éxito (toast con el verbo del botón).
5. Escrituras con `version`; en 409 `CONFLICTO_VERSION` modal "Alguien más cambió esto. Recarga para ver los cambios."
6. Protege la ruta por rol (middleware + `GET /yo`). El backend es quien autoriza.

## Reglas rápidas

- Escritorio primero (≥ 1024 px); barra lateral por rol; banner permanente "Datos de ejemplo · no son rutas oficiales".
- Verde `#0E7C66` para acciones, amarillo `#F6C500` solo para busetas en vivo, rojo ladrillo solo para errores; nunca el color como único canal.
- Leaflet con importación dinámica sin SSR, teselas desde `NEXT_PUBLIC_MAP_TILE_URL`, atribución de OSM.
- Supabase solo para Auth. Sin `service_role`.
- Jefe: nunca envía `empresaId`. Rodamiento: advertencias visibles con texto y fila marcada; **Publicar** deshabilitado mientras haya solapamientos.
- Secretaría: solo recorrido "Circular"; ruta compartida y eliminación con modales de confirmación.
- Admin: la clave de fuente GPS se muestra una sola vez. El Panel de demo solo aparece si `GET /demo/estado` responde 200.
- Excel: pantalla desactivada ("No incluido en el prototipo").

## Comprobaciones antes de entregar

`npm run lint`, `npm run build`, y el recorrido manual de la sección 8 de `web-admin/CLAUDE.md`.

## Ajustes por la revisión de las SPECs

- Modal de confirmación al reemplazar una asignación (409 `CONFLICTO_NEGOCIO` → reenviar con `confirmarReemplazo=true`). Texto en doc 01 §3.1.
- El jefe no crea ni edita rutas ni paraderos.
- La gráfica de uso del jefe ya trae datos simulados; mantén igual el estado vacío.
