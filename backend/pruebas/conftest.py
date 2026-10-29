"""Las pruebas unitarias nunca tocan la base de datos real: se vacía DATABASE_URL antes de importar la app.

Las variables de entorno tienen prioridad sobre `.env` en pydantic-settings, así que esto aísla las pruebas
aunque exista un `backend/.env` con credenciales. Las pruebas de integración (`-m integracion`) exigen
`PRUEBAS_INTEGRACION=1` y entonces se respeta el `.env`.
"""

import os

if os.environ.get("PRUEBAS_INTEGRACION") != "1":
    for variable in ("DATABASE_URL", "TELEGRAM_BOT_TOKEN", "SUPABASE_SERVICE_ROLE_KEY"):
        os.environ[variable] = ""
