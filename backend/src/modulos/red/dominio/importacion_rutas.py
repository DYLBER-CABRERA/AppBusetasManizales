"""Importación de rutas desde un CSV de la Secretaría: lectura, agrupación por ruta y validación por fila (stdlib únicamente).

El archivo es dato NO confiable: solo se lee como texto (nada se ejecuta, no hay fórmulas), con límites de tamaño, filas, rutas y
puntos, y sin registrar nunca su contenido. Una fila = un punto de una ruta, con coordenadas."""

from __future__ import annotations

import csv
import io
import math
import re
import unicodedata
from dataclasses import dataclass, field
from typing import Any

from modulos.red.dominio.puntos_ruta import MAX_PUNTOS, MIN_PUNTOS, validar_puntos
from nucleo.errores import ErrorValidacion

MAX_BYTES = 200 * 1024  # un CSV de 400 filas pesa ~30 KB
MAX_FILAS = 400  # filas de datos no vacías
MAX_RUTAS = 10  # ver docs/03 §25: cada punto es una llamada a OSRM (demo compartido)
MAX_TEXTO = 120
PREFIJOS_DE_FORMULA = ("=", "+", "-", "@", "\t", "\r")

# Plantilla: columnas fijas en español. `empresa` es obligatoria (desde-puntos exige un servicio por ruta).
COLUMNAS = ("ruta", "orden", "latitud", "longitud", "nombre_punto", "empresa", "codigo_publico")
OBLIGATORIAS = ("ruta", "orden", "latitud", "longitud", "empresa")
ALIAS = {
    "ruta": "ruta", "nombre_ruta": "ruta", "orden": "orden", "latitud": "latitud", "lat": "latitud", "longitud": "longitud",
    "lng": "longitud", "lon": "longitud", "nombre_punto": "nombre_punto", "nombre": "nombre_punto", "punto": "nombre_punto",
    "empresa": "empresa", "codigo_publico": "codigo_publico", "codigo": "codigo_publico",
}
PLANTILLA = (
    "ruta,orden,latitud,longitud,nombre_punto,empresa,codigo_publico\n"
    "Ejemplo Fátima a Chipre (datos de ejemplo),1,5.052476,-75.497089,Fátima,Sideral,77\n"
    "Ejemplo Fátima a Chipre (datos de ejemplo),2,5.0617019,-75.5079102,,Sideral,77\n"
    "Ejemplo Fátima a Chipre (datos de ejemplo),3,5.0701278,-75.5179314,,Sideral,77\n"
    "Ejemplo Fátima a Chipre (datos de ejemplo),4,5.07655,-75.525721,Chipre,Sideral,77\n"
)


@dataclass(frozen=True)
class ErrorImportacion:
    fila: int | None  # número de línea del archivo (1 = encabezado); None = error de la ruta completa
    columna: str | None
    motivo: str
    mensaje: str


@dataclass(frozen=True)
class FilaPunto:
    fila: int
    orden: int
    lat: float
    lng: float
    nombre_punto: str | None


@dataclass
class RutaImportada:
    nombre: str
    puntos: list[FilaPunto] = field(default_factory=list)
    empresa: str | None = None
    codigo_publico: str | None = None
    fila_empresa: int | None = None
    errores: list[ErrorImportacion] = field(default_factory=list)


def normalizar(texto: str) -> str:
    sin_tildes = "".join(c for c in unicodedata.normalize("NFD", texto) if unicodedata.category(c) != "Mn")
    return " ".join(sin_tildes.lower().split())


def _general(motivo: str, mensaje: str, columna: str | None = None) -> ErrorValidacion:
    return ErrorValidacion(mensaje, [{"fila": None, "columna": columna, "motivo": motivo}])


# ------------------------------------------------------------------ lectura del CSV
def error_archivo_muy_grande() -> ErrorValidacion:
    return _general("archivo_muy_grande", f"El archivo supera el máximo de {MAX_BYTES // 1024} KB.")


def decodificar(contenido: bytes) -> str:
    if not contenido.strip():
        raise _general("archivo_vacio", "El archivo está vacío.")
    if len(contenido) > MAX_BYTES:
        raise _general("archivo_muy_grande", f"El archivo supera el máximo de {MAX_BYTES // 1024} KB.")
    if contenido[:4] == b"PK\x03\x04":  # un .xlsx es un zip
        raise _general("formato_no_soportado", "Por ahora solo se aceptan archivos CSV. En Excel usa «Guardar como» → CSV UTF-8.")
    for codificacion in ("utf-8-sig", "cp1252"):  # Excel en Windows suele guardar el CSV en cp1252
        try:
            return contenido.decode(codificacion)
        except UnicodeDecodeError:
            continue
    raise _general("codificacion", "No se pudo leer el texto del archivo. Guárdalo como CSV UTF-8.")


