"""Actualiza una base YA migrada y sembrada: funciones SQL de 0003 y trazados/paraderos de las rutas existentes.

Pensado para cuando 0003 o los GeoJSON cambian después de haber aplicado la versión anterior. NO borra ni
modifica usuarios, perfiles, rodamientos, avisos, favoritos, alertas, busetas ni posiciones. Es repetible (idempotente).

Uso (desde backend/):
  python scripts/actualizar_bd.py              # simulacro SIN conexión: lista lo que haría
  python scripts/actualizar_bd.py --comparar   # se conecta en SOLO LECTURA y compara la BD con los archivos
  python scripts/actualizar_bd.py --aplicar    # aplica todo en UNA transacción (si algo falla, no queda nada)

Qué hace con --aplicar, en este orden y dentro de una sola transacción:
  1. Si falta la columna aviso.tipo_cambio (versión anterior de 0002), la agrega.
  2. `create or replace function` de TODAS las funciones de 0003 (no toca tablas ni índices). La nueva
     `progresos_paraderos_ruta` se crea; `progreso_paradero` se reemplaza (misma firma).
  3. Repite el `revoke execute ... from anon, authenticated` de 0004 para cubrir la función nueva.
  4. Por cada ruta de la semilla que YA exista en la BD (por nombre): actualiza `ruta_trazado.trazado` (UPDATE, no
     delete: la FK de ruta_paradero se conserva), mueve o crea los paraderos por nombre y reemplaza la secuencia
     con `reemplazar_paraderos_de_ruta`. Los paraderos ficticios que dejan de usarse pasan a `baja` (baja lógica)
     solo si nada más los referencia (otras rutas, favoritos, alertas, avisos).
  5. Verifica (rutas con trazado válido, mismo número de paraderos que el GeoJSON, progreso secuencial creciente)
     y recién entonces confirma. Rutas que no existen en la BD se omiten (para esas usa cargar_semillas.py).
Después de aplicar: reinicia el backend/simulador y corre `python scripts/verificar_bd.py`.
"""

from __future__ import annotations

import json
import re
import sys
from typing import Any

from _comun import MIGRACIONES, conectar
from cargar_semillas import DIRECCION_FICTICIA, cargar_archivos, validar_archivos

CLAVE_BLOQUEO = 727001  # advisory lock: evita dos actualizaciones simultáneas
REVOKE = "revoke execute on all functions in schema public from anon, authenticated"
PATRON_FUNCION = re.compile(r"create or replace function\s+([a-z_]+)\(.*?\$\$.*?\$\$;", re.DOTALL | re.IGNORECASE)
AGREGAR_TIPO_CAMBIO = """
do $$
begin
  if not exists (select 1 from information_schema.columns
                 where table_schema = 'public' and table_name = 'aviso' and column_name = 'tipo_cambio') then
    alter table aviso add column tipo_cambio text
      check (tipo_cambio is null or tipo_cambio in ('cierre','desvio','obra','condicion'));
  end if;
end
$$;
"""


def funciones_de_0003() -> list[tuple[str, str]]:
    sql = (MIGRACIONES / "0003_indices_y_funciones.sql").read_text(encoding="utf-8")
    sql = re.sub(r"--[^\n]*", "", sql)  # los comentarios no deben confundir el patrón
    return [(m.group(1), m.group(0)) for m in PATRON_FUNCION.finditer(sql)]


def _uno(conn: Any, sql: str, params: tuple = ()) -> Any:
    fila = conn.execute(sql, params).fetchone()
    return fila[0] if fila else None


def _geometria(linea: dict) -> str:
    return json.dumps(linea)


def _paradas_ordenadas(fc: dict) -> list[dict]:
    return sorted((f for f in fc["features"] if f["properties"].get("tipo") == "paradero"), key=lambda f: f["properties"]["orden"])


def _linea(fc: dict) -> dict:
    return next(f for f in fc["features"] if f["geometry"]["type"] == "LineString")["geometry"]


