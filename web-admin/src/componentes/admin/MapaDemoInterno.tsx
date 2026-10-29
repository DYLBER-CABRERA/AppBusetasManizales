"use client";
import { CircleMarker, Tooltip } from "react-leaflet";
import MapaBaseInterno from "@/componentes/MapaBaseInterno";
import type { BusetaVivo } from "@/lib/demo";

/** Amarillo = buseta en vivo. Sin señal: círculo vacío con borde rojo ladrillo y la palabra en la etiqueta. */
export default function MapaDemoInterno({ busetas }: { busetas: BusetaVivo[] }) {
  return (
    <MapaBaseInterno alto={380}>
      {busetas.map((b) => {
        const sinSenal = b.estado === "sin_senal";
        return (
          <CircleMarker
            key={b.busetaId}
            center={[b.lat, b.lng]}
            radius={10}
            pathOptions={
              sinSenal
                ? { color: "#a8392b", weight: 3, fillColor: "#ffffff", fillOpacity: 0.5, dashArray: "4 3" }
                : { color: "#13271e", weight: 2, fillColor: "#f6c500", fillOpacity: 1 }
            }
          >
            <Tooltip permanent direction="top" offset={[0, -8]}>
              {b.numeroLateral}
              {sinSenal ? " · sin señal" : ""}
            </Tooltip>
          </CircleMarker>
        );
      })}
    </MapaBaseInterno>
  );
}
