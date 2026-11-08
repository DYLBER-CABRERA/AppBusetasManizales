"use client";
import dynamic from "next/dynamic";
import { Esqueleto } from "@/componentes/Esqueleto";

/** Mapa de solo lectura con el trazado de una ruta; Leaflet se carga sin SSR. */
export const MapaVistaRuta = dynamic(() => import("./MapaVistaRutaInterno"), {
  ssr: false,
  loading: () => <Esqueleto filas={6} />,
});