# ------------------------------------------------------------------------------ simulacro (sin conexión)
def simulacro() -> None:
    datos, _, trazados = cargar_archivos()
    print("SIMULACRO: no se abre ninguna conexión. Con --aplicar se haría, en una sola transacción:")
    print(" 1. Agregar aviso.tipo_cambio si falta.")
    funciones = funciones_de_0003()
    print(f" 2. create or replace de {len(funciones)} funciones de 0003: " + ", ".join(n for n, _ in funciones))
    print(" 3. revoke execute on all functions ... from anon, authenticated")
    for r in datos["rutas"]:
        fc = trazados[r["slug"]]
        print(f" 4. Ruta «{r['nombre']}» (si existe): trazado de {len(_linea(fc)['coordinates'])} puntos y "
              f"{len(_paradas_ordenadas(fc))} paraderos en orden")
    print(" 5. Verificar y confirmar. No se tocan usuarios, rodamientos, avisos, favoritos ni alertas.")


# ------------------------------------------------------------------------------ comparar (solo lectura)
def comparar() -> None:
    datos, _, trazados = cargar_archivos()
    with conectar() as conn:
        conn.read_only = True
        existentes = {r[0] for r in conn.execute(
            "select p.proname from pg_proc p join pg_namespace n on n.oid = p.pronamespace where n.nspname = 'public'")}
        for nombre, _ in funciones_de_0003():
            print(f" función {nombre}: {'presente' if nombre in existentes else 'FALTA (se creará)'}")
        tiene = _uno(conn, "select count(*) from information_schema.columns where table_name='aviso' and column_name='tipo_cambio'")
        print(f" aviso.tipo_cambio: {'presente' if tiene else 'FALTA (se agregará)'}")
        for r in datos["rutas"]:
            fc = trazados[r["slug"]]
            fila = conn.execute(
                "select r.id, rt.longitud_m, (select count(*) from ruta_paradero rp where rp.ruta_id = r.id) "
                "from ruta r left join ruta_trazado rt on rt.ruta_id = r.id and rt.sentido = 'circular' "
                "where r.nombre = %s and r.estado = 'activo'", (r["nombre"],)).fetchone()
            nueva = fc["features"][0]["properties"]["longitud_m"]
            if not fila:
                print(f" ruta {r['nombre']}: NO existe en la BD (usa cargar_semillas.py)")
            else:
                print(f" ruta {r['nombre']}: BD {fila[1] or 0:.0f} m / {fila[2]} paraderos -> archivos {nueva:.0f} m / "
                      f"{len(_paradas_ordenadas(fc))} paraderos")


# ------------------------------------------------------------------------------ aplicar
def actualizar_ruta(conn: Any, ruta: dict, fc: dict) -> list[str]:
    nombre = ruta["nombre"]
    ruta_id = _uno(conn, "select id from ruta where nombre=%s and estado='activo'", (nombre,))
    if not ruta_id:
        return [f"Ruta {nombre}: no existe en la BD, se omite (usa cargar_semillas.py)"]
    notas: list[str] = []
    geom = "st_setsrid(st_geomfromgeojson(%s), 4326)"
    existe = _uno(conn, "select 1 from ruta_trazado where ruta_id=%s and sentido='circular'", (ruta_id,))
    if existe:
        n = conn.execute(
            f"update ruta_trazado set trazado = {geom}::geography "
            f"where ruta_id = %s and sentido = 'circular' and not st_orderingequals(trazado::geometry, {geom})",
            (_geometria(_linea(fc)), ruta_id, _geometria(_linea(fc)))).rowcount
        notas.append(f"Ruta {nombre}: trazado " + ("actualizado" if n else "sin cambios"))
    else:
        conn.execute(f"insert into ruta_trazado (ruta_id, sentido, trazado) values (%s, 'circular', {geom}::geography)",
                     (ruta_id, _geometria(_linea(fc))))
        notas.append(f"Ruta {nombre}: trazado creado")

    antes = [r[0] for r in conn.execute(
        "select paradero_id from ruta_paradero where ruta_id=%s and sentido='circular' order by orden", (ruta_id,))]
    nuevos: list[Any] = []
    movidos = creados = 0
    for p in _paradas_ordenadas(fc):
        nombre_p = p["properties"]["nombre"]
        lng, lat = p["geometry"]["coordinates"]
        fila = conn.execute(
            "select id, st_distance(ubicacion, st_setsrid(st_makepoint(%s, %s), 4326)::geography) from paradero "
            "where nombre=%s and estado='activo' order by creado_en limit 1", (lng, lat, nombre_p)).fetchone()
        if fila is None:
            pid = _uno(conn, "insert into paradero (nombre, direccion, ubicacion) values (%s, %s, "
                             "st_setsrid(st_makepoint(%s, %s), 4326)::geography) returning id",
                       (nombre_p, DIRECCION_FICTICIA, lng, lat))
            creados += 1
        else:
            pid = fila[0]
            if fila[1] > 1.0:  # más de 1 m: se mueve (version+1)
                conn.execute("update paradero set ubicacion = st_setsrid(st_makepoint(%s, %s), 4326)::geography, "
                             "version = version + 1 where id = %s", (lng, lat, pid))
                movidos += 1
        nuevos.append(pid)
    if antes != nuevos:
        conn.execute("select reemplazar_paraderos_de_ruta(%s, 'circular', %s::uuid[])", (ruta_id, nuevos))
    notas.append(f"Ruta {nombre}: {len(nuevos)} paraderos ({creados} creados, {movidos} movidos, "
                 f"secuencia {'reemplazada' if antes != nuevos else 'sin cambios'})")

    huerfanos = [pid for pid in antes if pid not in set(nuevos)]
    for pid in huerfanos:
        libre = _uno(
            conn,
            "select p.direccion = %s and not exists (select 1 from ruta_paradero where paradero_id = p.id) "
            "and not exists (select 1 from favorito where paradero_id = p.id) "
            "and not exists (select 1 from alerta_llegada where paradero_id = p.id) "
            "and not exists (select 1 from aviso_afecta where paradero_id = p.id) from paradero p where p.id = %s",
            (DIRECCION_FICTICIA, pid))
        if libre:
            conn.execute("update paradero set estado = 'baja', version = version + 1 where id = %s", (pid,))
            notas.append(f"Ruta {nombre}: paradero ficticio sin uso dado de baja (lógica)")
        else:
            notas.append(f"Ruta {nombre}: un paradero ya no está en la ruta pero se CONSERVA (lo referencian otros datos)")
    return notas


