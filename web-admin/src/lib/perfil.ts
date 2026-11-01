"use client";
import { useQuery } from "@tanstack/react-query";
import { api, consultar } from "./api";
import { registrarPerfil } from "./contexto-empresa";

/** Rol y empresa vienen siempre de GET /yo: el backend decide, nunca el navegador. */
export function usePerfil() {
  return useQuery({
    queryKey: ["yo"],
    queryFn: async () => {
      const perfil = await consultar(() => api.GET("/api/v1/yo"));
      registrarPerfil(perfil);
      return perfil;
    },
    retry: false,
    staleTime: 60_000,
  });
}
