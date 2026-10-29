"""Adaptador SQL del simulador: busetas, trazados y el rodamiento de la demo (docs/01 §2.7).

`asegurar_rodamientos_demo` ESCRIBE en la BD (rodamiento y turnos de hoy si faltan) y solo corre con MODO_DEMO=true.
Es idempotente: si ya existe un rodamiento no anulado de la empresa para esa fecha, no lo toca.
"""

from __future__ import annotations

import json
from datetime import date, time, timedelta
from pathlib import Path
from typing import Any
from uuid import UUID

from psycopg import AsyncConnection
from psycopg_pool import AsyncConnectionPool

DATOS_JSON = Path(__file__).resolve().parents[2] / "supabase" / "semillas" / "datos.json"


class RepositorioSimulacionSql:
    def __init__(self, pool: AsyncConnectionPool, ruta_datos: Path = DATOS_JSON) -> None:
        self._pool = pool
        self._ruta_datos = ruta_datos

    async def busetas_activas(self) -> list[dict[str, Any]]:
        async with self._pool.connection() as conexion:
            cursor = await conexion.execute(
                """select b.id as buseta_id, b.numero_lateral, e.id as empresa_id, e.nombre as empresa_nombre
                   from buseta b join empresa e on e.id = b.empresa_id
                   where b.estado = 'activa' and e.estado = 'activo' order by e.nombre, b.numero_lateral"""
            )
            return await cursor.fetchall()

    async def trazado_de_ruta(self, ruta_id: UUID) -> list[list[float]] | None:
        async with self._pool.connection() as conexion:
            cursor = await conexion.execute(
                """select (st_asgeojson(trazado::geometry, 6)::jsonb -> 'coordinates') as coordenadas
                   from ruta_trazado where ruta_id = %s and sentido = 'circular'""",
                (ruta_id,),
            )
            fila = await cursor.fetchone()
        return fila["coordenadas"] if fila else None

    async def limpiar_posiciones(self) -> None:
        async with self._pool.connection() as conexion:
            await conexion.execute("delete from posicion_buseta")

    async def asegurar_rodamientos_demo(self, hoy: date) -> list[str]:
        datos = json.loads(self._ruta_datos.read_text(encoding="utf-8"))
        rutas = {r["slug"]: r["nombre"] for r in datos["rutas"]}
        notas: list[str] = []
        async with self._pool.connection() as conexion:
            for empresa in datos["empresas"]:
                turnos = [t for t in datos["rodamientoHoy"] if t["empresa"] == empresa]
                notas.append(await self._crear(conexion, datos, rutas, empresa, hoy, "publicado", turnos))
            borrador = datos["rodamientoMananaBorrador"]
            notas.append(await self._crear(conexion, datos, rutas, "Sideral", hoy + timedelta(days=1), "borrador", borrador))
        return notas

    async def _uno(self, conexion: AsyncConnection[Any], sql: str, params: tuple[Any, ...]) -> Any:
        cursor = await conexion.execute(sql, params)
        fila = await cursor.fetchone()
        return None if fila is None else next(iter(fila.values()))

    async def _crear(
        self, conexion: AsyncConnection[Any], datos: dict, rutas: dict[str, str], empresa: str, fecha: date, estado: str,
        turnos: list[dict[str, Any]],
    ) -> str:
        empresa_id = await self._uno(
            conexion, "select id from empresa where lower(nombre) = lower(%s) and estado = 'activo'", (empresa,)
        )
        if empresa_id is None:
            return f"Rodamiento {estado} de {empresa} {fecha}: la empresa no existe (¿faltan las semillas?)"
        if await self._uno(
            conexion, "select 1 from rodamiento where empresa_id = %s and fecha = %s and estado <> 'anulado'", (empresa_id, fecha)
        ):
            return f"Rodamiento {estado} de {empresa} {fecha}: ya existía"
        rodamiento_id = await self._uno(
            conexion,
            """insert into rodamiento (empresa_id, fecha, estado, publicado_en)
               values (%s, %s, %s::estado_rodamiento, case when %s = 'publicado' then now() end) returning id""",
            (empresa_id, fecha, estado, estado),
        )
        for t in turnos:
            servicio = await self._uno(
                conexion,
                """select s.id from servicio_ruta s join ruta r on r.id = s.ruta_id
                   where r.nombre = %s and r.estado = 'activo' and s.empresa_id = %s and s.estado <> 'baja'""",
                (rutas[t["ruta"]], empresa_id),
            )
            buseta = await self._uno(
                conexion, "select id from buseta where empresa_id = %s and numero_lateral = %s", (empresa_id, t["buseta"])
            )
            codigo = datos["conductores"][empresa][t["conductor"]][1]
            conductor = await self._uno(
                conexion,
                "select id from conductor where empresa_id = %s and codigo = %s and estado = 'activo'",
                (empresa_id, codigo),
            )
            if servicio is None or buseta is None:
                continue
            await conexion.execute(
                """insert into turno (rodamiento_id, servicio_ruta_id, buseta_id, conductor_id, hora_salida, hora_fin_estimada)
                   values (%s, %s, %s, %s, %s, %s)""",
                (rodamiento_id, servicio, buseta, conductor, time.fromisoformat(t["salida"]), time.fromisoformat(t["fin"])),
            )
        return f"Rodamiento {estado} de {empresa} {fecha}: {len(turnos)} turnos creados"
