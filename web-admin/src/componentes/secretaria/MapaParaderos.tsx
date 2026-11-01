"use client";
import dynamic from "next/dynamic";
import { Esqueleto } from "@/componentes/Esqueleto";

/** Mapa de paraderos (selección, punto nuevo, trazado en orden); Leaflet se carga sin SSR. */
export const MapaParaderos = dynamic(() => import("./MapaParaderosInterno"), {
  ssr: false,
  loading: () => <Esqueleto filas={6} />,
});
