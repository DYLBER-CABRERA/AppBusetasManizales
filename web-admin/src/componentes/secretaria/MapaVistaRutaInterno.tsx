"use client";
import type L from "leaflet";
import { useEffect, useRef, type RefObject } from "react";
import { Marker, Polyline, Popup, Tooltip, useMap } from "react-leaflet";
import MapaBaseInterno from "@/componentes/MapaBaseInterno";
import { textoCoordenadas } from "@/lib/puntos-ruta";
import type { RutaDetalle } from "@/lib/secretaria";
import { iconoNumerado } from "./iconoNumerado";

/** Encuadra el mapa en el trazado completo de la ruta, solo cuando cambia la ruta o su versión (no en cada render). */
function Encuadrar({ puntos, clave }: { puntos: [number, number][]; clave: string }) {
  const mapa = useMap();
  useEffect(() => {
    if (puntos.length >= 2) mapa.fitBounds(puntos, { padding: [30, 30] });
    else if (puntos[0]) mapa.setView(puntos[0], 16);
    // `puntos` se deriva de la ruta identificada por `clave`.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [mapa, clave]);
  return null;
}

type Marcadores = RefObject<Map<string, L.Marker>>;

/** Centra el mapa en el paradero elegido desde la lista y abre su globo con las coordenadas. */
function AbrirSeleccionado({ id, clave, marcadores }: { id: string; clave: number; marcadores: Marcadores }) {
  const mapa = useMap();
  useEffect(() => {
    const m = marcadores.current.get(id);
    if (!m) return;
    mapa.setView(m.getLatLng(), Math.max(mapa.getZoom(), 16));
    m.openPopup();
  }, [mapa, id, clave, marcadores]);
  return null;
}

type Props = {
  ruta: RutaDetalle;
  alto?: number;
  /** Paradero elegido en la lista; `clave` cambia en cada clic para reabrirlo aunque sea el mismo. */
  seleccionado?: { id: string; clave: number } | null;
};

/**
 * Solo lectura: el trazado real (`trazado` del contrato, [lng, lat]) y los paraderos numerados en su orden.
 * Tocar un paradero muestra su latitud y longitud.
 */
export default function MapaVistaRutaInterno({ ruta, alto = 460, seleccionado }: Props) {
  const marcadores = useRef(new Map<string, L.Marker>());
  const linea = ruta.trazado.coordinates.map(([lng, lat]): [number, number] => [lat as number, lng as number]);
  const paradas = [...ruta.paraderos].sort((a, b) => a.orden - b.orden);
  const encuadre = linea.length >= 2 ? linea : paradas.map((p): [number, number] => [p.lat, p.lng]);

  return (
    <MapaBaseInterno alto={alto}>
      <Encuadrar puntos={encuadre} clave={`${ruta.id}:${ruta.version}`} />
      {linea.length >= 2 ? <Polyline positions={linea} interactive={false} pathOptions={{ color: "#1d6fdc", weight: 4 }} /> : null}
      {paradas.map((p) => (
        <Marker key={p.paraderoId} position={[p.lat, p.lng]} icon={iconoNumerado(p.orden)} keyboard={false}
          ref={(m) => { if (m) marcadores.current.set(p.paraderoId, m); else marcadores.current.delete(p.paraderoId); }}>
          <Tooltip direction="top" offset={[0, -14]}>{p.orden} · {p.nombre}</Tooltip>
          <Popup>
            <p className="font-semibold">{p.orden} · {p.nombre}</p>
            <p>Lat, lng: <span className="font-mono">{textoCoordenadas(p.lat, p.lng)}</span></p>
          </Popup>
        </Marker>
      ))}
      {seleccionado ? <AbrirSeleccionado id={seleccionado.id} clave={seleccionado.clave} marcadores={marcadores} /> : null}
    </MapaBaseInterno>
  );
}
