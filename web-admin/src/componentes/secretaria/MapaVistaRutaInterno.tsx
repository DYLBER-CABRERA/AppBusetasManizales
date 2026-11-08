"use client";
import { useEffect } from "react";
import { Marker, Polyline, Tooltip, useMap } from "react-leaflet";
import MapaBaseInterno from "@/componentes/MapaBaseInterno";
import type { RutaDetalle } from "@/lib/secretaria";
import { iconoNumerado } from "./iconoNumerado";

/** Encuadra el mapa en el trazado completo de la ruta. */
function Encuadrar({ puntos }: { puntos: [number, number][] }) {
  const mapa = useMap();
  useEffect(() => {
    if (puntos.length >= 2) mapa.fitBounds(puntos, { padding: [30, 30] });
    else if (puntos[0]) mapa.setView(puntos[0], 16);
  }, [mapa, puntos]);
  return null;
}

/** Solo lectura: el trazado real (`trazado` del contrato, [lng, lat]) y los paraderos numerados en su orden. */
export default function MapaVistaRutaInterno({ ruta, alto = 460 }: { ruta: RutaDetalle; alto?: number }) {
  const linea = ruta.trazado.coordinates.map(([lng, lat]): [number, number] => [lat as number, lng as number]);
  const paradas = [...ruta.paraderos].sort((a, b) => a.orden - b.orden);
  const encuadre = linea.length >= 2 ? linea : paradas.map((p): [number, number] => [p.lat, p.lng]);

  return (
    <MapaBaseInterno alto={alto}>
      <Encuadrar puntos={encuadre} />
      {linea.length >= 2 ? <Polyline positions={linea} interactive={false} pathOptions={{ color: "#1d6fdc", weight: 4 }} /> : null}
      {paradas.map((p) => (
        <Marker key={p.paraderoId} position={[p.lat, p.lng]} icon={iconoNumerado(p.orden)} keyboard={false}>
          <Tooltip direction="top" offset={[0, -14]}>{p.orden} · {p.nombre}</Tooltip>
        </Marker>
      ))}
    </MapaBaseInterno>
  );
}
