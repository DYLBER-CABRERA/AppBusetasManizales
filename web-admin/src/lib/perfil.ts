"use client";
import { useQuery } from "@tanstack/react-query";
import { api, consultar } from "./api";
import { correoSesionEjemplo } from "./auth";
import { registrarPerfil } from "./contexto-empresa";
import { PERFILES_EJEMPLO } from "./mocks";

/** Rol y empresa vienen siempre de GET /yo: el backend decide, nunca el navegador. */
export function usePerfil() {
  return useQuery({
    queryKey: ["yo"],
    queryFn: async () => {
      const perfil = await consultar(
        () => api.GET("/api/v1/yo"),
        () => {
          const p = PERFILES_EJEMPLO[correoSesionEjemplo() ?? ""];
          if (!p) throw new Error("sin sesión de ejemplo");
          return p;
        },
      );
      registrarPerfil(perfil);
      return perfil;
    },
    retry: false,
    staleTime: 60_000,
  });
}
