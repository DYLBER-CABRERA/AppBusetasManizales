"use client";
import { useEffect, useState } from "react";
import { CircleMarker, Marker, Polyline, Popup, Tooltip, useMap, useMapEvents } from "react-leaflet";
import MapaBaseInterno from "@/componentes/MapaBaseInterno";
import { textoCoordenadas, type PuntoCapturado } from "@/lib/puntos-ruta";
import type { Paradero } from "@/lib/secretaria";
import { iconoNumerado } from "./iconoNumerado";

type Props = {
  puntos: PuntoCapturado[];
  /** Índices (base 0) de puntos que el backend o la validación rechazaron: se resaltan en rojo. */
  conError?: number[];
  /** Paraderos ya registrados, de contexto: un punto a ≤ 20 m de uno lo reutiliza. */
  existentes?: Paradero[];
  /** Coordenadas escritas o pegadas que aún no se agregan: se dibujan punteadas. */
  vistaPrevia?: PuntoCapturado[];
  /** Cambia cada vez que el mapa debe encuadrar estos puntos (al pegar o agregar por coordenadas). */
  enfoque?: { clave: string; puntos: [number, number][] } | null;
  onPunto: (p: PuntoCapturado) => void;
  alto?: number;
};

function Interaccion({ onPunto, onMover }: { onPunto: Props["onPunto"]; onMover: (p: [number, number] | null) => void }) {
  useMapEvents({
    click: (e) => onPunto({ lat: e.latlng.lat, lng: e.latlng.lng }),
    mousemove: (e) => onMover([e.latlng.lat, e.latlng.lng]),
    mouseout: () => onMover(null),
  });
  return null;
}

/** Encuadra los puntos solo cuando cambia `clave` (no en cada render ni al tocar el mapa). */
function Encuadrar({ enfoque }: { enfoque: NonNullable<Props["enfoque"]> }) {
  const mapa = useMap();
  const { clave, puntos } = enfoque;
  useEffect(() => {
    if (puntos.length >= 2) mapa.fitBounds(puntos, { padding: [40, 40], maxZoom: 17 });
    else if (puntos[0]) mapa.setView(puntos[0], Math.max(mapa.getZoom(), 16));
    // `puntos` se deriva de `clave`: encuadrar solo cuando esta cambia.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [mapa, clave]);
  return null;
}

/**
 * Captura de puntos: cada clic en el mapa agrega un punto; línea azul en vivo hasta el cursor y cierre punteado al primero.
 * Tocar un punto o un paradero existente muestra su latitud y longitud (no agrega un punto nuevo).
 */
export default function MapaCapturaRutaInterno({
  puntos, conError = [], existentes = [], vistaPrevia = [], enfoque, onPunto, alto = 440,
}: Props) {
  const [cursor, setCursor] = useState<[number, number] | null>(null);
  const trazo = puntos.map((p): [number, number] => [p.lat, p.lng]);
  const ultimo = trazo[trazo.length - 1];
  const primero = trazo[0];
  const previa = vistaPrevia.map((p): [number, number] => [p.lat, p.lng]);

  return (
    <MapaBaseInterno alto={alto}>
      <Interaccion onPunto={onPunto} onMover={setCursor} />
      {enfoque ? <Encuadrar enfoque={enfoque} /> : null}
      {existentes.map((p) => (
        <CircleMarker key={p.id} center={[p.lat, p.lng]} radius={6} bubblingMouseEvents={false}
          pathOptions={{ color: "#0a5e4d", weight: 1, fillColor: "#ffffff", fillOpacity: 1 }}>
          <Popup>
            <p className="font-semibold">Paradero existente: {p.nombre}</p>
            <p>Lat, lng: <span className="font-mono">{textoCoordenadas(p.lat, p.lng)}</span></p>
            <button type="button" onClick={() => onPunto({ lat: p.lat, lng: p.lng })}
              className="mt-2 min-h-11 rounded bg-verde px-3 font-semibold text-white">
              Agregar al recorrido
            </button>
          </Popup>
        </CircleMarker>
      ))}
      {trazo.length >= 2 ? <Polyline positions={trazo} interactive={false} pathOptions={{ color: "#1d6fdc", weight: 4 }} /> : null}
      {ultimo && cursor ? (
        <Polyline positions={[ultimo, cursor]} interactive={false} pathOptions={{ color: "#1d6fdc", weight: 3, dashArray: "4 8", opacity: 0.7 }} />
      ) : null}
      {trazo.length >= 3 && ultimo && primero ? (
        <Polyline positions={[ultimo, primero]} interactive={false} pathOptions={{ color: "#1d6fdc", weight: 2, dashArray: "6 6", opacity: 0.6 }} />
      ) : null}
      {previa.length > 0 ? (
        <Polyline positions={ultimo ? [ultimo, ...previa] : previa} interactive={false}
          pathOptions={{ color: "#13271e", weight: 2, dashArray: "2 6" }} />
      ) : null}
      {vistaPrevia.map((p, i) => (
        <CircleMarker key={`previa-${i}-${p.lat}-${p.lng}`} center={[p.lat, p.lng]} radius={9} interactive={false}
          pathOptions={{ color: "#13271e", weight: 2, dashArray: "3 3", fillColor: "#ffffff", fillOpacity: 0.8 }}>
          <Tooltip permanent direction="top" offset={[0, -8]}>Vista previa {puntos.length + i + 1}</Tooltip>
        </CircleMarker>
      ))}
      {puntos.map((p, i) => (
        <Marker key={`${i}-${p.lat}-${p.lng}`} position={[p.lat, p.lng]} icon={iconoNumerado(i + 1, conError.includes(i))}
          keyboard={false}>
          {p.nombre ? <Tooltip permanent direction="top" offset={[0, -14]}>{p.nombre}</Tooltip> : null}
          <Popup>
            <p className="font-semibold">Punto {i + 1}{p.nombre ? ` · ${p.nombre}` : ""}</p>
            <p>Lat, lng: <span className="font-mono">{textoCoordenadas(p.lat, p.lng)}</span></p>
          </Popup>
        </Marker>
      ))}
      <div aria-hidden="true"
        className="pointer-events-none absolute bottom-2 left-2 z-[1000] rounded bg-white/90 px-2 py-1 font-mono text-xs text-tinta shadow">
        {cursor ? `Cursor: ${textoCoordenadas(cursor[0], cursor[1])}` : "Pasa el cursor por el mapa para ver la latitud y longitud"}
      </div>
    </MapaBaseInterno>
  );
}
