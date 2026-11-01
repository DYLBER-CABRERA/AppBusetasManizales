"use client";
import { useState } from "react";
import type { Paradero } from "@/lib/secretaria";
import { MapaParaderos } from "./MapaParaderos";

const boton = "min-h-11 min-w-11 rounded border border-tinta/40 px-2 font-semibold hover:bg-fondo disabled:opacity-40";

/** Paraderos de la ruta en orden: lista + mapa. Tocar un paradero en el mapa lo agrega o lo quita. */
export function SelectorParaderos({
  paraderos, valor, onCambio,
}: { paraderos: Paradero[]; valor: string[]; onCambio: (ids: string[]) => void }) {
  const [filtro, setFiltro] = useState("");
  const nombre = (id: string) => paraderos.find((p) => p.id === id)?.nombre ?? "Paradero dado de baja";
  const disponibles = paraderos.filter(
    (p) => !valor.includes(p.id) && p.nombre.toLowerCase().includes(filtro.trim().toLowerCase()),
  );

  const alternar = (id: string) => onCambio(valor.includes(id) ? valor.filter((x) => x !== id) : [...valor, id]);
  const mover = (i: number, d: number) => {
    const copia = [...valor];
    const [x] = copia.splice(i, 1);
    if (x === undefined) return;
    copia.splice(i + d, 0, x);
    onCambio(copia);
  };

  return (
    <div className="grid gap-4 lg:grid-cols-2">
      <div>
        <MapaParaderos paraderos={paraderos} ordenados={valor} onElegir={alternar} alto={380} />
        <p className="mt-1 text-xs">Toca un paradero del mapa para agregarlo o quitarlo del recorrido.</p>
      </div>
      <div className="space-y-4">
        <div>
          <h3 className="font-semibold">Recorrido (en orden)</h3>
          {valor.length === 0 ? (
            <p className="mt-1 text-sm">Aún no hay paraderos. Agrega al menos 2.</p>
          ) : (
            <ol className="mt-1 space-y-1">
              {valor.map((id, i) => (
                <li key={id} className="flex items-center gap-2 rounded bg-fondo px-2 py-1">
                  <span className="w-6 text-right font-bold">{i + 1}.</span>
                  <span className="flex-1">{nombre(id)}</span>
                  <button type="button" className={boton} disabled={i === 0} onClick={() => mover(i, -1)}
                    aria-label={`Subir ${nombre(id)}`}>↑</button>
                  <button type="button" className={boton} disabled={i === valor.length - 1} onClick={() => mover(i, 1)}
                    aria-label={`Bajar ${nombre(id)}`}>↓</button>
                  <button type="button" className={boton} onClick={() => alternar(id)}
                    aria-label={`Quitar ${nombre(id)}`}>Quitar</button>
                </li>
              ))}
            </ol>
          )}
        </div>
        <div>
          <label htmlFor="filtro-paraderos" className="font-semibold">Agregar paradero</label>
          <input id="filtro-paraderos" type="search" placeholder="Buscar por nombre" value={filtro}
            onChange={(e) => setFiltro(e.target.value)}
            className="mt-1 min-h-11 w-full rounded border border-tinta/40 bg-white px-3" />
          <ul className="mt-2 max-h-44 space-y-1 overflow-y-auto">
            {disponibles.map((p) => (
              <li key={p.id}>
                <button type="button" onClick={() => onCambio([...valor, p.id])}
                  className="min-h-11 w-full rounded border border-borde bg-white px-3 text-left hover:bg-fondo">
                  + {p.nombre}
                </button>
              </li>
            ))}
            {disponibles.length === 0 ? <li className="text-sm">Sin paraderos para mostrar.</li> : null}
          </ul>
        </div>
      </div>
    </div>
  );
}