def _delimitador(texto: str) -> str:
    primera = next((linea for linea in texto.splitlines() if linea.strip()), "")
    return max((",", ";", "\t"), key=lambda d: primera.count(d)) if any(d in primera for d in ",;\t") else ","


def _numero(texto: str) -> float | None:
    """Decimal con punto o con coma; rechaza separadores de miles y cualquier cosa que no sea un número."""
    limpio = texto.strip().replace(" ", "")
    if limpio.count(",") + limpio.count(".") > 1 and not (limpio.count(".") == 1 and limpio.count(",") == 0):
        return None
    limpio = limpio.replace(",", ".")
    if not re.fullmatch(r"[+-]?\d+(\.\d+)?", limpio):
        return None
    valor = float(limpio)
    return valor if math.isfinite(valor) else None


def _texto(valor: str, columna: str, fila: int, errores: list[ErrorImportacion]) -> str | None:
    limpio = " ".join(valor.split())
    if not limpio:
        return None
    if valor.lstrip(" ").startswith(PREFIJOS_DE_FORMULA) or limpio.startswith(PREFIJOS_DE_FORMULA):
        errores.append(ErrorImportacion(fila, columna, "formula_no_permitida",
                                        "El texto no puede empezar con =, +, - o @ (se confundiría con una fórmula de Excel)."))
        return None
    if len(limpio) > MAX_TEXTO:
        errores.append(ErrorImportacion(fila, columna, "muy_largo", f"Máximo {MAX_TEXTO} caracteres."))
        return None
    if any(unicodedata.category(c) == "Cc" for c in limpio):
        errores.append(ErrorImportacion(fila, columna, "caracteres_invalidos", "Tiene caracteres de control."))
        return None
    return limpio


@dataclass
class ResultadoLectura:
    rutas: list[RutaImportada]
    errores_generales: list[ErrorImportacion]
    total_filas: int
    columnas_ignoradas: list[str]


def leer(contenido: bytes) -> ResultadoLectura:
    """Lee el CSV y agrupa las filas por ruta (nombre sin tildes ni mayúsculas). Los errores generales de formato lanzan
    `ErrorValidacion` (400); los de fila o de ruta quedan en el resultado."""
    texto = decodificar(contenido)
    lector = csv.reader(io.StringIO(texto, newline=""), delimiter=_delimitador(texto))
    try:
        encabezado = next(lector)
    except (StopIteration, csv.Error) as exc:
        raise _general("archivo_vacio", "El archivo no tiene encabezado.") from exc
    indice: dict[str, int] = {}
    ignoradas: list[str] = []
    for i, nombre in enumerate(encabezado):
        clave = ALIAS.get(re.sub(r"[\s\-]+", "_", normalizar(nombre)).strip("_"))
        if clave and clave not in indice:
            indice[clave] = i
        elif nombre.strip():
            ignoradas.append(" ".join(nombre.split())[:40])
    faltan = [c for c in OBLIGATORIAS if c not in indice]
    if faltan:
        raise ErrorValidacion(
            "Faltan columnas obligatorias: " + ", ".join(faltan) + ".",
            [{"fila": 1, "columna": c, "motivo": "columna_obligatoria"} for c in faltan],
        )

    por_ruta: dict[str, RutaImportada] = {}
    generales: list[ErrorImportacion] = []
    filas_datos = 0
    try:
        for registro in lector:
            if not any(celda.strip() for celda in registro):
                continue  # fila vacía
            filas_datos += 1
            if filas_datos > MAX_FILAS:
                raise _general("demasiadas_filas", f"El archivo supera las {MAX_FILAS} filas de datos.")
            numero = lector.line_num
            celda = lambda c, registro=registro: registro[indice[c]] if c in indice and indice[c] < len(registro) else ""  # noqa: E731
            errores: list[ErrorImportacion] = []
            nombre = _texto(celda("ruta"), "ruta", numero, errores)
            if nombre is None:
                if not errores:
                    errores.append(ErrorImportacion(numero, "ruta", "obligatorio", "Falta el nombre de la ruta."))
                generales += errores
                continue
            ruta = por_ruta.setdefault(normalizar(nombre), RutaImportada(nombre))
            orden_txt = celda("orden").strip()
            orden = int(orden_txt) if re.fullmatch(r"\d+", orden_txt) and int(orden_txt) >= 1 else None
            if orden is None:
                errores.append(ErrorImportacion(numero, "orden", "orden_invalido", "El orden debe ser un entero desde 1."))
            lat, lng = _numero(celda("latitud")), _numero(celda("longitud"))
            if lat is None:
                errores.append(ErrorImportacion(numero, "latitud", "numero_invalido", "La latitud debe ser un número (punto o coma decimal)."))
            if lng is None:
                errores.append(ErrorImportacion(numero, "longitud", "numero_invalido", "La longitud debe ser un número (punto o coma decimal)."))
            nombre_punto = _texto(celda("nombre_punto"), "nombre_punto", numero, errores)
            empresa = _texto(celda("empresa"), "empresa", numero, errores)
            codigo = celda("codigo_publico").strip()
            if codigo and not re.fullmatch(r"\d{1,6}", codigo):
                errores.append(ErrorImportacion(numero, "codigo_publico", "codigo_invalido", "El código público son solo dígitos (máx. 6)."))
                codigo = ""
            for nombre_columna, valor, previo in (("empresa", empresa, ruta.empresa), ("codigo_publico", codigo or None, ruta.codigo_publico)):
                if valor and previo and normalizar(valor) != normalizar(previo):
                    errores.append(ErrorImportacion(numero, nombre_columna, f"{nombre_columna}_distinta",
                                                    "Todas las filas de una ruta deben traer el mismo valor."))
                    if nombre_columna == "empresa":
                        empresa = None
                    else:
                        codigo = ""
            if empresa and not ruta.empresa:
                ruta.empresa, ruta.fila_empresa = empresa, numero
            if codigo and not ruta.codigo_publico:
                ruta.codigo_publico = codigo
            if orden is not None and any(p.orden == orden for p in ruta.puntos):
                errores.append(ErrorImportacion(numero, "orden", "orden_duplicado", f"El orden {orden} está repetido en esta ruta."))
            ruta.errores += errores
            if not errores and lat is not None and lng is not None and orden is not None:
                ruta.puntos.append(FilaPunto(numero, orden, lat, lng, nombre_punto))
    except csv.Error as exc:
        raise _general("csv_invalido", "El archivo no es un CSV válido.") from exc
    rutas = list(por_ruta.values())
    if filas_datos == 0:
        raise _general("sin_datos", "El archivo no tiene filas de datos.")
    if len(rutas) > MAX_RUTAS:
        raise _general("demasiadas_rutas", f"El archivo trae {len(rutas)} rutas; el máximo es {MAX_RUTAS}.")
    return ResultadoLectura(rutas, generales, filas_datos, ignoradas)


