export type CajaCiudad = { minLat: number; maxLat: number; minLng: number; maxLng: number };
export const CLAVES_CAJA = ["minLat", "maxLat", "minLng", "maxLng"] as const;
export type ClaveCaja = (typeof CLAVES_CAJA)[number];

const numeroValido = (v: string) => (v.trim() === "" ? NaN : Number(v.replace(",", ".")));

/** Valida los cuatro bordes de la caja de la ciudad; devuelve errores por campo o la caja lista para enviar. */
export function validarCaja(texto: Record<ClaveCaja, string>): { errores: Partial<Record<ClaveCaja, string>>; caja?: CajaCiudad } {
  const n = Object.fromEntries(CLAVES_CAJA.map((k) => [k, numeroValido(texto[k])])) as Record<ClaveCaja, number>;
  const errores: Partial<Record<ClaveCaja, string>> = {};
  for (const k of CLAVES_CAJA) {
    const lat = k.endsWith("Lat");
    const limite = lat ? 90 : 180;
    if (!Number.isFinite(n[k])) errores[k] = "Escribe un número.";
    else if (Math.abs(n[k]) > limite) errores[k] = `Debe estar entre -${limite} y ${limite}.`;
  }
  if (!errores.minLat && !errores.maxLat && n.minLat >= n.maxLat) errores.maxLat = "La latitud máxima debe ser mayor que la mínima.";
  if (!errores.minLng && !errores.maxLng && n.minLng >= n.maxLng) errores.maxLng = "La longitud máxima debe ser mayor que la mínima.";
  return Object.keys(errores).length ? { errores } : { errores, caja: n };
}

export function cajaDesdeValor(valor: unknown): Record<ClaveCaja, string> {
  const o = (typeof valor === "object" && valor ? valor : {}) as Record<string, unknown>;
  return Object.fromEntries(CLAVES_CAJA.map((k) => [k, o[k] == null ? "" : String(o[k])])) as Record<ClaveCaja, string>;
}
