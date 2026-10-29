"use client";
import { useQuery } from "@tanstack/react-query";
import { api, consultar } from "./api";
import type { components } from "./tipos-api";

export type Parametro = components["schemas"]["Parametro"];
export type EmpresaAdmin = components["schemas"]["EmpresaAdmin"];
export type CredencialGps = components["schemas"]["CredencialGps"];

export const CLAVE_PARAMETROS = ["admin", "parametros"] as const;

export function useParametros() {
  return useQuery({
    queryKey: CLAVE_PARAMETROS,
    queryFn: () => consultar(() => api.GET("/api/v1/admin/parametros")),
  });
}

export const actualizarParametro = (clave: string, cuerpo: { valor: unknown; version: number }) =>
  consultar(() => api.PUT("/api/v1/admin/parametros/{clave}", { params: { path: { clave } }, body: cuerpo }));

export function useEmpresasAdmin() {
  return useQuery({
    queryKey: ["admin", "empresas"],
    queryFn: () => consultar(() => api.GET("/api/v1/admin/empresas")),
  });
}

export const claveCredenciales = (empresaId: string) => ["admin", "credenciales", empresaId] as const;

export function useCredenciales(empresaId: string) {
  return useQuery({
    queryKey: claveCredenciales(empresaId),
    queryFn: () =>
      consultar(() =>
        api.GET("/api/v1/admin/empresas/{empresa_id}/credenciales-gps", { params: { path: { empresa_id: empresaId } } }),
      ),
    refetchInterval: 10_000,
  });
}

export const crearCredencial = (empresaId: string, nombre: string) =>
  consultar(() =>
    api.POST("/api/v1/admin/empresas/{empresa_id}/credenciales-gps", {
      params: { path: { empresa_id: empresaId } },
      body: { nombre },
    }),
  );

export const revocarCredencial = (credencialId: string) =>
  consultar(() =>
    api.DELETE("/api/v1/admin/credenciales-gps/{credencial_id}", { params: { path: { credencial_id: credencialId } } }),
  );
