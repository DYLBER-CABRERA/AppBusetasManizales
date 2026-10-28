"""Carga los datos simulados (docs/01 §2) en la base apuntada por DATABASE_URL. Idempotente.

Uso:
  python scripts/cargar_semillas.py              # solo valida los archivos de semilla (no abre ninguna conexión)
  python scripts/cargar_semillas.py --aplicar    # inserta en la BD de DATABASE_URL (Supabase si así está en .env)

Orden recomendado: migraciones -> cargar_semillas --aplicar -> crear_usuarios_demo --aplicar -> cargar_semillas --aplicar
(los avisos necesitan perfiles de usuario como autor; la segunda pasada los agrega).
La hora de «hoy» sale de PuertoReloj (RelojReal), nunca de datetime.now().
"""

from __future__ import annotations

import json
import random
import sys
from datetime import date, datetime, time, timedelta
from typing import Any

from _comun import SEMILLAS, conectar
from nucleo.reloj import ZONA_BOGOTA, PuertoReloj, RelojReal

DIRECCION_FICTICIA = "Paradero de ejemplo (ficticio)"
TIPOS_DIA = ("lun_vie", "sabado", "dom_festivo")


def hora(texto: str) -> time:
    h, m = texto.split(":")
    return time(int(h), int(m))


# ---------------------------------------------------------------- validación sin base de datos
def cargar_archivos() -> tuple[dict, list[dict], dict[str, dict]]:
    datos = json.loads((SEMILLAS / "datos.json").read_text(encoding="utf-8"))
    hitos = json.loads((SEMILLAS / "hitos.json").read_text(encoding="utf-8"))
    trazados = {r["slug"]: json.loads((SEMILLAS / "trazados" / f"{r['slug']}.geojson").read_text(encoding="utf-8"))
                for r in datos["rutas"]}
    return datos, hitos, trazados


def validar_archivos() -> list[str]:
    """Devuelve la lista de problemas (vacía = semillas consistentes)."""
    problemas: list[str] = []
    datos, hitos, trazados = cargar_archivos()
    empresas = set(datos["empresas"])
    rutas = {r["slug"] for r in datos["rutas"]}
    nombres_hitos = {h["nombre"] for h in hitos}
    for obligatorio in ("Catedral", "El Cable", "Carrera 23", "Fundadores", "Terminal", "Parque de Caldas"):
        if obligatorio not in nombres_hitos:
            problemas.append(f"Falta el hito {obligatorio}")
    for slug, fc in trazados.items():
        lineas = [f for f in fc["features"] if f["geometry"]["type"] == "LineString"]
        puntos = [f for f in fc["features"] if f["properties"].get("tipo") == "paradero"]
        if len(lineas) != 1:
            problemas.append(f"{slug}: debe tener exactamente un LineString")
            continue
        coords = lineas[0]["geometry"]["coordinates"]
        if coords[0] != coords[-1]:
            problemas.append(f"{slug}: el circuito no cierra")
        if not 6 <= len(puntos) <= 12:
            problemas.append(f"{slug}: {len(puntos)} paraderos (deben ser 6 a 12)")
        if [p["properties"]["orden"] for p in puntos] != list(range(1, len(puntos) + 1)):
            problemas.append(f"{slug}: orden de paraderos no consecutivo")
    for s in datos["servicios"]:
        if s["ruta"] not in rutas or s["empresa"] not in empresas:
            problemas.append(f"Servicio con ruta/empresa desconocida: {s['ruta']} · {s['empresa']}")
    por_ruta = {r: [s["empresa"] for s in datos["servicios"] if s["ruta"] == r] for r in rutas}
    if sorted(por_ruta["villamaria"]) != ["Serviturismo", "Socobuses"]:
        problemas.append("Villamaría es obligatoria (D-P16) y la operan Serviturismo y Socobuses")
    if sorted(por_ruta["la-enea"]) != ["Serviturismo", "Socobuses"]:
        problemas.append("La Enea debe ser compartida por Socobuses y Serviturismo")
    laterales = {(b["empresa"], b["numeroLateral"]) for b in datos["busetas"]}
    for turno in datos["rodamientoHoy"] + datos["rodamientoMananaBorrador"]:
        if (turno["empresa"], turno["buseta"]) not in laterales:
            problemas.append(f"Turno con buseta inexistente: {turno['buseta']}")
        if (turno["ruta"], turno["empresa"]) not in {(s["ruta"], s["empresa"]) for s in datos["servicios"]}:
            problemas.append(f"Turno de {turno['empresa']} en ruta que no opera: {turno['ruta']}")
    if {"2683", "2676"} - {b["numeroLateral"] for b in datos["busetas"]}:
        problemas.append("Faltan las busetas reales 2683 y 2676 (campo)")
    return problemas


