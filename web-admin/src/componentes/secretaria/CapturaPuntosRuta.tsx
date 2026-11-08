"use client";
import { useState } from "react";
import {
  longitudCircuitoM, MAX_NOMBRE_PUNTO, MAX_PUNTOS, MIN_PUNTOS, muyPegado, type ErrorPunto, type PuntoCapturado,
} from "@/lib/puntos-ruta";
import type { Paradero } from "@/lib/secretaria";
import { MapaCapturaRuta } from "./MapaCapturaRuta";

const boton = "min-h-11 rounded border border-tinta/40 px-3 font-semibold hover:bg-fondo disabled:opacity-40";

type Props = {
  puntos: PuntoCapturado[];
  onCambio: (p: PuntoCapturado[]) => void;
  /** Errores por punto (del backend o de la validación local), para señalar cuál falló. */
  errores: ErrorPunto[];
  existentes: Paradero[];
};

/** Toca el mapa para agregar puntos en orden; deshacer quita el último. El circuito se cierra solo. */
export function CapturaPuntosRuta({ puntos, onCambio, errores, existentes }: Props) {
  const [aviso, setAviso] = useState<string | null>(null);
  const indicesError = errores.map((e) => e.indice);

  function agregar(p: PuntoCapturado) {
    if (puntos.length >= MAX_PUNTOS) return setAviso(`Máximo ${MAX_PUNTOS} puntos por ruta.`);
    if (muyPegado(puntos, p)) return setAviso("Ese punto queda a menos de 10 m del anterior. Toca un poco más lejos.");
    setAviso(null);
    onCambio([...puntos, p]);
  }
  const cambiarNombre = (i: number, nombre: string) =>
    onCambio(puntos.map((p, j) => (j === i ? { ...p, nombre } : p)));

  return (
    <div className="grid gap-4 lg:grid-cols-2">
      <div>
        <MapaCapturaRuta puntos={puntos} conError={indicesError} existentes={existentes} onPunto={agregar} alto={440} />
        <p className="mt-1 text-xs">
          Toca el mapa para agregar puntos en el orden del recorrido. El último punto se une solo con el primero.
        </p>
      </div>
      <div className="space-y-3">
        <div className="flex flex-wrap items-center gap-2">
          <h3 className="font-semibold">Puntos del recorrido ({puntos.length} de {MAX_PUNTOS})</h3>
          <button type="button" className={boton} disabled={puntos.length === 0}
            onClick={() => { setAviso(null); onCambio(puntos.slice(0, -1)); }}>Deshacer último</button>
          <button type="button" className={boton} disabled={puntos.length === 0}
            onClick={() => { setAviso(null); onCambio([]); }}>Borrar todos</button>
        </div>
        {puntos.length >= MIN_PUNTOS ? (
          <p className="text-sm">Longitud aproximada del circuito: {(longitudCircuitoM(puntos) / 1000).toFixed(1)} km.</p>
        ) : null}
        {aviso ? <p role="status" className="rounded border border-amarillo bg-fondo p-2 text-sm">{aviso}</p> : null}
        {errores.length > 0 ? (
          <ul role="alert" className="space-y-1 rounded bg-ladrillo-claro p-3 text-sm text-ladrillo">
            {errores.map((e, i) => <li key={i}>{e.texto}</li>)}
          </ul>
        ) : null}
        {puntos.length === 0 ? (
          <p className="text-sm">Aún no hay puntos. Toca el mapa para empezar (mínimo {MIN_PUNTOS}).</p>
        ) : (
          <ol className="max-h-72 space-y-1 overflow-y-auto">
            {puntos.map((p, i) => (
              <li key={i} className={`flex items-center gap-2 rounded px-2 py-1 ${indicesError.includes(i) ? "bg-ladrillo-claro" : "bg-fondo"}`}>
                <span className="w-7 text-right font-bold">{i + 1}.</span>
                <input type="text" aria-label={`Nombre del punto ${i + 1} (opcional)`} maxLength={MAX_NOMBRE_PUNTO}
                  placeholder="Nombre (opcional)" value={p.nombre ?? ""}
                  onChange={(e) => cambiarNombre(i, e.target.value)}
                  className="min-h-11 flex-1 rounded border border-tinta/40 bg-white px-2" />
              </li>
            ))}
          </ol>
        )}
        <p className="text-xs">Si no escribes nombre, se genera uno automático. Un punto a 20 m o menos de un paradero existente lo reutiliza.</p>
      </div>
    </div>
  );
}
