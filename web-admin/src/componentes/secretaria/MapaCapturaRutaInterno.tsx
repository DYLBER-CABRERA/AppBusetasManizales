"use client";
import L from "leaflet";
import { useState } from "react";
import { CircleMarker, Marker, Polyline, Tooltip, useMapEvents } from "react-leaflet";
import MapaBaseInterno from "@/componentes/MapaBaseInterno";
import type { PuntoCapturado } from "@/lib/puntos-ruta";
import type { Paradero } from "@/lib/secretaria";

type Props = {
  puntos: PuntoCapturado[];
  /** Índices (base 0) de puntos que el backend o la validación rechazaron: se resaltan en rojo. */
  conError?: number[];
  /** Paraderos ya registrados, de contexto: un punto a ≤ 20 m de uno lo reutiliza. */
  existentes?: Paradero[];
  onPunto: (p: PuntoCapturado) => void;
  alto?: number;
};

/** Marcador numerado. Rojo ladrillo con «!» si el punto tiene error (el color no es el único canal). */
const icono = (n: number, error: boolean) =>
  L.divIcon({
    className: "",
    iconSize: [30, 30],
    iconAnchor: [15, 15],
    html: `<div style="width:30px;height:30px;border-radius:50%;display:flex;align-items:center;justify-content:center;font:700 14px sans-serif;color:#fff;border:3px solid #fff;box-shadow:0 1px 4px rgba(0,0,0,.5);background:${error ? "#a63d2f" : "#0e7c66"}">${n}${error ? "!" : ""}</div>`,
  });

function Interaccion({ onPunto, onMover }: { onPunto: Props["onPunto"]; onMover: (p: [number, number] | null) => void }) {
  useMapEvents({
    click: (e) => onPunto({ lat: e.latlng.lat, lng: e.latlng.lng }),
    mousemove: (e) => onMover([e.latlng.lat, e.latlng.lng]),
    mouseout: () => onMover(null),
  });
  return null;
}

/** Captura de puntos: cada clic agrega un punto; línea azul en vivo hasta el cursor y cierre punteado al primero. */
export default function MapaCapturaRutaInterno({ puntos, conError = [], existentes = [], onPunto, alto = 440 }: Props) {
  const [cursor, setCursor] = useState<[number, number] | null>(null);
  const trazo = puntos.map((p): [number, number] => [p.lat, p.lng]);
  const ultimo = trazo[trazo.length - 1];
  const primero = trazo[0];

  return (
    <MapaBaseInterno alto={alto}>
      <Interaccion onPunto={onPunto} onMover={setCursor} />
      {existentes.map((p) => (
        <CircleMarker key={p.id} center={[p.lat, p.lng]} radius={4} interactive={false}
          pathOptions={{ color: "#0a5e4d", weight: 1, fillColor: "#ffffff", fillOpacity: 1 }} />
      ))}
      {trazo.length >= 2 ? <Polyline positions={trazo} pathOptions={{ color: "#1d6fdc", weight: 4 }} /> : null}
      {ultimo && cursor ? (
        <Polyline positions={[ultimo, cursor]} interactive={false} pathOptions={{ color: "#1d6fdc", weight: 3, dashArray: "4 8", opacity: 0.7 }} />
      ) : null}
      {trazo.length >= 3 && ultimo && primero ? (
        <Polyline positions={[ultimo, primero]} interactive={false} pathOptions={{ color: "#1d6fdc", weight: 2, dashArray: "6 6", opacity: 0.6 }} />
      ) : null}
      {puntos.map((p, i) => (
        <Marker key={`${i}-${p.lat}-${p.lng}`} position={[p.lat, p.lng]} icon={icono(i + 1, conError.includes(i))}
          interactive={false} keyboard={false}>
          {p.nombre ? <Tooltip permanent direction="top" offset={[0, -14]}>{p.nombre}</Tooltip> : null}
        </Marker>
      ))}
    </MapaBaseInterno>
  );
}
