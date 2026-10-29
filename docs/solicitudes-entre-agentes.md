# Solicitudes entre agentes

Formato: fecha · quién pide · a quién · qué necesita · estado (abierta/resuelta).

- 2026-10-28 · web-admin-dev → backend-dev · **abierta** · BR-07 dice que el administrador entra a `/jefe` como superconjunto, pero los endpoints del jefe (`/mis-servicios`, `/busetas`, `/conductores`, `/rodamientos`, `/servicios/{id}/horarios`) toman la empresa del token y `GET /yo` del administrador trae `empresaId: null`. Falta definir cómo elige empresa el administrador: ¿parámetro de consulta `empresaId` opcional (solo válido para rol `administrador`) en esos endpoints? Mientras tanto el panel de administrador no mostrará el selector de empresa en `/jefe/*` (`PENDIENTE(decisión)`).