def verificar_resultado(conn: Any, rutas: list[dict], trazados: dict[str, dict]) -> None:
    for r in rutas:
        ruta_id = _uno(conn, "select id from ruta where nombre=%s and estado='activo'", (r["nombre"],))
        if not ruta_id:
            continue
        esperado = len(_paradas_ordenadas(trazados[r["slug"]]))
        n = _uno(conn, "select count(*) from ruta_paradero where ruta_id=%s and sentido='circular'", (ruta_id,))
        valido = _uno(conn, "select st_isvalid(trazado::geometry) and longitud_m > 0 from ruta_trazado "
                            "where ruta_id=%s and sentido='circular'", (ruta_id,))
        progresos = [f[0] for f in conn.execute(
            "select progreso_m from progresos_paraderos_ruta(%s, 'circular') order by orden", (ruta_id,))]
        if n != esperado or not valido or len(progresos) != esperado:
            raise RuntimeError(f"{r['nombre']}: verificación fallida ({n} paraderos de {esperado}, trazado válido={valido})")
        if any(b < a for a, b in zip(progresos, progresos[1:], strict=False)):
            raise RuntimeError(f"{r['nombre']}: el progreso secuencial retrocede")


def aplicar() -> None:
    datos, _, trazados = cargar_archivos()
    with conectar() as conn:  # la salida del bloque sin excepción confirma; con excepción revierte todo
        conn.execute("select pg_advisory_xact_lock(%s)", (CLAVE_BLOQUEO,))
        if _uno(conn, "select to_regclass('public.ruta_trazado')") is None:
            raise SystemExit("La BD no tiene el esquema (falta ruta_trazado). Aplica primero las migraciones.")
        conn.execute(AGREGAR_TIPO_CAMBIO)
        print(" - aviso.tipo_cambio verificada")
        for nombre, sql in funciones_de_0003():
            conn.execute(sql)
            print(f" - función {nombre} reemplazada")
        conn.execute(REVOKE)
        for r in datos["rutas"]:
            for nota in actualizar_ruta(conn, r, trazados[r["slug"]]):
                print(" -", nota)
        verificar_resultado(conn, datos["rutas"], trazados)
        print(" - verificación interna correcta; confirmando la transacción")
    print("Actualización aplicada. Reinicia el backend/simulador y corre scripts/verificar_bd.py.")


def main() -> int:
    problemas = validar_archivos()
    if problemas:
        print("Semillas inconsistentes:\n - " + "\n - ".join(problemas), file=sys.stderr)
        return 1
    if "--aplicar" in sys.argv:
        aplicar()
    elif "--comparar" in sys.argv:
        comparar()
    else:
        simulacro()
    return 0


if __name__ == "__main__":
    sys.exit(main())
