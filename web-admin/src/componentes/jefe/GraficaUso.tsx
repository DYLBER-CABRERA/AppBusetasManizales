"use client";
import dynamic from "next/dynamic";
import { Esqueleto } from "@/componentes/Esqueleto";

export const GraficaUso = dynamic(() => import("./GraficaUsoInterna"), {
  ssr: false,
  loading: () => <Esqueleto filas={5} />,
});
