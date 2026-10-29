"use client";
import dynamic from "next/dynamic";
import { Esqueleto } from "@/componentes/Esqueleto";

/** Mapa de busetas en vivo; Leaflet se carga sin SSR. */
export const MapaDemo = dynamic(() => import("./MapaDemoInterno"), {
  ssr: false,
  loading: () => <Esqueleto filas={6} />,
});
