"use client";
import { useQuery } from "@tanstack/react-query";
import { api, consultar } from "./api";

export const CLAVE_AVISOS = ["avisos", "vigentes"] as const;

/** Avisos vigentes de todos los orígenes (empresa, movilidad, aplicativo). */
export const useAvisosVigentes = () =>
  useQuery({ queryKey: CLAVE_AVISOS, queryFn: () => consultar(() => api.GET("/api/v1/avisos")) });
