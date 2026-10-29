const ZONA = "America/Bogota";

// PENDIENTE(decisión): el jefe no puede leer GET /admin/parametros; se usa el valor por defecto
// de `dias_max_rodamiento_adelante` (docs/03-contrato-api.md §6). El backend valida de todos modos.
export const DIAS_MAX_RODAMIENTO_ADELANTE = 15;

/** Fecha de hoy en Bogotá, `YYYY-MM-DD`. */
export function hoyBogota(): string {
  return new Intl.DateTimeFormat("en-CA", { timeZone: ZONA }).format(new Date());
}

export function sumarDias(fecha: string, dias: number): string {
  const d = new Date(`${fecha}T12:00:00Z`);
  d.setUTCDate(d.getUTCDate() + dias);
  return d.toISOString().slice(0, 10);
}

export function diaSemana(fecha: string): string {
  return new Intl.DateTimeFormat("es-CO", { weekday: "long", timeZone: "UTC" }).format(
    new Date(`${fecha}T12:00:00Z`),
  );
}

export function fechaLarga(fecha: string): string {
  return new Intl.DateTimeFormat("es-CO", { day: "numeric", month: "long", timeZone: "UTC" }).format(
    new Date(`${fecha}T12:00:00Z`),
  );
}

/** El backend puede devolver `06:00:00`; la interfaz siempre muestra `HH:MM`. */
export function hora(valor: string | null | undefined): string {
  return valor ? valor.slice(0, 5) : "";
}

export function minutos(hhmm: string): number {
  const [h, m] = hhmm.split(":");
  return Number(h) * 60 + Number(m);
}

/** «hace 4 s», «hace 3 min», «hace 2 h», «hace 1 d». */
export function haceTexto(iso: string, ahora: number): string {
  const s = Math.max(0, Math.round((ahora - new Date(iso).getTime()) / 1000));
  if (s < 60) return `hace ${s} s`;
  if (s < 3600) return `hace ${Math.floor(s / 60)} min`;
  if (s < 86400) return `hace ${Math.floor(s / 3600)} h`;
  return `hace ${Math.floor(s / 86400)} d`;
}

/** Hora local de Bogotá `HH:MM` de un instante ISO. */
export function horaBogota(iso: string): string {
  return new Intl.DateTimeFormat("es-CO", { timeZone: ZONA, hour: "2-digit", minute: "2-digit", hour12: false }).format(new Date(iso));
}
