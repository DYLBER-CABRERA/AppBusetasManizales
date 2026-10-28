"""Logging con filtro que oculta secretos y datos personales.

Nunca se registran: tokens, cabecera Authorization, X-Clave-Fuente, correos ni coordenadas del pasajero.
"""

from __future__ import annotations

import logging
import re

_PATRONES: list[tuple[re.Pattern[str], str]] = [
    (re.compile(r"(?i)bearer\s+[A-Za-z0-9._\-]+"), "Bearer ***"),
    (re.compile(r"(?i)(x-clave-fuente|token|apikey|api_key|password|clave)\s*[:=]\s*\S+"), r"\1=***"),
    (re.compile(r"eyJ[A-Za-z0-9_\-]{10,}\.[A-Za-z0-9_\-]{10,}\.[A-Za-z0-9_\-]*"), "***jwt***"),
    (re.compile(r"[\w.+\-]+@[\w\-]+\.[\w.\-]+"), "***correo***"),
    (re.compile(r"(?i)\b(lat|lng|latitud|longitud)\s*[:=]\s*-?\d+(\.\d+)?"), r"\1=***"),
]


def ocultar_sensibles(texto: str) -> str:
    for patron, reemplazo in _PATRONES:
        texto = patron.sub(reemplazo, texto)
    return texto


class FiltroSecretos(logging.Filter):
    def filter(self, record: logging.LogRecord) -> bool:
        record.msg = ocultar_sensibles(record.getMessage())
        record.args = None
        return True


def configurar_registro(nivel: int = logging.INFO) -> None:
    raiz = logging.getLogger()
    if not any(isinstance(f, FiltroSecretos) for h in raiz.handlers for f in h.filters):
        manejador = logging.StreamHandler()
        manejador.addFilter(FiltroSecretos())
        manejador.setFormatter(logging.Formatter("%(asctime)s %(levelname)s %(name)s: %(message)s"))
        raiz.addHandler(manejador)
    raiz.setLevel(nivel)
