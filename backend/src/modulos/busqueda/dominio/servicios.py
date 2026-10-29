"""Servicios de dominio de búsqueda (stdlib únicamente)."""

from __future__ import annotations

import unicodedata


def normalizar_consulta(texto: str) -> str:
    """Minúsculas, sin tildes y con espacios colapsados (equivalente a `normalizar_texto` de la BD)."""
    sin_tildes = "".join(c for c in unicodedata.normalize("NFD", texto) if unicodedata.category(c) != "Mn")
    return " ".join(sin_tildes.lower().split())


def patron_contiene(texto_normalizado: str) -> str:
    """Patrón `LIKE '%texto%'` escapando los comodines (`\\`, `%`, `_`)."""
    escapado = texto_normalizado.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")
    return f"%{escapado}%"
