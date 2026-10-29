"use client";
import "leaflet/dist/leaflet.css";
import type { ReactNode } from "react";
import { MapContainer, TileLayer } from "react-leaflet";
import { entorno } from "@/lib/entorno";

const MANIZALES: [number, number] = [5.0689, -75.5174];

export default function MapaBaseInterno({ children, alto = 360 }: { children?: ReactNode; alto?: number }) {
  return (
    <MapContainer center={MANIZALES} zoom={14} style={{ height: alto }} className="rounded-lg border border-borde">
      <TileLayer url={entorno.tileUrl} attribution="&copy; colaboradores de OpenStreetMap" />
      {children}
    </MapContainer>
  );
}
