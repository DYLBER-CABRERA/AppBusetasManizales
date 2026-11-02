"use client";
import { useState } from "react";
import { BannerError } from "@/componentes/BannerError";
import { Esqueleto } from "@/componentes/Esqueleto";
import { Vacio } from "@/componentes/Vacio";
import { hoyBogota, sumarDias } from "@/lib/fechas";
import { useEstadisticasUso } from "@/lib/jefe";
import { GraficaUso } from "./GraficaUso";

const TIPOS: Record<string, string> = {
  mapa: "Mapa", detalle_ruta: "Detalle de ruta", horarios: "Horarios", frecuencias: "Frecuencias",
  eta: "¿Cuándo llega?", busqueda: "Búsquedas", planificacion: "Planificar viaje", busetas_vivo: "Busetas en vivo",
};

export function PantallaUso() {
  const hoy = hoyBogota();
  const [desde, setDesde] = useState(sumarDias(hoy, -13));
  const [hasta, setHasta] = useState(hoy);
  const valido = desde !== "" && hasta !== "" && desde <= hasta;
  const uso = useEstadisticasUso(valido ? desde : sumarDias(hoy, -13), valido ? hasta : hoy);

  const datos = uso.data;
  const totalPorDia = [...(datos?.porDia ?? [])].sort((a, b) => a.dia.localeCompare(b.dia));
  const porRuta = [...(datos?.porRuta ?? [])].sort((a, b) => b.total - a.total);

  return (
    <section className="space-y-6">
      <h1 className="text-2xl font-bold">Estadísticas de uso</h1>

      <div className="flex flex-wrap items-end gap-4">
        <div>
          <label htmlFor="uso-desde" className="block text-sm font-semibold">Desde</label>
          <input id="uso-desde" type="date" max={hasta} value={desde} onChange={(e) => setDesde(e.target.value)}
            className="min-h-11 rounded border border-tinta/40 bg-white px-3" />
        </div>
        <div>
          <label htmlFor="uso-hasta" className="block text-sm font-semibold">Hasta</label>
          <input id="uso-hasta" type="date" min={desde} max={hoy} value={hasta} onChange={(e) => setHasta(e.target.value)}
            className="min-h-11 rounded border border-tinta/40 bg-white px-3" />
        </div>
        {!valido ? <p className="text-sm text-ladrillo">La fecha de inicio no puede ser posterior a la de fin.</p> : null}
      </div>

      {uso.isError ? <BannerError mensaje={uso.error.message} onReintentar={() => uso.refetch()} /> : null}
      {uso.isPending ? <Esqueleto filas={5} /> : null}

      {datos?.sinDatos ? (
        <Vacio titulo="Sin datos" causa="No hay consultas registradas en ese rango de fechas." accion={<span>Prueba con un rango más amplio.</span>} />
      ) : null}

      {datos && !datos.sinDatos ? (
        <>
          <div className="rounded-lg border border-borde bg-white p-4">
            <h2 className="mb-2 text-lg font-bold">Consultas por día</h2>
            <GraficaUso datos={totalPorDia} />
            <details className="mt-3">
              <summary className="min-h-11 cursor-pointer font-semibold">Ver los datos en una tabla</summary>
              <table className="mt-2 w-full text-left">
                <caption className="sr-only">Consultas por día</caption>
                <thead className="bg-fondo text-sm"><tr><th scope="col" className="p-2">Día</th><th scope="col" className="p-2">Consultas</th></tr></thead>
                <tbody>
                  {totalPorDia.map((d) => <tr key={d.dia} className="border-t border-borde"><td className="p-2">{d.dia}</td><td className="p-2">{d.total}</td></tr>)}
                </tbody>
              </table>
            </details>
          </div>

          <div className="grid gap-6 lg:grid-cols-2">
            <div className="overflow-x-auto rounded-lg border border-borde bg-white">
              <table className="w-full text-left">
                <caption className="p-3 text-left font-bold">Consultas por ruta</caption>
                <thead className="bg-fondo text-sm"><tr><th scope="col" className="p-3">Ruta</th><th scope="col" className="p-3">Consultas</th></tr></thead>
                <tbody>
                  {porRuta.map((r) => <tr key={r.rutaId} className="border-t border-borde"><td className="p-3">{r.rutaNombre}</td><td className="p-3">{r.total}</td></tr>)}
                  {porRuta.length === 0 ? <tr><td colSpan={2} className="p-4 text-center">Sin datos por ruta.</td></tr> : null}
                </tbody>
              </table>
            </div>
            <div className="overflow-x-auto rounded-lg border border-borde bg-white">
              <table className="w-full text-left">
                <caption className="p-3 text-left font-bold">Consultas por tipo</caption>
                <thead className="bg-fondo text-sm"><tr><th scope="col" className="p-3">Tipo</th><th scope="col" className="p-3">Consultas</th></tr></thead>
                <tbody>
                  {datos.totalesPorTipo.map((t) => <tr key={t.tipo} className="border-t border-borde"><td className="p-3">{TIPOS[t.tipo] ?? t.tipo}</td><td className="p-3">{t.total}</td></tr>)}
                </tbody>
              </table>
            </div>
          </div>
        </>
      ) : null}
    </section>
  );
}
