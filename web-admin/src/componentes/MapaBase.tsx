"use client";
import dynamic from "next/dynamic";
import { Esqueleto } from "./Esqueleto";

/** Leaflet se importa sin SSR. Los hijos son capas de react-leaflet. */
export const MapaBase = dynamic(() => import("./MapaBaseInterno"), {
  ssr: false,
  loading: () => <Esqueleto filas={6} />,
});
