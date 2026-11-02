"use client";
import { useQuery } from "@tanstack/react-query";
import { api, consultar } from "./api";
import type { components } from "./tipos-api";

type Esq = components["schemas"];
export type RutaResumen = Esq["RutaResumen"];
export type RutaDetalle = Esq["RutaDetalle"];
export type RutaCrear = Esq["RutaCrear"];
export type ServicioCrearEntrada = Esq["ServicioCrearEntrada"];
export type Paradero = Esq["Paradero"];
export type Aviso = Esq["Aviso"];
export type Empresa = Esq["Empresa"];

export const CLAVE_RUTAS = ["sec", "rutas"] as const;
export const CLAVE_PARADEROS = ["sec", "paraderos"] as const;
export const CLAVE_AVISOS_MOVILIDAD = ["sec", "avisos"] as const;

export const useRutas = () =>
  useQuery({ queryKey: CLAVE_RUTAS, queryFn: () => consultar(() => api.GET("/api/v1/rutas")) });

export const useParaderos = () =>
  useQuery({ queryKey: CLAVE_PARADEROS, queryFn: () => consultar(() => api.GET("/api/v1/paraderos")) });

export const detalleRuta = (rutaId: string) =>
  consultar(() => api.GET("/api/v1/rutas/{ruta_id}", { params: { path: { ruta_id: rutaId } } }));

export const useDetalleRuta = (rutaId: string | null) =>
  useQuery({
    queryKey: ["sec", "ruta", rutaId],
    queryFn: () => detalleRuta(rutaId as string),
    enabled: rutaId !== null,
    gcTime: 0, // el formulario de edición siempre parte de la versión vigente
  });

/** `version` de un servicio (la necesita `DELETE /servicios/{id}`): sale de `GET /rutas/{id}/horarios`. */
export async function versionDeServicio(rutaId: string, servicioId: string): Promise<number | undefined> {
  const h = await consultar(() =>
    api.GET("/api/v1/rutas/{ruta_id}/horarios", { params: { path: { ruta_id: rutaId } } }),
  );
  return h.servicios.find((s) => s.servicioId === servicioId)?.version;
}

export const crearRuta = (cuerpo: RutaCrear) => consultar(() => api.POST("/api/v1/rutas", { body: cuerpo }));

export const editarRuta = (
  rutaId: string,
  cuerpo: { nombre?: string | null; descripcion?: string | null; paraderoIds?: string[] | null; version: number },
) =>
  consultar(() => api.PUT("/api/v1/rutas/{ruta_id}", { params: { path: { ruta_id: rutaId } }, body: cuerpo }));

export const eliminarRuta = (rutaId: string, version: number, confirmar: boolean) =>
  consultar(() =>
    api.DELETE("/api/v1/rutas/{ruta_id}", { params: { path: { ruta_id: rutaId }, query: { version, confirmar } } }),
  );

export const asignarServicio = (
  rutaId: string,
  cuerpo: { empresaId: string; codigoPublico?: string | null; codigoInterno?: string | null; confirmarCompartida: boolean },
) =>
  consultar(() =>
    api.POST("/api/v1/rutas/{ruta_id}/servicios", { params: { path: { ruta_id: rutaId } }, body: cuerpo }),
  );

export const retirarServicio = (servicioId: string, version: number, confirmar: boolean) =>
  consultar(() =>
    api.DELETE("/api/v1/servicios/{servicio_id}", {
      params: { path: { servicio_id: servicioId }, query: { version, confirmar } },
    }),
  );

export const crearParadero = (cuerpo: { nombre: string; lat: number; lng: number; direccion?: string | null }) =>
  consultar(() => api.POST("/api/v1/paraderos", { body: cuerpo }));

export const editarParadero = (
  paraderoId: string,
  cuerpo: { nombre?: string | null; lat?: number | null; lng?: number | null; direccion?: string | null; version: number },
) =>
  consultar(() =>
    api.PUT("/api/v1/paraderos/{paradero_id}", { params: { path: { paradero_id: paraderoId } }, body: cuerpo }),
  );

export const eliminarParadero = (paraderoId: string, version: number, confirmar: boolean) =>
  consultar(() =>
    api.DELETE("/api/v1/paraderos/{paradero_id}", {
      params: { path: { paradero_id: paraderoId }, query: { version, confirmar } },
    }),
  );

/** Avisos vigentes de origen `movilidad` (la Secretaría solo retira esos). */
export const useAvisosMovilidad = () =>
  useQuery({
    queryKey: CLAVE_AVISOS_MOVILIDAD,
    queryFn: async () => (await consultar(() => api.GET("/api/v1/avisos"))).filter((a) => a.origen === "movilidad"),
  });

export const publicarAviso = (cuerpo: Esq["AvisoCrear"]) =>
  consultar(() => api.POST("/api/v1/avisos", { body: cuerpo }));

export const retirarAviso = (avisoId: string) =>
  consultar(() => api.DELETE("/api/v1/avisos/{aviso_id}", { params: { path: { aviso_id: avisoId } } }));
