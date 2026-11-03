"""Reconocimiento de lugares (hitos, barrios y rutas) en texto libre del bot. Sin LLM, determinista y sin Telegram.

Por qué existe: la búsqueda de hitos del backend es por SUBCADENA («contiene»). Si el bot le pasa palabras sueltas, «van» (de
«¿qué ruta van a la enea?») coincide con «A-VAN-zada». Aquí el texto se parte en frases candidatas (de la más larga a la más
corta), se consulta la búsqueda y el resultado se filtra en Python por PALABRA COMPLETA:

  1. nombre exacto → 2. alias exacto → 3. palabras completas dentro del nombre o alias (si hay varios, ambigüedad) → 4. rutas.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Any

from modulos.busqueda import normalizar_consulta

ARTICULOS = {"la", "el", "los", "las"}
# Palabras de pregunta o de relleno. Nunca se quitan del interior de una frase candidata: «La Enea» y «Caserío La Enea» se
# prueban completas primero; solo se descartan frases que empiezan (salvo artículo) o terminan con ellas, o que son solo relleno.
VACIAS = ARTICULOS | {
    "que", "ruta", "rutas", "van", "va", "voy", "vamos", "vaya", "pasa", "pasan", "pasar", "por", "para", "hacia", "hasta",
    "desde", "a", "al", "de", "del", "en", "un", "una", "me", "mi", "sirve", "sirven", "como", "llego", "llegar", "cual",
    "cuales", "donde", "hay", "quiero", "quisiera", "necesito", "ir", "bus", "buses", "buseta", "busetas", "cerca", "cuando",
    "llega", "llegan", "horario", "horarios", "aviso", "avisos", "hola", "buenas", "buenos", "dias", "tardes", "noches",
    "gracias", "favor", "lo", "y", "o", "es", "esta", "estan", "se", "tomo", "tomar", "coger", "cogo", "alguna", "algun",
    "toda", "todas", "todos",
}
MAX_PALABRAS = 5
MIN_LETRAS_PARCIAL = 3


@dataclass
class Reconocimiento:
    """`hitos`: coincidencias (1 = reconocido; varios = ambiguo y hay que preguntar). `rutas`: si no hubo hito."""

    hitos: list[dict[str, Any]] = field(default_factory=list)
    rutas: list[dict[str, Any]] = field(default_factory=list)
    frase: str = ""

    @property
    def vacio(self) -> bool:
        return not self.hitos and not self.rutas

    @property
    def ambiguo(self) -> bool:
        return len(self.hitos) > 1


def palabras(texto: str) -> list[str]:
    """Palabras del texto normalizado (minúsculas, sin tildes), sin signos de puntuación."""
    return re.findall(r"\w+", normalizar_consulta(texto))


def frases_candidatas(tokens: list[str]) -> list[list[str]]:
    """Frases contiguas, de la más larga a la más corta. Descarta las que son solo relleno, las que terminan en relleno y las que
    empiezan con relleno que no sea un artículo."""
    frases: list[list[str]] = []
    for largo in range(min(MAX_PALABRAS, len(tokens)), 0, -1):
        for i in range(len(tokens) - largo + 1):
            f = tokens[i:i + largo]
            if all(t in VACIAS for t in f) or f[-1] in VACIAS or (f[0] in VACIAS and f[0] not in ARTICULOS):
                continue
            frases.append(f)
    return frases


def _contiguo(frase: list[str], texto: list[str]) -> bool:
    n = len(frase)
    return any(texto[i:i + n] == frase for i in range(len(texto) - n + 1))


def _nombres(h: dict[str, Any]) -> list[list[str]]:
    return [palabras(h["nombre"]), *(palabras(a) for a in h.get("alias", []))]


class ReconocedorDeLugares:
    def __init__(self, servicios: Any) -> None:
        self._s = servicios

    async def reconocer(self, texto: str) -> Reconocimiento:
        tokens = palabras(texto)
        frases = frases_candidatas(tokens)
        cache: dict[str, list[dict[str, Any]]] = {}

        async def hitos_de(frase: list[str]) -> list[dict[str, Any]]:
            clave = " ".join(frase)
            if clave not in cache:
                cache[clave] = await self._s.buscar_hitos(clave)
            return cache[clave]

        # 1) y 2) coincidencia exacta de nombre y luego de alias, empezando por la frase más larga
        for f in frases:
            candidatos = await hitos_de(f)
            por_nombre = [h for h in candidatos if palabras(h["nombre"]) == f]
            por_alias = [h for h in candidatos if any(palabras(a) == f for a in h.get("alias", []))]
            for exactos in (por_nombre, por_alias):  # el nombre exacto gana al alias exacto
                if exactos:
                    return Reconocimiento(hitos=exactos, frase=" ".join(f))
        # 3) palabras completas dentro del nombre o de un alias (nunca subcadenas dentro de una palabra)
        for f in frases:
            if len(f) == 1 and len(f[0]) < MIN_LETRAS_PARCIAL:
                continue
            parciales = [h for h in await hitos_de(f) if any(_contiguo(f, n) for n in _nombres(h))]
            if parciales:
                return Reconocimiento(hitos=parciales, frase=" ".join(f))
        # 4) rutas por nombre (palabras completas) o por código público
        for f in frases:
            if len(f) == 1 and len(f[0]) < MIN_LETRAS_PARCIAL and not f[0].isdigit():
                continue
            rutas = [
                r for r in await self._s.buscar_rutas_por_texto(" ".join(f))
                if _contiguo(f, palabras(r["nombre"])) or " ".join(f) in {s.get("codigo_publico") for s in r.get("servicios", [])}
            ]
            if rutas:
                return Reconocimiento(rutas=rutas, frase=" ".join(f))
        return Reconocimiento()