# ---------------------------------------------------------------- inserción
def _uno(conn: Any, sql: str, params: tuple) -> Any:
    fila = conn.execute(sql, params).fetchone()
    return fila[0] if fila else None


def cargar_empresas_y_red(conn: Any, datos: dict, hitos: list[dict], trazados: dict[str, dict]) -> dict:
    ids: dict[str, Any] = {"empresa": {}, "ruta": {}, "servicio": {}, "buseta": {}, "conductor": {}}
    for nombre in datos["empresas"]:
        ids["empresa"][nombre] = _uno(conn, "select id from empresa where lower(nombre)=lower(%s) and estado='activo'", (nombre,)) \
            or _uno(conn, "insert into empresa (nombre) values (%s) returning id", (nombre,))
    for h in hitos:
        if not _uno(conn, "select id from hito where nombre=%s and estado='activo'", (h["nombre"],)):
            conn.execute(
                "insert into hito (nombre, tipo, alias, ubicacion) values (%s, %s::tipo_hito, %s, "
                "st_setsrid(st_makepoint(%s, %s), 4326)::geography)",
                (h["nombre"], h["tipo"], h["alias"], h["lng"], h["lat"]),
            )
    for r in datos["rutas"]:
        existente = _uno(conn, "select id from ruta where nombre=%s and estado='activo'", (r["nombre"],))
        if existente:
            ids["ruta"][r["slug"]] = existente
            continue
        ruta_id = _uno(conn, "insert into ruta (nombre, tipo_recorrido, descripcion) values (%s, 'circular', %s) returning id",
                       (r["nombre"], r["descripcion"]))
        ids["ruta"][r["slug"]] = ruta_id
        fc = trazados[r["slug"]]
        linea = next(f for f in fc["features"] if f["geometry"]["type"] == "LineString")["geometry"]
        conn.execute(
            "insert into ruta_trazado (ruta_id, sentido, trazado) values (%s, 'circular', "
            "st_setsrid(st_geomfromgeojson(%s), 4326)::geography)",
            (ruta_id, json.dumps(linea)),
        )
        paraderos = sorted((f for f in fc["features"] if f["properties"].get("tipo") == "paradero"),
                           key=lambda f: f["properties"]["orden"])
        ids_paraderos = []
        for p in paraderos:
            nombre = p["properties"]["nombre"]
            pid = _uno(conn, "select id from paradero where nombre=%s and estado='activo'", (nombre,))
            if not pid:
                lng, lat = p["geometry"]["coordinates"]
                pid = _uno(conn, "insert into paradero (nombre, direccion, ubicacion) values (%s, %s, "
                                 "st_setsrid(st_makepoint(%s, %s), 4326)::geography) returning id",
                           (nombre, DIRECCION_FICTICIA, lng, lat))
            ids_paraderos.append(pid)
        conn.execute("select reemplazar_paraderos_de_ruta(%s, 'circular', %s::uuid[])", (ruta_id, ids_paraderos))
    for s in datos["servicios"]:
        clave = (s["ruta"], s["empresa"])
        sid = _uno(conn, "select id from servicio_ruta where ruta_id=%s and empresa_id=%s and estado<>'baja'",
                   (ids["ruta"][s["ruta"]], ids["empresa"][s["empresa"]]))
        if not sid:
            sid = _uno(conn, "insert into servicio_ruta (ruta_id, empresa_id, codigo_publico, duracion_estandar_min) "
                             "values (%s, %s, %s, %s) returning id",
                       (ids["ruta"][s["ruta"]], ids["empresa"][s["empresa"]], s["codigoPublico"], s["duracionEstandarMin"]))
        ids["servicio"][clave] = sid
        for tipo_dia, h in s["horarios"].items():
            conn.execute(
                "insert into horario (servicio_ruta_id, tipo_dia, primera_salida, ultima_salida, cierre, nota) "
                "values (%s, %s::tipo_dia, %s, %s, %s, %s) on conflict (servicio_ruta_id, tipo_dia) do nothing",
                (sid, tipo_dia, hora(h["primeraSalida"]), hora(h["ultimaSalida"]),
                 hora(h["cierre"]) if h["cierre"] else None, h["nota"]),
            )
        for tipo_dia, franjas in s["frecuencias"].items():
            if _uno(conn, "select 1 from frecuencia where servicio_ruta_id=%s and tipo_dia=%s::tipo_dia limit 1", (sid, tipo_dia)):
                continue
            for f in franjas:
                conn.execute(
                    "insert into frecuencia (servicio_ruta_id, tipo_dia, inicio_minuto, fin_minuto, minutos_min, minutos_max) "
                    "values (%s, %s::tipo_dia, %s, %s, %s, %s)",
                    (sid, tipo_dia, f["inicio"], f["fin"], f["min"], f["max"]),
                )
    for b in datos["busetas"]:
        conn.execute("insert into buseta (empresa_id, numero_lateral) values (%s, %s) on conflict (empresa_id, numero_lateral) do nothing",
                     (ids["empresa"][b["empresa"]], b["numeroLateral"]))
        ids["buseta"][(b["empresa"], b["numeroLateral"])] = _uno(
            conn, "select id from buseta where empresa_id=%s and numero_lateral=%s", (ids["empresa"][b["empresa"]], b["numeroLateral"]))
    for empresa, lista in datos["conductores"].items():
        ids["conductor"][empresa] = []
        for nombre, codigo in lista:
            cid = _uno(conn, "select id from conductor where empresa_id=%s and codigo=%s and estado='activo'",
                       (ids["empresa"][empresa], codigo)) or _uno(
                conn, "insert into conductor (empresa_id, nombre, codigo) values (%s, %s, %s) returning id",
                (ids["empresa"][empresa], nombre, codigo))
            ids["conductor"][empresa].append(cid)
    return ids


