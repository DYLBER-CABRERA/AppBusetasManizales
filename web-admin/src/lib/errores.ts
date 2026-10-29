import type { components } from "./tipos-api";

export type DetalleError = components["schemas"]["DetalleError"];

/** Error del contrato (CLAUDE.md §6) ya traducido, listo para mostrarse. */
export class ErrorApi extends Error {
  constructor(
    public readonly estado: number,
    public readonly codigo: string,
    mensaje: string,
    public readonly reintentable = false,
    public readonly detalles: unknown = null,
  ) {
    super(mensaje);
    this.name = "ErrorApi";
  }

  get esConflictoVersion() {
    return this.codigo === "CONFLICTO_VERSION";
  }
  get esConflictoNegocio() {
    return this.codigo === "CONFLICTO_NEGOCIO";
  }
  get esSinPermiso() {
    return this.estado === 403 || this.codigo === "NO_AUTORIZADO";
  }
}

export const MENSAJE_SIN_CONEXION =
  "No se pudo conectar con el servidor. Mostramos lo último que cargó. Revisa tu conexión.";
export const MENSAJE_SIN_PERMISO = "No tienes permiso para esta sección";

export function errorDesdeRespuesta(estado: number, cuerpo: unknown): ErrorApi {
  const e = (cuerpo as { error?: Partial<DetalleError> } | undefined)?.error;
  if (e?.codigo) {
    const mensaje = estado === 403 ? MENSAJE_SIN_PERMISO : (e.mensaje ?? "Ocurrió un error.");
    return new ErrorApi(estado, e.codigo, mensaje, e.reintentable ?? false, e.detalles ?? null);
  }
  if (estado === 401) return new ErrorApi(401, "NO_AUTENTICADO", "Tu sesión venció. Inicia sesión de nuevo.");
  if (estado === 403) return new ErrorApi(403, "NO_AUTORIZADO", MENSAJE_SIN_PERMISO);
  return new ErrorApi(estado, "ERROR_INTERNO", "Ocurrió un error inesperado.", estado >= 500);
}

export function errorDeRed(): ErrorApi {
  return new ErrorApi(503, "SERVICIO_EXTERNO_NO_DISPONIBLE", MENSAJE_SIN_CONEXION, true);
}

/** Lista dentro de `detalles` de un 409 (p. ej. `turnosFuturos`, `rutas`): contrato §13 y §16. */
export function listaDeDetalles(e: unknown, clave: string): Record<string, unknown>[] {
  if (!(e instanceof ErrorApi)) return [];
  const d = e.detalles as Record<string, unknown> | null;
  const lista = d?.[clave];
  return Array.isArray(lista) ? (lista as Record<string, unknown>[]) : [];
}
