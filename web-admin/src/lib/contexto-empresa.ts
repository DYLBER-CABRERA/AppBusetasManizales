import { useSyncExternalStore } from "react";
import type { Perfil } from "./auth";

// Empresa con la que opera el panel del jefe. El jefe NUNCA envía empresaId (sale del token).
// Solo el administrador (BR-07) elige una empresa y solo entonces se agrega `empresaId` a las
// peticiones del jefe. Se guarda en memoria: no sobrevive a una recarga ni a un cierre de sesión.
export type EmpresaActiva = { id: string; nombre: string };

let rol: string | null = null;
let perfilEmpresa: EmpresaActiva | null = null;
let elegida: EmpresaActiva | null = null;
const oyentes = new Set<() => void>();

function avisar() {
  oyentes.forEach((f) => f());
}

/** Se llama cada vez que GET /yo responde: el rol sale del backend, no del navegador. */
export function registrarPerfil(p: Perfil) {
  rol = p.rol;
  perfilEmpresa = p.empresaId ? { id: p.empresaId, nombre: p.empresaNombre ?? "" } : null;
  if (p.rol !== "administrador" && elegida) {
    elegida = null;
    avisar();
  }
}

export function olvidarEmpresa() {
  rol = null;
  perfilEmpresa = null;
  elegida = null;
  avisar();
}

export function fijarEmpresaElegida(e: EmpresaActiva | null) {
  if (rol !== "administrador") return;
  elegida = e;
  avisar();
}

/** Empresa con la que se trabaja: la del jefe o la que eligió el administrador. */
export function empresaEfectiva(): EmpresaActiva | null {
  return rol === "administrador" ? elegida : perfilEmpresa;
}

/** Valor para el parámetro `empresaId`: solo existe para el administrador. */
export function empresaParaApi(): string | null {
  return rol === "administrador" ? (elegida?.id ?? null) : null;
}

const suscribir = (f: () => void) => {
  oyentes.add(f);
  return () => oyentes.delete(f);
};

export function useEmpresaElegida(): EmpresaActiva | null {
  return useSyncExternalStore(suscribir, () => elegida, () => null);
}
