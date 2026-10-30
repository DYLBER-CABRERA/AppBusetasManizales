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

export const anularRodamiento = (rodamientoId: string, version: number) =>
  consultar(() =>
    api.POST("/api/v1/rodamientos/{rodamiento_id}/anular", {
      params: { path: { rodamiento_id: rodamientoId } },
      body: { version },
    }),
  );

export const publicarRodamiento = (rodamientoId: string, version: number) =>
  consultar(() =>
    api.POST("/api/v1/rodamientos/{rodamiento_id}/publicar", {
      params: { path: { rodamiento_id: rodamientoId } },
      body: { version },
    }),
  );

// ---------- horarios y frecuencias (W4) ----------
type Esq = components["schemas"];
export type HorariosDeServicio = Esq["HorariosDeServicio"];
export type FrecuenciasDeServicio = Esq["FrecuenciasDeServicio"];

export function useHorariosDeServicio(rutaId: string | undefined, servicioId: string | undefined) {
  const emp = useClaveEmpresa();
  return useQuery({
    queryKey: ["jefe", emp, "horarios", servicioId],
    enabled: Boolean(rutaId && servicioId),
    gcTime: 0, // el editor siempre parte de lo vigente
    queryFn: async () => {
      const r = await consultar(() =>
        api.GET("/api/v1/rutas/{ruta_id}/horarios", { params: { path: { ruta_id: rutaId as string } } }),
      );
      return r.servicios.find((s) => s.servicioId === servicioId) ?? null;
    },
  });
}

export function useFrecuenciasDeServicio(rutaId: string | undefined, servicioId: string | undefined) {
  const emp = useClaveEmpresa();
  return useQuery({
    queryKey: ["jefe", emp, "frecuencias", servicioId],
    enabled: Boolean(rutaId && servicioId),
    gcTime: 0,
    queryFn: async () => {
      const r = await consultar(() =>
        api.GET("/api/v1/rutas/{ruta_id}/frecuencias", { params: { path: { ruta_id: rutaId as string } } }),
      );
      return r.servicios.find((s) => s.servicioId === servicioId) ?? null;
    },
  });
}

export const guardarHorarios = (servicioId: string, cuerpo: Esq["HorariosActualizar"]) =>
  consultar(() =>
    api.PUT("/api/v1/servicios/{servicio_id}/horarios", { params: { path: { servicio_id: servicioId } }, body: cuerpo }),
  );

export const guardarFrecuencias = (servicioId: string, cuerpo: Esq["FrecuenciasActualizar"]) =>
  consultar(() =>
    api.PUT("/api/v1/servicios/{servicio_id}/frecuencias", { params: { path: { servicio_id: servicioId } }, body: cuerpo }),
  );

export const crearBuseta = (cuerpo: Esq["BusetaCrear"]) => consultar(() => api.POST("/api/v1/busetas", { body: cuerpo }));
export const crearConductor = (cuerpo: Esq["ConductorCrear"]) =>
  consultar(() => api.POST("/api/v1/conductores", { body: cuerpo }));

export const editarBuseta = (id: string, cuerpo: Esq["BusetaEditar"]) =>
  consultar(() => api.PUT("/api/v1/busetas/{buseta_id}", { params: { path: { buseta_id: id } }, body: cuerpo }));
export const editarConductor = (id: string, cuerpo: Esq["ConductorEditar"]) =>
  consultar(() => api.PUT("/api/v1/conductores/{conductor_id}", { params: { path: { conductor_id: id } }, body: cuerpo }));

// ---------- estadísticas de uso (W4) ----------
export function useEstadisticasUso(desde: string, hasta: string) {
  const emp = useClaveEmpresa();
  return useQuery({
    queryKey: ["jefe", emp, "uso", desde, hasta],
    queryFn: () =>
      consultar(() =>
        api.GET("/api/v1/estadisticas/uso", {
          // El jefe lo ignora (usa su token); el administrador indica la empresa elegida.
          params: { query: { desde, hasta, empresaId: empresaEfectiva()?.id ?? null } },
        }),
      ),
  });
}
