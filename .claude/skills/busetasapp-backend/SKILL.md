---
name: busetasapp-backend
description: Guía para construir el backend de BusetasApp (FastAPI hexagonal, Supabase/PostGIS, simulador de GPS, WebSockets). Úsala al crear o modificar casos de uso, repositorios, routers, migraciones, el simulador o el contrato de API en backend/.
---

# Backend de BusetasApp

Documentos fuente (léelos, no los reinventes): `CLAUDE.md`, `backend/CLAUDE.md`, `docs/03-contrato-api.md`, `docs/01-alcance-y-datos-simulados.md`.

## Receta para agregar una funcionalidad

1. Busca la historia (HU) y el endpoint en `docs/03-contrato-api.md`. Si no está, no la construyas: `PENDIENTE(decisión)`.
2. **Dominio:** entidades y servicios puros en `modulos/<modulo>/dominio/` + el puerto (`typing.Protocol`) que necesites. Sin imports de FastAPI, Pydantic ni psycopg.
3. **Prueba unitaria** con repositorio en memoria y `PuertoReloj` fijo.
4. **Aplicación:** el caso de uso en `aplicacion/`, que recibe `Identidad` y sus puertos. La autorización (rol y empresa) se comprueba aquí.
5. **Infraestructura:** repositorio SQL (psycopg, funciones PostGIS), esquemas Pydantic con alias `camelCase` y el router. El router solo traduce HTTP ↔ caso de uso.
6. **Composición:** cablea en `composicion.py`.
7. Actualiza el contrato y exporta `contrato/openapi.json`.

## Reglas rápidas

- Escrituras con `version` → `ErrorConflictoVersion` (409) si no coincide; 404 si no existe o es de otra empresa.
- Errores con el formato de `CLAUDE.md` §6; nunca una traza al cliente.
- Búsquedas por texto: `normalizar_texto(...)` de ambos lados (si no, no se usa el índice).
- Hora siempre por `PuertoReloj`; zona `America/Bogota`.
- Todas las rutas son circulares: distancia al paradero = `(progreso_paradero − progreso_buseta) mod longitud`.
- El simulador entra por `registrar_posiciones`, igual que un GPS real. No lo dupliques en los routers.
- Logs sin tokens, `X-Clave-Fuente`, correos ni coordenadas del pasajero.
- No agregar: Excel, Web Push, geocodificación en ejecución, transbordos, LLM.

## Comprobaciones antes de entregar

`ruff check`, `pytest`, `GET /salud`, y el flujo del bloque (ver `backend/CLAUDE.md` §12–13). Reporta lo `PENDIENTE`.

## Ajustes por la revisión de las SPECs

- Alertas: además de cercanía, aviso de desvío una vez por episodio (`alerta_desvio`, D-P14).
- `PUT /rodamientos/{id}`: reemplazar buseta/conductor de un turno guardado exige `confirmarReemplazo=true` o responde 409 (D-P15).
- `cargar_semillas` incluye 14 días de uso simulado (doc 01 §2.9) y **Villamaría es obligatoria**.
- El jefe no crea rutas (D-P13).
