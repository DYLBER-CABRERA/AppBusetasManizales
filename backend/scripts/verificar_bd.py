"""Pruebas de humo de la base de datos: restricciones y funciones SQL con los datos semilla.

Uso:
  python scripts/verificar_bd.py                        # verifica la BD de DATABASE_URL (todo dentro de una transacción que se revierte)
  python scripts/verificar_bd.py --aplicar-migraciones  # antes, aplica 0001..0005 SOLO si la BD está limpia (sin tabla `empresa`)

Las verificaciones nunca dejan datos: al final se hace ROLLBACK. Las violaciones intencionales usan savepoints.
Si algo falla en Supabase se reporta tal cual (exit code 1); no se maquilla.
"""

from __future__ import annotations

import sys
from collections.abc import Callable
from datetime import datetime, timedelta
from typing import Any

import psycopg

from _comun import MIGRACIONES, conectar
from nucleo.reloj import ZONA_BOGOTA

FECHA_PRUEBA = "2099-01-05"
FECHA_PRUEBA_2 = "2099-01-06"
TABLAS_ELIMINADAS = ("permiso_rol", "dia_festivo", "asignacion", "suscripcion_push", "notificacion", "importacion")
TABLAS_CONSERVADAS = (
    "empresa", "perfil_usuario", "ruta", "ruta_trazado", "paradero", "ruta_paradero", "hito", "servicio_ruta", "horario",
    "frecuencia", "buseta", "conductor", "rodamiento", "turno", "credencial_fuente_gps", "posicion_buseta", "aviso",
    "aviso_afecta", "favorito", "alerta_llegada", "evento_uso", "parametro_global",
)
FUNCIONES = (
    "normalizar_texto", "rutas_cercanas", "paraderos_cercanos", "paradero_mas_cercano_a_ruta", "rutas_por_hito",
    "progreso_en_ruta", "progreso_paradero", "turno_vigente", "guardar_posicion", "reemplazar_paraderos_de_ruta",
    "dar_de_baja_ruta", "estadisticas_uso",
)


class Saltada(Exception):  # noqa: N818
    """Faltan datos semilla para esta verificación."""


class Aviso(Exception):  # noqa: N818
    """Resultado no fatal que el equipo debe revisar."""


class Revertir(Exception):  # noqa: N818
    """Fuerza el rollback del savepoint."""


class Verificador:
    def __init__(self, conn: Any) -> None:
        self.conn = conn
        self.resultados: list[tuple[str, str, str]] = []

    def uno(self, sql: str, params: tuple = ()) -> Any:
        fila = self.conn.execute(sql, params).fetchone()
        return fila[0] if fila else None

    def comprobar(self, nombre: str, fn: Callable[[], str]) -> None:
        try:
            with self.conn.transaction():
                detalle = fn()
            self.resultados.append(("OK", nombre, detalle))
        except Saltada as e:
            self.resultados.append(("SALTADA", nombre, str(e)))
        except Aviso as e:
            self.resultados.append(("AVISO", nombre, str(e)))
        except (AssertionError, psycopg.Error) as e:
            self.resultados.append(("FALLO", nombre, f"{type(e).__name__}: {str(e).splitlines()[0] if str(e) else ''}"))

    def debe_fallar(self, nombre: str, sqlstates: tuple[str, ...], accion: Callable[[], None]) -> None:
        def intento() -> str:
            try:
                with self.conn.transaction():
                    accion()
                    raise Revertir
            except Revertir:
                raise AssertionError("la operación inválida NO falló (restricción ausente)") from None
            except psycopg.Error as e:
                if e.sqlstate not in sqlstates:
                    raise AssertionError(f"falló con SQLSTATE {e.sqlstate}, se esperaba {'/'.join(sqlstates)}") from None
                return f"rechazada como se esperaba (SQLSTATE {e.sqlstate})"

        self.comprobar(nombre, intento)


def aplicar_migraciones(conn: Any) -> None:
    if conn.execute("select to_regclass('public.empresa')").fetchone()[0] is not None:
        raise SystemExit("La BD NO está limpia (ya existe public.empresa). No se aplican migraciones sobre datos existentes.")
    archivos = sorted(MIGRACIONES.glob("0*.sql"))
    for archivo in archivos:
        conn.execute(archivo.read_text(encoding="utf-8"))
        print(f" - aplicada {archivo.name}")
    conn.commit()


