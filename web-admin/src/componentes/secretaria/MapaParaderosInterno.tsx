"use client";
import { CircleMarker, Polyline, Tooltip, useMapEvents } from "react-leaflet";
import MapaBaseInterno from "@/componentes/MapaBaseInterno";
import type { Paradero } from "@/lib/secretaria";

export type PuntoMapa = { lat: number; lng: number };

type Props = {
  paraderos: Paradero[];
  /** Ids de paraderos de la ruta, en orden de recorrido. */
  ordenados?: string[];
  /** Tocar un paradero existente. */
  onElegir?: (id: string) => void;
  /** Punto nuevo o en edición (se fija tocando el mapa). */
  punto?: PuntoMapa | null;
  onPunto?: (p: PuntoMapa) => void;
  alto?: number;
};

function ClicMapa({ onPunto }: { onPunto: (p: PuntoMapa) => void }) {
  useMapEvents({ click: (e) => onPunto({ lat: e.latlng.lat, lng: e.latlng.lng }) });
  return null;
}

/** Verde = paradero; los de la ruta llevan su número de orden. Tinta = punto que se está fijando. */
export default function MapaParaderosInterno({ paraderos, ordenados = [], onElegir, punto, onPunto, alto = 420 }: Props) {
  const posicion = new Map(ordenados.map((id, i) => [id, i + 1]));
  const lineas = ordenados
    .map((id) => paraderos.find((p) => p.id === id))
    .filter((p): p is Paradero => Boolean(p))
    .map((p): [number, number] => [p.lat, p.lng]);
  if (lineas.length >= 3 && lineas[0]) lineas.push(lineas[0]); // circuito (D-P02)

  return (
    <MapaBaseInterno alto={alto}>
      {onPunto ? <ClicMapa onPunto={onPunto} /> : null}
      {lineas.length >= 2 ? <Polyline positions={lineas} pathOptions={{ color: "#0e7c66", weight: 3, dashArray: "6 6" }} /> : null}
      {paraderos.map((p) => {
        const n = posicion.get(p.id);
        return (
          <CircleMarker
            key={p.id}
            center={[p.lat, p.lng]}
            radius={n ? 10 : 6}
            bubblingMouseEvents={false}
            eventHandlers={onElegir ? { click: () => onElegir(p.id) } : undefined}
            pathOptions={{ color: "#0a5e4d", weight: 2, fillColor: n ? "#0e7c66" : "#ffffff", fillOpacity: 1 }}
          >
            <Tooltip permanent={Boolean(n)} direction="top" offset={[0, -6]}>
              {n ? `${n} · ${p.nombre}` : p.nombre}
            </Tooltip>
          </CircleMarker>
        );
      })}
      {punto ? (
        <CircleMarker center={[punto.lat, punto.lng]} radius={11} pathOptions={{ color: "#ffffff", weight: 3, fillColor: "#13271e", fillOpacity: 1 }}>
          <Tooltip permanent direction="top" offset={[0, -8]}>Ubicación elegida</Tooltip>
        </CircleMarker>
      ) : null}
    </MapaBaseInterno>
  );
}
