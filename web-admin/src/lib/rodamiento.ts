import type { components } from "./tipos-api";
import { hora } from "./fechas";

export type Rodamiento = components["schemas"]["Rodamiento"];
export type Turno = components["schemas"]["Turno"];
export type TurnoEntrada = components["schemas"]["TurnoEntrada"];
export type ServicioRuta = components["schemas"]["ServicioRuta"];
export type Buseta = components["schemas"]["Buseta"];
export type Conductor = components["schemas"]["Conductor"];

/** Fila editable de la tabla del rodamiento (`clave` identifica la fila aunque aún no tenga id). */
export type Fila = {
  clave: string;
  id: string | null;
  servicioId: string;
  busetaId: string;
  conductorId: string;
  horaSalida: string;
  horaFin: string;
};

export const filaDesdeTurno = (t: Turno): Fila => ({
  clave: t.id ?? `${t.servicioId}-${t.horaSalida}`,
  id: t.id ?? null,
  servicioId: t.servicioId,
  busetaId: t.busetaId,
  conductorId: t.conductorId ?? "",
  horaSalida: hora(t.horaSalida),
  horaFin: hora(t.horaFinEstimada),
});

export const turnosVigentes = (r: Rodamiento): Turno[] => r.turnos.filter((t) => t.estado !== "cancelado");

export const aTurnoEntrada = (f: Pick<Fila, "servicioId" | "busetaId" | "conductorId" | "horaSalida" | "horaFin">): TurnoEntrada => ({
  servicioId: f.servicioId,
  busetaId: f.busetaId,
  conductorId: f.conductorId || null,
  horaSalida: f.horaSalida,
  horaFinEstimada: f.horaFin || null,
});

export const turnoAEntrada = (t: Turno): TurnoEntrada => aTurnoEntrada(filaDesdeTurno(t));

/** Texto del solapamiento: «Hay 1 solapamiento.» / «Hay 2 solapamientos.» */
export const textoSolapamientos = (n: number) => (n === 1 ? "Hay 1 solapamiento." : `Hay ${n} solapamientos.`);

type Nombres = { busetas: Buseta[]; conductores: Conductor[] };

/**
 * Frases de la confirmación de reemplazo (doc 01 §3.1), calculadas comparando lo guardado con lo
 * que se va a enviar (mismo `servicioId` + `horaSalida`, distinta buseta o conductor).
 */
export function frasesDeReemplazo(guardados: Turno[], nuevos: TurnoEntrada[], { busetas, conductores }: Nombres): string[] {
  const lateral = (id: string) => busetas.find((b) => b.id === id)?.numeroLateral ?? id;
  const nombre = (id: string | null | undefined) => conductores.find((c) => c.id === id)?.nombre ?? "sin conductor";
  const frases: string[] = [];
  for (const n of nuevos) {
    const g = guardados.find((t) => t.servicioId === n.servicioId && hora(t.horaSalida) === n.horaSalida);
    if (!g) continue;
    if (g.busetaId !== n.busetaId) {
      frases.push(`La ruta ya tiene asignada la buseta ${lateral(g.busetaId)} a las ${n.horaSalida}. ¿Reemplazarla por la ${lateral(n.busetaId)}?`);
    }
    if ((g.conductorId ?? null) !== (n.conductorId ?? null)) {
      frases.push(`La ruta ya tiene asignado a ${nombre(g.conductorId)} a las ${n.horaSalida}. ¿Reemplazarlo por ${nombre(n.conductorId)}?`);
    }
  }
  return frases;
}

/** Tabla del rodamiento: «El Cable (Sideral)». */
export const etiquetaServicioTabla = (s: ServicioRuta) => `${s.rutaNombre ?? "Ruta"} (${s.empresaNombre ?? ""})`;

/** Selector de asignar: «El Cable (39)»; sin código público, «La Enea (sin código)». */
export const etiquetaServicioSelector = (s: ServicioRuta) => `${s.rutaNombre ?? "Ruta"} (${s.codigoPublico ?? "sin código"})`;
