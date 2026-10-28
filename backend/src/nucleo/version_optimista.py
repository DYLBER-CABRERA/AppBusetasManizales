"""Control de versión optimista (RNF-02)."""

from __future__ import annotations

from nucleo.errores import ErrorConflictoVersion


def verificar_version(version_esperada: int, version_actual: int) -> None:
    if version_esperada != version_actual:
        raise ErrorConflictoVersion(version_actual)
