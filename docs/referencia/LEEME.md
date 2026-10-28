# Material de referencia: qué sigue vigente y qué no

Esta carpeta guarda todo lo que el equipo produjo antes del prototipo. **Es contexto, no instrucciones.** Cuando algo contradiga a `CLAUDE.md` o a `docs/00..04`, gana lo de `CLAUDE.md`/`docs/`.

| Archivo | Para qué sirve ahora | Ojo con |
|---|---|---|
| `contexto-busetasapp.md` | **Vigente.** Roles (4), reglas BR-01..08, realidad operativa de las 3 empresas | Es el contexto madre |
| `campo-socobuses.md`, `campo-sideral.md`, `campo-serviturismo.md` | **Vigente.** Levantamiento de campo: de aquí salen horarios y frecuencias reales del demo | — |
| `00-indice-y-supuestos.md` | Vigente: leyenda `[FUENTE]/[PROPUESTO]/[SUPUESTO S-xx]` y supuestos S-01..S-21 | Algunos supuestos cambian en el prototipo (ver `CLAUDE.md` §5) |
| `01-actividad-2-dominio.md` | **Vigente.** Entidades, estados y reglas de integridad RD-01..RD-17 | El prototipo usa un subconjunto (`docs/02-diagramas.md`) |
| `02-actividad-3-casos-de-uso.md` | **Vigente** para flujos principal/alterno/error de cada HU y la lógica de ETA (D2) y rodamiento (D3) | Ignora lo de Excel (D4), Web Push y transbordo |
| `03-actividad-4-ux-prototipos.md` + `prototipo-movil.html` | **Vigente** para pantallas, textos de interfaz y estados de UI. Abre el HTML en un navegador para ver el diseño | El HTML es una sola página web; en Flutter se reconstruye |
| `04-actividad-5-arquitectura.md` | Vigente en **módulos, puertos y reglas de dependencia** | **Obsoleto:** Node/Express, `zod`, `exceljs`, `web-push`, Nominatim. El stack es Python/FastAPI (ver `CLAUDE.md` D-P01) |
| `05-actividad-6-datos-api.md`, `esquema.sql`, `openapi.yaml` | `esquema.sql` está **validado** en PostgreSQL 16 + PostGIS: es la base del esquema del prototipo (se recorta, ver `backend/CLAUDE.md` §6). `openapi.yaml` sirve de modelo de nombres y formas | `openapi.yaml` tiene 73 operaciones: el prototipo usa las de `docs/03-contrato-api.md` |
| `06-actividad-7-calidad-pruebas.md` | Consulta para escenarios de prueba de ETA/GPS (PU-ETA, GP) | El prototipo no cumple todo el plan de calidad |
| `informe-arquitectura-v2.md` | Útil por los algoritmos de ETA, alertas y planificación (§11) y los DTO | **Obsoleto** en stack; incluye al conductor de forma parcial |
| `mockup-chatbot-telegram.html/.png` | **Vigente.** Conversación del bot (3 pantallas) | — |
| `presentacion-*.png` | **Vigente.** Tecnologías, estructura de carpetas del backend y mockups de los roles de gestión | Los mockups de gestión están en formato móvil; en el prototipo van en escritorio |