def cargar_avisos(conn: Any, datos: dict, ids: dict) -> list[str]:
    notas: list[str] = []
    rol_de = {"empresa": "jefe_operaciones", "movilidad": "secretaria_movilidad", "aplicativo": "administrador"}
    for a in datos["avisos"]:
        if _uno(conn, "select 1 from aviso where titulo=%s and origen=%s::origen_aviso limit 1", (a["titulo"], a["origen"])):
            continue
        empresa_id = ids["empresa"].get(a.get("empresa"))
        autor = _uno(conn, "select id from perfil_usuario where rol=%s::rol_usuario and activo "
                           "and (%s::uuid is null or empresa_id=%s::uuid) limit 1", (rol_de[a["origen"]], empresa_id, empresa_id))
        if not autor:
            notas.append(f"Aviso «{a['titulo']}» omitido: aún no hay perfil de {rol_de[a['origen']]} (corre crear_usuarios_demo y repite)")
            continue
        aviso_id = _uno(conn, "insert into aviso (origen, empresa_id, tipo_cambio, titulo, cuerpo, autor_id) "
                              "values (%s::origen_aviso, %s, %s, %s, %s, %s) returning id",
                        (a["origen"], empresa_id if a["origen"] == "empresa" else None, a.get("tipoCambio"),
                         a["titulo"], a["cuerpo"], autor))
        for slug in a["rutas"]:
            conn.execute("insert into aviso_afecta (aviso_id, ruta_id) values (%s, %s)", (aviso_id, ids["ruta"][slug]))
    return notas


