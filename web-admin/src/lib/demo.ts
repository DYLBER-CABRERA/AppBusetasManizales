"use client";
import { useQuery } from "@tanstack/react-query";
import { useEffect, useMemo, useState } from "react";
import { api, consultar } from "./api";
import { entorno } from "./entorno";
import type { components } from "./tipos-api";

export type EstadoDemo = components["schemas"]["EstadoDemo"];
export type EscenarioDemo = components["schemas"]["EscenarioDemo"];
export type BusetaEnVivo = components["schemas"]["BusetaEnVivo"];

export const CLAVE_ESTADO_DEMO = ["demo", "estado"] as const;

/**
 * `GET /demo/estado`: el Panel de demo existe solo si responde 200 (si no, 404 por MODO_DEMO=false).
 * Va con el backend real: sin datos de ejemplo.
 */
export function useEstadoDemo({ habilitado, intervaloMs }: { habilitado: boolean; intervaloMs?: number }) {
  return useQuery({
    queryKey: CLAVE_ESTADO_DEMO,
    queryFn: () => consultar(() => api.GET("/api/v1/demo/estado")),
    enabled: habilitado,
    refetchInterval: intervaloMs,
    retry: false,
  });
}

export const enviarEscenario = (cuerpo: EscenarioDemo) =>
  consultar(() => api.POST("/api/v1/demo/escenarios", { body: cuerpo }));

/** Empresas reales (id UUID) para los escenarios por empresa; sin datos de ejemplo. */
export function useEmpresasReales(habilitado: boolean) {
  return useQuery({
    queryKey: ["demo", "empresas"],
    queryFn: () => consultar(() => api.GET("/api/v1/empresas")),
    enabled: habilitado,
    staleTime: 5 * 60_000,
  });
}

export function useRutasReales(habilitado: boolean) {
  return useQuery({
    queryKey: ["demo", "rutas"],
    queryFn: () => consultar(() => api.GET("/api/v1/rutas")),
    enabled: habilitado,
    staleTime: 5 * 60_000,
  });
}

export type BusetaVivo = BusetaEnVivo & { rutaId: string };

const REFRESCO_REST_MS = 5000; // intervalo_refresco_cliente_s (5)
const SIN_WS_MS = 8000; // si el WebSocket no entrega nada en este tiempo, se consulta por REST

/**
 * Busetas en vivo de varias rutas: WebSocket `/ws/rutas/{rutaId}` con reconexión (1, 2, 4, 8 s, máx. 15 s)
 * y respaldo `GET /rutas/{id}/busetas` mientras el WebSocket no entregue datos (docs/03-contrato-api.md §4).
 */
export function useBusetasEnVivo(rutaIds: string[]) {
  const clave = rutaIds.join(",");
  const [porRuta, setPorRuta] = useState<Record<string, BusetaEnVivo[]>>({});
  const [abiertos, setAbiertos] = useState<Record<string, boolean>>({});

  useEffect(() => {
    const ids = clave ? clave.split(",") : [];
    let cerrado = false;
    const ultimo: Record<string, number> = {};
    const sockets: Record<string, WebSocket> = {};
    const temporizadores = new Set<ReturnType<typeof setTimeout>>();

    function conectar(id: string, intento: number) {
      if (cerrado) return;
      const ws = new WebSocket(`${entorno.wsUrl}/ws/rutas/${id}`);
      sockets[id] = ws;
      ws.onopen = () => setAbiertos((a) => ({ ...a, [id]: true }));
      ws.onmessage = (e) => {
        if (typeof e.data !== "string" || e.data === "pong") return;
        try {
          const m = JSON.parse(e.data) as { tipo?: string; busetas?: BusetaEnVivo[]; numeroLateral?: string };
          if (m.tipo === "posiciones" && Array.isArray(m.busetas)) {
            ultimo[id] = Date.now();
            const busetas = m.busetas;
            setPorRuta((p) => ({ ...p, [id]: busetas }));
          } else if (m.tipo === "senal_perdida" && m.numeroLateral) {
            ultimo[id] = Date.now();
            setPorRuta((p) => ({
              ...p,
              [id]: (p[id] ?? []).map((b) => (b.numeroLateral === m.numeroLateral ? { ...b, estado: "sin_senal" as const } : b)),
            }));
          }
        } catch {
          /* mensaje que no es JSON: se ignora */
        }
      };
      ws.onclose = () => {
        setAbiertos((a) => ({ ...a, [id]: false }));
        if (cerrado) return;
        const t = setTimeout(() => {
          temporizadores.delete(t);
          conectar(id, intento + 1);
        }, Math.min(15000, 1000 * 2 ** intento));
        temporizadores.add(t);
      };
    }

    async function porRest(id: string) {
      try {
        const r = await api.GET("/api/v1/rutas/{ruta_id}/busetas", { params: { path: { ruta_id: id } } });
        if (!cerrado && r.data) {
          const busetas = r.data.busetas;
          setPorRuta((p) => ({ ...p, [id]: busetas }));
        }
      } catch {
        /* sin red: se reintenta en el siguiente ciclo */
      }
    }

    ids.forEach((id) => {
      conectar(id, 0);
      void porRest(id);
    });
    const ciclo = setInterval(() => {
      ids.forEach((id) => {
        if (Date.now() - (ultimo[id] ?? 0) > SIN_WS_MS) void porRest(id);
      });
    }, REFRESCO_REST_MS);

    return () => {
      cerrado = true;
      clearInterval(ciclo);
      temporizadores.forEach(clearTimeout);
      Object.values(sockets).forEach((s) => s.close());
    };
  }, [clave]);

  const busetas = useMemo<BusetaVivo[]>(
    () => Object.entries(porRuta).flatMap(([rutaId, lista]) => lista.map((b) => ({ ...b, rutaId }))),
    [porRuta],
  );
  const conectadas = Object.values(abiertos).filter(Boolean).length;
  return { busetas, conectadas, total: rutaIds.length };
}
