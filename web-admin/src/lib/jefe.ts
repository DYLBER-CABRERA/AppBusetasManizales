"use client";
import { useQuery } from "@tanstack/react-query";
import { api, consultar } from "./api";
import { useEmpresaElegida, empresaEfectiva } from "./contexto-empresa";
import type { Rodamiento } from "./rodamiento";
import type { components } from "./tipos-api";

/**
 * Las consultas del jefe dependen de la empresa: la propia (jefe) o la que eligió el administrador.
 * Entra en la clave para que al cambiar de empresa se vuelva a pedir todo.
 */
export function useClaveEmpresa(): string {
  const elegida = useEmpresaElegida();
  return elegida?.id ?? empresaEfectiva()?.id ?? "propia";
}

export function useServicios() {
  const emp = useClaveEmpresa();
  return useQuery({
    queryKey: ["jefe", emp, "servicios"],
    queryFn: () => consultar(() => api.GET("/api/v1/mis-servicios")),
  });
}

export function useBusetas() {
  const emp = useClaveEmpresa();
  return useQuery({
    queryKey: ["jefe", emp, "busetas"],
    queryFn: () => consultar(() => api.GET("/api/v1/busetas")),
  });
}

export function useConductores() {
  const emp = useClaveEmpresa();
  return useQuery({
    queryKey: ["jefe", emp, "conductores"],
    queryFn: () => consultar(() => api.GET("/api/v1/conductores")),
  });
}

export function useEmpresasPublicas() {
  return useQuery({
    queryKey: ["empresas"],
    queryFn: () => consultar(() => api.GET("/api/v1/empresas")),
  });
}

/** Rodamiento de la fecha (uno por empresa y fecha) o `null` si aún no existe. */
export async function buscarRodamiento(fecha: string): Promise<Rodamiento | null> {
  const lista = await consultar(() =>
    api.GET("/api/v1/rodamientos", { params: { query: { desde: fecha, hasta: fecha } } }),
  );
  return lista.find((r) => r.fecha === fecha) ?? null;
}

export function useRodamiento(fecha: string) {
  const emp = useClaveEmpresa();
  return useQuery({
    queryKey: ["jefe", emp, "rodamiento", fecha],
    queryFn: () => buscarRodamiento(fecha),
  });
}

export const guardarTurnos = (
  rodamientoId: string,
  cuerpo: { turnos: components["schemas"]["TurnoEntrada"][]; version: number; confirmarReemplazo?: boolean },
) =>
  consultar(() =>
    api.PUT("/api/v1/rodamientos/{rodamiento_id}", {
      params: { path: { rodamiento_id: rodamientoId } },
      body: { ...cuerpo, confirmarReemplazo: cuerpo.confirmarReemplazo ?? false },
    }),
  );

export const crearRodamiento = (cuerpo: components["schemas"]["RodamientoCrear"]) =>
  consultar(() => api.POST("/api/v1/rodamientos", { body: cuerpo }));

export const publicarRodamiento = (rodamientoId: string, version: number) =>
  consultar(() =>
    api.POST("/api/v1/rodamientos/{rodamiento_id}/publicar", {
      params: { path: { rodamiento_id: rodamientoId } },
      body: { version },
    }),
  );