def asegurar_rodamientos(conn: Any, datos: dict, ids: dict, hoy: date) -> list[str]:
    """Rodamiento de hoy (publicado) para todas las empresas y borrador de mañana de Sideral (docs/01 §2.7)."""
    notas: list[str] = []

    def crear(empresa: str, fecha: date, estado: str, turnos: list[dict]) -> None:
        eid = ids["empresa"][empresa]
        if _uno(conn, "select 1 from rodamiento where empresa_id=%s and fecha=%s and estado<>'anulado'", (eid, fecha)):
            notas.append(f"Rodamiento {estado} de {empresa} {fecha}: ya existía, no se modificó")
            return
        rid = _uno(conn, "insert into rodamiento (empresa_id, fecha, estado, publicado_en) values (%s, %s, %s::estado_rodamiento, "
                         "case when %s = 'publicado' then now() end) returning id", (eid, fecha, estado, estado))
        for t in turnos:
            conn.execute(
                "insert into turno (rodamiento_id, servicio_ruta_id, buseta_id, conductor_id, hora_salida, hora_fin_estimada) "
                "values (%s, %s, %s, %s, %s, %s)",
                (rid, ids["servicio"][(t["ruta"], empresa)], ids["buseta"][(empresa, t["buseta"])],
                 ids["conductor"][empresa][t["conductor"]], hora(t["salida"]), hora(t["fin"])),
            )
        notas.append(f"Rodamiento {estado} de {empresa} {fecha}: {len(turnos)} turnos")

    for empresa in datos["empresas"]:
        crear(empresa, hoy, "publicado", [t for t in datos["rodamientoHoy"] if t["empresa"] == empresa])
    crear("Sideral", hoy + timedelta(days=1), "borrador", datos["rodamientoMananaBorrador"])
    return notas


def cargar_uso_historico(conn: Any, datos: dict, ids: dict, hoy: date) -> str:
    """Eventos anónimos de los últimos 14 días, solo si evento_uso está vacía (idempotente).

    PENDIENTE(decisión): evento_uso no tiene columna que distinga simulado de real; no se modificó la tabla.
    """
    if _uno(conn, "select count(*) from evento_uso", ()):
        return "Uso histórico: evento_uso ya tenía datos, no se agregó nada"
    cfg = datos["usoHistorico"]
    azar = random.Random(20261027)
    pesos_hora = [0.2] * 24
    for h in range(24):
        if 6 <= h <= 7 or 17 <= h <= 18:
            pesos_hora[h] = 3.0
        elif 8 <= h <= 16 or 19 <= h <= 21:
            pesos_hora[h] = 1.0
    tipos, pesos_tipo = list(cfg["tipos"]), list(cfg["tipos"].values())
    empresas_de = {slug: [s["empresa"] for s in datos["servicios"] if s["ruta"] == slug] for slug in ids["ruta"]}
    filas = []
    for atras in range(1, cfg["dias"] + 1):
        dia = hoy - timedelta(days=atras)
        factor_dia = 0.5 if dia.weekday() >= 5 else 1.0
        for slug, peso in cfg["pesosRuta"].items():
            n = int(cfg["baseDiaPorRuta"] * peso * factor_dia * azar.uniform(0.8, 1.2))
            for _ in range(n):
                h = azar.choices(range(24), weights=pesos_hora)[0]
                momento = datetime.combine(dia, time(h, azar.randrange(60), azar.randrange(60)), tzinfo=ZONA_BOGOTA)
                filas.append((azar.choices(tipos, weights=pesos_tipo)[0], ids["ruta"][slug],
                              ids["empresa"][azar.choice(empresas_de[slug])], momento))
    with conn.cursor() as cur:
        cur.executemany("insert into evento_uso (tipo, ruta_id, empresa_id, ocurrido_en) values (%s::tipo_evento_uso, %s, %s, %s)", filas)
    return f"Uso histórico: {len(filas)} eventos de ejemplo insertados"


def cargar(conn: Any, reloj: PuertoReloj) -> list[str]:
    datos, hitos, trazados = cargar_archivos()
    hoy = reloj.ahora().date()
    ids = cargar_empresas_y_red(conn, datos, hitos, trazados)
    notas = cargar_avisos(conn, datos, ids)
    notas += asegurar_rodamientos(conn, datos, ids, hoy)
    notas.append(cargar_uso_historico(conn, datos, ids, hoy))
    return notas


def main() -> int:
    problemas = validar_archivos()
    if problemas:
        print("Semillas inconsistentes:\n - " + "\n - ".join(problemas), file=sys.stderr)
        return 1
    print("Archivos de semilla consistentes.")
    if "--aplicar" not in sys.argv:
        print("Modo simulacro: no se tocó ninguna base. Usa --aplicar para insertar en DATABASE_URL.")
        return 0
    with conectar() as conn:
        for nota in cargar(conn, RelojReal()):
            print(" -", nota)
    print("Semillas aplicadas.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
