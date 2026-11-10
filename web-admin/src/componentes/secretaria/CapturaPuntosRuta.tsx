"use client";
import { useMemo, useState } from "react";
import {
  leerCoordenadas, longitudCircuitoM, MAX_NOMBRE_PUNTO, MAX_PUNTOS, MIN_PUNTOS, muyPegado, textoCoordenadas,
  type ErrorPunto, type OrdenCoordenadas, type PuntoCapturado,
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

type Enfoque = { clave: string; puntos: [number, number][] };
const enfoqueDe = (ps: PuntoCapturado[]): Enfoque => ({
  clave: ps.map((p) => `${p.lat},${p.lng}`).join(";"),
  puntos: ps.map((p): [number, number] => [p.lat, p.lng]),
});

/**
 * Dos formas de armar el recorrido, combinables: tocar el mapa o pegar coordenadas (una por línea).
 * Lo pegado se ve en el mapa como vista previa mientras se escribe y entra al recorrido con «Agregar».
 * El circuito se cierra solo.
 */
export function CapturaPuntosRuta({ puntos, onCambio, errores, existentes }: Props) {
  const [aviso, setAviso] = useState<string | null>(null);
  const [texto, setTexto] = useState("");
  const [orden, setOrden] = useState<OrdenCoordenadas>("lat_lng");
  const [enfoque, setEnfoque] = useState<Enfoque | null>(null);
  const indicesError = errores.map((e) => e.indice);

  const lectura = useMemo(() => leerCoordenadas(texto, orden), [texto, orden]);
  const vistaPrevia = lectura.puntos;

  /** Al escribir o pegar, el mapa encuadra la vista previa junto al último punto agregado (para ver el tramo nuevo). */
  function cambiarTexto(nuevo: string, nuevoOrden: OrdenCoordenadas = orden) {
    setTexto(nuevo);
    setOrden(nuevoOrden);
    setAviso(null);
    const previa = leerCoordenadas(nuevo, nuevoOrden).puntos;
    if (previa.length === 0) return;
    const ultimo = puntos[puntos.length - 1];
    const e = enfoqueDe(ultimo ? [ultimo, ...previa] : previa);
    setEnfoque((actual) => (actual?.clave === e.clave ? actual : e));
  }

  function agregar(p: PuntoCapturado) {
    if (puntos.length >= MAX_PUNTOS) return setAviso(`Máximo ${MAX_PUNTOS} puntos por ruta.`);
    if (muyPegado(puntos, p)) return setAviso("Ese punto queda a menos de 10 m del anterior. Toca un poco más lejos.");
    setAviso(null);
    onCambio([...puntos, p]);
  }

  /** Agrega en orden las líneas válidas; las que no caben o quedan pegadas a la anterior se dejan en la caja. */
  function agregarPegados() {
    const nuevos: PuntoCapturado[] = [];
    const pendientes = new Set<number>(lectura.errores.map((e) => e.linea));
    const motivos: string[] = [];
    for (const { linea, ...p } of lectura.puntos) {
      const lista = [...puntos, ...nuevos];
      if (lista.length >= MAX_PUNTOS) {
        pendientes.add(linea);
        motivos.push(`Línea ${linea}: ya hay ${MAX_PUNTOS} puntos, el máximo por ruta.`);
      } else if (muyPegado(lista, p)) {
        pendientes.add(linea);
        motivos.push(`Línea ${linea}: queda a menos de 10 m del punto anterior.`);
      } else {
        nuevos.push(p);
      }
    }
    if (nuevos.length > 0) {
      onCambio([...puntos, ...nuevos]);
      setEnfoque(enfoqueDe([...puntos, ...nuevos]));
    }
    // Quedan en la caja solo las líneas que no entraron, para corregirlas.
    setTexto(texto.split(/\r?\n/).filter((_, i) => pendientes.has(i + 1)).join("\n"));
    setAviso(motivos.length > 0
      ? `Se agregaron ${nuevos.length} punto(s). No se agregaron: ${motivos.join(" ")}`
      : nuevos.length > 0 ? null : "No hay coordenadas válidas para agregar.");
  }

  const cambiarNombre = (i: number, nombre: string) =>
    onCambio(puntos.map((p, j) => (j === i ? { ...p, nombre } : p)));
  const quitar = (i: number) => { setAviso(null); onCambio(puntos.filter((_, j) => j !== i)); };
  // El contador hace que tocar dos veces el mismo punto vuelva a centrarlo.
  const enfocarPunto = (p: PuntoCapturado) =>
    setEnfoque((actual) => ({ clave: `punto:${(actual?.clave.length ?? 0) + 1}:${p.lat},${p.lng}`, puntos: [[p.lat, p.lng]] }));

  return (
    <div className="grid gap-4 lg:grid-cols-2">
      <div>
        <MapaCapturaRuta puntos={puntos} conError={indicesError} existentes={existentes} vistaPrevia={vistaPrevia}
          enfoque={enfoque} onPunto={agregar} alto={440} />
        <p className="mt-1 text-xs">
          Toca el mapa para agregar puntos en el orden del recorrido, o pega sus coordenadas al lado. El último punto se une solo
          con el primero. Toca un punto o un paradero del mapa para ver su latitud y longitud.
        </p>
      </div>
      <div className="space-y-3">
        <div className="space-y-2 rounded border border-borde p-3">
          <label htmlFor="coordenadas-pegadas" className="block font-semibold">Agregar por coordenadas</label>
          <p className="text-sm">
            Una coordenada por línea, en el orden del recorrido. Puedes copiarlas de Google Maps (clic derecho sobre el punto).
            Opcional: un nombre después, por ejemplo <span className="font-mono">5.068906, -75.517412, Catedral</span>.
          </p>
          <textarea id="coordenadas-pegadas" rows={4} value={texto} spellCheck={false}
            onChange={(e) => cambiarTexto(e.target.value)}
            onKeyDown={(e) => { if (e.key === "Enter" && (e.ctrlKey || e.metaKey)) { e.preventDefault(); agregarPegados(); } }}
            placeholder={orden === "lat_lng" ? "5.068906, -75.517412\n5.061702, -75.507910" : "-75.517412, 5.068906\n-75.507910, 5.061702"}
            aria-describedby="coordenadas-estado"
            className="w-full rounded border border-tinta/40 bg-white px-3 py-2 font-mono text-sm" />
          <div className="flex flex-wrap items-center gap-3">
            <label className="text-sm">
              Orden
              <select value={orden} onChange={(e) => cambiarTexto(texto, e.target.value as OrdenCoordenadas)}
                className="ml-2 min-h-11 rounded border border-tinta/40 bg-white px-2">
                <option value="lat_lng">Latitud, longitud (Google Maps)</option>
                <option value="lng_lat">Longitud, latitud (GeoJSON)</option>
              </select>
            </label>
            <button type="button" onClick={agregarPegados} disabled={vistaPrevia.length === 0}
              className="min-h-11 rounded bg-verde px-4 font-semibold text-white hover:bg-verde-oscuro disabled:opacity-40">
              Agregar {vistaPrevia.length > 0 ? `${vistaPrevia.length} punto(s)` : "puntos"}
            </button>
          </div>
          <p id="coordenadas-estado" role="status" className="text-sm">
            {texto.trim() === ""
              ? "Lo que pegues se verá en el mapa como vista previa (círculos punteados) antes de agregarlo."
              : `Vista previa: ${vistaPrevia.length} punto(s) válidos en el mapa. Ctrl + Enter también agrega.`}
          </p>
          {lectura.errores.length > 0 ? (
            <ul className="space-y-1 rounded bg-ladrillo-claro p-2 text-sm text-ladrillo">
              {lectura.errores.map((e) => <li key={e.linea}>{e.texto}</li>)}
            </ul>
          ) : null}
        </div>

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
          <p className="text-sm">Aún no hay puntos. Toca el mapa o pega coordenadas para empezar (mínimo {MIN_PUNTOS}).</p>
        ) : (
          <ol className="max-h-80 space-y-1 overflow-y-auto">
            {puntos.map((p, i) => (
              <li key={i} className={`flex flex-wrap items-center gap-2 rounded px-2 py-1 ${indicesError.includes(i) ? "bg-ladrillo-claro" : "bg-fondo"}`}>
                <span className="w-7 text-right font-bold">{i + 1}.</span>
                <input type="text" aria-label={`Nombre del punto ${i + 1} (opcional)`} maxLength={MAX_NOMBRE_PUNTO}
                  placeholder="Nombre (opcional)" value={p.nombre ?? ""}
                  onChange={(e) => cambiarNombre(i, e.target.value)}
                  className="min-h-11 min-w-32 flex-1 rounded border border-tinta/40 bg-white px-2" />
                <button type="button" onClick={() => enfocarPunto(p)} title="Ver en el mapa"
                  aria-label={`Ver el punto ${i + 1} en el mapa: latitud y longitud ${textoCoordenadas(p.lat, p.lng)}`}
                  className="min-h-11 rounded px-1 font-mono text-xs underline decoration-dotted hover:text-verde">
                  {textoCoordenadas(p.lat, p.lng)}
                </button>
                <button type="button" className={boton} onClick={() => quitar(i)} aria-label={`Quitar el punto ${i + 1}`}>
                  Quitar
                </button>
              </li>
            ))}
          </ol>
        )}
        <p className="text-xs">Si no escribes nombre, se genera uno automático. Un punto muy cerca de un paradero existente (20 m por omisión) lo reutiliza.</p>
      </div>
    </div>
  );
}
