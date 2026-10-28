"""B1 sin base de datos: consistencia de semillas y del recorte del esquema."""

from __future__ import annotations

import json
import re
from pathlib import Path

import pytest

from cargar_semillas import validar_archivos
from generar_trazados import haversine_m

RAIZ = Path(__file__).resolve().parents[2]
MIGRACIONES = RAIZ / "supabase" / "migraciones"
TODO_SQL = "\n".join(p.read_text(encoding="utf-8") for p in sorted(MIGRACIONES.glob("0*.sql")))


def test_semillas_consistentes() -> None:
    assert validar_archivos() == []


def test_hitos_dentro_de_manizales_y_catedral_cerca_de_la_referencia() -> None:
    hitos = {h["nombre"]: h for h in json.loads((RAIZ / "supabase/semillas/hitos.json").read_text(encoding="utf-8"))}
    for h in hitos.values():
        assert 4.95 <= h["lat"] <= 5.20 and -75.65 <= h["lng"] <= -75.40
    # docs/01 §2.3: la Catedral queda cerca de 5.069 N, 75.517 O
    assert haversine_m((-75.517, 5.069), (hitos["Catedral"]["lng"], hitos["Catedral"]["lat"])) < 1000


def test_cinco_migraciones_en_orden() -> None:
    nombres = [p.name for p in sorted(MIGRACIONES.glob("0*.sql"))]
    assert nombres == [
        "0001_extensiones_y_tipos.sql", "0002_tablas.sql", "0003_indices_y_funciones.sql",
        "0004_seguridad.sql", "0005_parametros.sql",
    ]


@pytest.mark.parametrize("tabla", ["permiso_rol", "dia_festivo", "asignacion", "suscripcion_push", "notificacion", "importacion"])
def test_tablas_eliminadas_no_se_crean(tabla: str) -> None:
    assert not re.search(rf"create table {tabla}\b", TODO_SQL)
    assert not re.search(rf"alter table {tabla}\b", TODO_SQL)


@pytest.mark.parametrize("nombre", [
    "tipo_importacion", "estado_importacion", "canal_notificacion", "estado_notificacion",
    "tipo_de_dia", "limpiar_eventos_uso", "eliminar_ruta_con_asignaciones", "ix_notificacion_user", "ix_asignacion_buseta",
    "max_filas_excel", "tamano_max_excel_mb", "radio_transbordo_m", "retencion_eventos_dias",
])
def test_objetos_eliminados_ausentes(nombre: str) -> None:
    sin_comentarios = re.sub(r"--.*", "", TODO_SQL)
    assert nombre not in sin_comentarios


def test_alerta_llegada_admite_telegram() -> None:
    assert "telegram_chat_id      bigint" in TODO_SQL
    assert "check ((usuario_id is not null) <> (telegram_chat_id is not null))" in TODO_SQL
    assert "ux_alerta_unica_usuario" in TODO_SQL and "ux_alerta_unica_telegram" in TODO_SQL
    assert not re.search(r"\bux_alerta_unica\b", TODO_SQL)


def test_funciones_conservadas_y_renombrada() -> None:
    for f in ("rutas_cercanas", "paraderos_cercanos", "paradero_mas_cercano_a_ruta", "rutas_por_hito", "progreso_en_ruta",
              "progreso_paradero", "turno_vigente", "guardar_posicion", "reemplazar_paraderos_de_ruta",
              "dar_de_baja_ruta", "estadisticas_uso", "normalizar_texto"):
        assert re.search(rf"create or replace function {f}\(", TODO_SQL), f


def test_catorce_parametros() -> None:
    sql = (MIGRACIONES / "0005_parametros.sql").read_text(encoding="utf-8")
    assert len(re.findall(r"^\s+\('[a-z_]+',", sql, flags=re.M)) == 14


def test_buseta_3102_cubre_villamaria_y_la_enea_sin_solaparse() -> None:
    datos = json.loads((RAIZ / "supabase/semillas/datos.json").read_text(encoding="utf-8"))
    turnos = sorted((t for t in datos["rodamientoHoy"] if t["buseta"] == "3102"), key=lambda t: t["salida"])
    assert [t["ruta"] for t in turnos] == ["villamaria", "la-enea"]
    assert turnos[0]["fin"] <= turnos[1]["salida"]


def test_extensiones_en_schema_public_y_tipo_cambio() -> None:
    for e in ("postgis", "pg_trgm", "unaccent", "btree_gist"):
        assert f"create extension if not exists {e} with schema public;" in TODO_SQL
    assert re.search(r"tipo_cambio text check", TODO_SQL)
