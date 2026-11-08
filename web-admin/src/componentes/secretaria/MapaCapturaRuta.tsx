"use client";
import dynamic from "next/dynamic";
import { Esqueleto } from "@/componentes/Esqueleto";

/** Mapa para armar una ruta tocando puntos; Leaflet se carga sin SSR. */
export const MapaCapturaRuta = dynamic(() => import("./MapaCapturaRutaInterno"), {
  ssr: false,
  loading: () => <Esqueleto filas={6} />,
});