def ejecutar(v: Verificador) -> None:
    c = v.conn

    def estructura() -> str:
        presentes = {r[0] for r in c.execute("select table_name from information_schema.tables where table_schema='public'")}
        assert not (set(TABLAS_ELIMINADAS) & presentes), f"quedan tablas eliminadas: {set(TABLAS_ELIMINADAS) & presentes}"
        assert not (set(TABLAS_CONSERVADAS) - presentes), f"faltan tablas: {set(TABLAS_CONSERVADAS) - presentes}"
        funciones = {r[0] for r in c.execute("select proname from pg_proc p join pg_namespace n on n.oid=p.pronamespace where n.nspname='public'")}
        assert not (set(FUNCIONES) - funciones), f"faltan funciones: {set(FUNCIONES) - funciones}"
        assert not ({"tipo_de_dia", "limpiar_eventos_uso", "eliminar_ruta_con_asignaciones"} & funciones)
        fuera = [r[0] for r in c.execute("select e.extname from pg_extension e join pg_namespace n on n.oid=e.extnamespace "
                                         "where e.extname in ('postgis','unaccent','pg_trgm','btree_gist') and n.nspname<>'public'")]
        assert not fuera, f"extensiones fuera del esquema public: {fuera} (normalizar_texto usa public.unaccent)"
        assert v.uno("select count(*) from information_schema.columns where table_name='aviso' and column_name='tipo_cambio'") == 1
        return f"{len(TABLAS_CONSERVADAS)} tablas y {len(FUNCIONES)} funciones presentes; tablas/funciones eliminadas ausentes"

    v.comprobar("Estructura del esquema recortado", estructura)

    def parametros() -> str:
        n = v.uno("select count(*) from parametro_global")
        assert n == 14, f"se esperaban 14 parámetros y hay {n}"
        assert not v.uno("select count(*) from parametro_global where clave in "
                         "('max_filas_excel','tamano_max_excel_mb','radio_transbordo_m','retencion_eventos_dias')")
        return "14 parámetros (13 + caja_ciudad); los de Excel/transbordo/retención no existen"

    v.comprobar("Parámetros globales", parametros)

    def hay_semillas() -> None:
        if not v.uno("select count(*) from ruta") or not v.uno("select count(*) from hito"):
            raise Saltada("faltan semillas (corre cargar_semillas.py --aplicar)")

    def rutas_cercanas() -> str:
        hay_semillas()
        lat, lng = c.execute("select st_y(ubicacion::geometry), st_x(ubicacion::geometry) from hito where nombre='Catedral'").fetchone()
        filas = c.execute("select nombre, distancia_m from rutas_cercanas(%s, %s, 800)", (lat, lng)).fetchall()
        assert filas, "ninguna ruta a menos de 800 m de la Catedral"
        lejos = c.execute("select count(*) from rutas_cercanas(%s, %s, 800)", (5.5, -74.0)).fetchone()[0]
        assert lejos == 0, "una coordenada fuera de la ciudad devolvió rutas"
        return "Catedral: " + ", ".join(f"{n} ({d:.0f} m)" for n, d in filas) + "; punto lejano: sin rutas"

    v.comprobar("rutas_cercanas con la semilla", rutas_cercanas)

    def progreso_circular() -> str:
        hay_semillas()
        avisos, detalle = [], []
        for ruta_id, nombre in c.execute("select id, nombre from ruta where tipo_recorrido='circular' and estado='activo' order by nombre").fetchall():
            longitud = v.uno("select longitud_m from ruta_trazado where ruta_id=%s and sentido='circular'", (ruta_id,))
            primero = c.execute("select st_y(st_startpoint(trazado::geometry)), st_x(st_startpoint(trazado::geometry)) "
                                "from ruta_trazado where ruta_id=%s", (ruta_id,)).fetchone()
            p0, d0, _ = c.execute("select progreso_m, desvio_m, longitud_m from progreso_en_ruta(%s,'circular',%s,%s)",
                                  (ruta_id, *primero)).fetchone()
            assert min(p0, longitud - p0) < 5 and d0 < 5, f"{nombre}: el punto de inicio no proyecta en 0/L (progreso {p0:.0f} de {longitud:.0f})"
            progresos = []
            for lat, lng in c.execute("select st_y(p.ubicacion::geometry), st_x(p.ubicacion::geometry) from ruta_paradero rp "
                                      "join paradero p on p.id=rp.paradero_id where rp.ruta_id=%s order by rp.orden", (ruta_id,)):
                prog, desv, _ = c.execute("select progreso_m, desvio_m, longitud_m from progreso_en_ruta(%s,'circular',%s,%s)",
                                          (ruta_id, lat, lng)).fetchone()
                assert -1 <= prog <= longitud + 1, f"{nombre}: progreso fuera de [0, L]"
                progresos.append((prog, desv))
            if any(b[0] + 50 < a[0] for a, b in zip(progresos, progresos[1:], strict=False)):
                avisos.append(f"{nombre}: el progreso de los paraderos no crece en orden (trazado que repite calles; revisar el GeoJSON)")
            if max(d for _, d in progresos) > 100:
                avisos.append(f"{nombre}: algún paradero queda a más de 100 m del trazado")
            detalle.append(f"{nombre} L={longitud / 1000:.1f} km")
        if avisos:
            raise Aviso("; ".join(avisos))
        return "progreso_en_ruta coherente en circular: " + ", ".join(detalle)

    v.comprobar("progreso_en_ruta en rutas circulares", progreso_circular)

    def ids_para_turnos() -> tuple[Any, ...]:
        hay_semillas()
        fila = c.execute(
            "select e.id, b.id, b.numero_lateral, s1.id, s2.id from empresa e "
            "join buseta b on b.empresa_id=e.id and b.numero_lateral='1520' "
            "join servicio_ruta s1 on s1.empresa_id=e.id and s1.ruta_id=(select id from ruta where nombre='El Cable') "
            "join servicio_ruta s2 on s2.empresa_id=e.id and s2.ruta_id=(select id from ruta where nombre='Centro') "
            "where e.nombre='Sideral'").fetchone()
        if not fila:
            raise Saltada("faltan Sideral/1520/El Cable/Centro en la semilla")
        return fila

    def turno_vigente() -> str:
        empresa, buseta, lateral, cable, centro = ids_para_turnos()
        rid = v.uno("insert into rodamiento (empresa_id, fecha, estado) values (%s, %s, 'publicado') returning id", (empresa, FECHA_PRUEBA))
        for servicio, a, b in ((cable, "05:00", "13:00"), (centro, "13:00", "22:00")):
            c.execute("insert into turno (rodamiento_id, servicio_ruta_id, buseta_id, hora_salida, hora_fin_estimada) values (%s,%s,%s,%s,%s)",
                      (rid, servicio, buseta, a, b))

        def en(hora: str) -> Any:
            instante = datetime.fromisoformat(f"{FECHA_PRUEBA}T{hora}").replace(tzinfo=ZONA_BOGOTA)
            return v.uno("select turno_vigente(%s, %s, %s)", (empresa, lateral, instante))

        assert en("06:00:00") == cable, "a las 06:00 debía ser El Cable"
        assert en("14:00:00") == centro, "a las 14:00 debía ser Centro (la buseta cambia de ruta)"
        assert en("03:00:00") is None and en("22:30:00") is None, "fuera de turno debía devolver null"
        return "1520: 06:00 -> El Cable, 14:00 -> Centro, 03:00 y 22:30 -> sin turno"

    v.comprobar("turno_vigente (buseta con dos turnos)", turno_vigente)

    def guardar_posicion() -> str:
        _, buseta, _, cable, _ = ids_para_turnos()
        t = datetime.fromisoformat("2099-01-05T10:00:00").replace(tzinfo=ZONA_BOGOTA)

        def guardar(momento: datetime) -> Any:
            return v.uno("select guardar_posicion(%s,%s,5.0675,-75.5100,30,90,%s)", (buseta, cable, momento))

        assert guardar(t) is True, "la primera posición debía aceptarse"
        assert guardar(t - timedelta(seconds=10)) is False, "una posición más vieja debía descartarse"
        assert guardar(t + timedelta(seconds=3)) is True, "una posición más nueva debía aceptarse"
        return "acepta, descarta la antigua y acepta la nueva"

    v.comprobar("guardar_posicion", guardar_posicion)

    def variante_de_variante() -> None:
        a = v.uno("insert into ruta (nombre) values ('Prueba A') returning id")
        b = v.uno("insert into ruta (nombre, ruta_principal_id) values ('Prueba B', %s) returning id", (a,))
        c.execute("insert into ruta (nombre, ruta_principal_id) values ('Prueba C', %s)", (b,))

    v.debe_fallar("Violación: variante de una variante", ("23514",), variante_de_variante)

    def franjas_solapadas() -> None:
        s = v.uno("select id from servicio_ruta where estado<>'baja' limit 1")
        if not s:
            raise Saltada("sin servicios en la semilla")
        c.execute("insert into frecuencia (servicio_ruta_id, tipo_dia, inicio_minuto, fin_minuto, minutos_min, minutos_max) "
                  "values (%s,'sabado',480,600,5,5)", (s,))
        c.execute("insert into frecuencia (servicio_ruta_id, tipo_dia, inicio_minuto, fin_minuto, minutos_min, minutos_max) "
                  "values (%s,'sabado',540,660,5,5)", (s,))

    # Si la semilla está vacía, `Saltada` se propaga como SALTADA (no como violación).
    v.debe_fallar("Violación: franjas de frecuencia solapadas", ("23P01",), franjas_solapadas)

    def turno_otra_empresa() -> None:
        empresa, _, _, cable, _ = ids_para_turnos()
        ajena = v.uno("select id from buseta where empresa_id<>%s limit 1", (empresa,))
        rid = v.uno("insert into rodamiento (empresa_id, fecha) values (%s, %s) returning id", (empresa, FECHA_PRUEBA_2))
        c.execute("insert into turno (rodamiento_id, servicio_ruta_id, buseta_id, hora_salida) values (%s,%s,%s,'06:00')", (rid, cable, ajena))

    v.debe_fallar("Violación: turno con buseta de otra empresa", ("23514",), turno_otra_empresa)

    def alerta_sin_dueno() -> None:
        ruta, paradero = c.execute("select ruta_id, paradero_id from ruta_paradero limit 1").fetchone()
        c.execute("insert into alerta_llegada (ruta_id, paradero_id, sentido, distancia_aviso_m) values (%s,%s,'circular',300)", (ruta, paradero))

    v.debe_fallar("Violación: alerta sin usuario ni chat de Telegram", ("23514",), alerta_sin_dueno)

    def sabado_sideral() -> str:
        hay_semillas()
        n = v.uno("select count(*) from horario h join servicio_ruta s on s.id=h.servicio_ruta_id join empresa e on e.id=s.empresa_id "
                  "where e.nombre='Sideral' and h.tipo_dia='sabado'")
        assert n == 0, "Sideral no debe tener horario de sábado (dato pendiente a propósito)"
        return "Sideral sin horario de sábado (pendiente_actualizacion)"

    v.comprobar("Semilla: sábado de Sideral sin dato", sabado_sideral)


def main() -> int:
    with conectar() as conn:
        if "--aplicar-migraciones" in sys.argv:
            print("Aplicando migraciones en limpio:")
            aplicar_migraciones(conn)
        v = Verificador(conn)
        try:
            ejecutar(v)
        finally:
            conn.rollback()  # no queda nada de las pruebas
    ancho = max(len(n) for _, n, _ in v.resultados)
    for estado, nombre, detalle in v.resultados:
        print(f"[{estado:7}] {nombre.ljust(ancho)}  {detalle}")
    fallos = [r for r in v.resultados if r[0] == "FALLO"]
    print(f"\n{len(v.resultados)} verificaciones: {len(fallos)} con FALLO, "
          f"{sum(r[0] == 'AVISO' for r in v.resultados)} con AVISO, {sum(r[0] == 'SALTADA' for r in v.resultados)} saltadas.")
    return 1 if fallos else 0


if __name__ == "__main__":
    sys.exit(main())
