"""Validación del perfil de pasajero (stdlib únicamente)."""

from __future__ import annotations

import re

from nucleo.errores import ErrorValidacion

MAX_NOMBRE = 60


def limpiar_nombre(texto: str | None, campo: str) -> str:
    limpio = " ".join((texto or "").split())
    if not limpio:
        raise ErrorValidacion(f"El {campo} es obligatorio.", [{"campo": campo, "motivo": "obligatorio"}])
    if len(limpio) > MAX_NOMBRE:
        raise ErrorValidacion(f"El {campo} no puede superar {MAX_NOMBRE} caracteres.", [{"campo": campo, "motivo": "muy_largo"}])
    return limpio


def normalizar_celular(texto: str | None) -> str:
    """Móvil colombiano: 10 dígitos que empiezan por 3. Admite +57, espacios, guiones, puntos y paréntesis.
    Devuelve solo los 10 dígitos (p. ej. «+57 300-123 4567» → «3001234567»)."""
    crudo = (texto or "").strip()
    if not re.fullmatch(r"\+?[\d\s\-.()]+", crudo):
        raise ErrorValidacion("El celular no es válido.", [{"campo": "celular", "motivo": "formato"}])
    digitos = re.sub(r"\D", "", crudo)
    if crudo.startswith("+") or len(digitos) == 12:
        if not digitos.startswith("57"):
            raise ErrorValidacion("El celular debe ser colombiano (+57).", [{"campo": "celular", "motivo": "indicativo"}])
        digitos = digitos[2:]
    if not re.fullmatch(r"3\d{9}", digitos):
        raise ErrorValidacion(
            "El celular debe tener 10 dígitos y empezar por 3.", [{"campo": "celular", "motivo": "formato"}]
        )
    return digitos