# ------------------------------------------------------------------ validación de cada ruta
def validar_ruta(ruta: RutaImportada, caja: dict[str, Any]) -> None:
    """Agrega a `ruta.errores` los errores de la ruta completa y de sus puntos (sin tocar la BD)."""
    if len(ruta.nombre) < 2:
        ruta.errores.append(ErrorImportacion(None, "ruta", "nombre_corto", "El nombre de la ruta necesita al menos 2 caracteres."))
    n = len(ruta.puntos)
    if n > MAX_PUNTOS:
        ruta.errores.append(ErrorImportacion(None, None, "demasiados_puntos", f"La ruta tiene {n} puntos; el máximo es {MAX_PUNTOS}."))
    if not ruta.empresa:
        ruta.errores.append(ErrorImportacion(None, "empresa", "falta_empresa", "Indica la empresa que opera la ruta."))
    if ruta.errores or n > MAX_PUNTOS:
        return  # primero se corrigen las filas con problemas
    if n < MIN_PUNTOS:
        ruta.errores.append(ErrorImportacion(None, None, "pocos_puntos", f"Una ruta necesita al menos {MIN_PUNTOS} puntos."))
        return
    ordenados = sorted(ruta.puntos, key=lambda p: p.orden)
    try:
        validar_puntos([{"lat": p.lat, "lng": p.lng} for p in ordenados], caja)
    except ErrorValidacion as exc:
        for d in exc.detalles or []:
            posicion = re.search(r"\[(\d+)\]", d["campo"])
            fila = ordenados[int(posicion.group(1))].fila if posicion else None
            columna = "orden" if d["motivo"] in ("duplicado_consecutivo", "ultimo_igual_al_primero") else "latitud"
            ruta.errores.append(ErrorImportacion(fila, columna, d["motivo"], _MENSAJES.get(d["motivo"], "Punto inválido.")))


_MENSAJES = {
    "fuera_de_zona": "El punto está fuera de la zona de Manizales y Villamaría.",
    "coordenadas_invalidas": "Coordenadas fuera de rango.",
    "duplicado_consecutivo": "El punto está a menos de 10 m del anterior.",
    "ultimo_igual_al_primero": "El último punto no puede coincidir con el primero (el circuito se cierra solo).",
}


def puntos_ordenados(ruta: RutaImportada) -> list[dict[str, Any]]:
    return [{"lat": p.lat, "lng": p.lng, "nombre": p.nombre_punto} for p in sorted(ruta.puntos, key=lambda p: p.orden)]
