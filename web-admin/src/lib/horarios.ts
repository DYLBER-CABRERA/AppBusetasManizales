import { minutos } from "./fechas";
import type { components } from "./tipos-api";

export type Horario = components["schemas"]["Horario"];
export type Frecuencia = components["schemas"]["Frecuencia"];
export type TipoDia = Horario["tipoDia"];

export const TIPOS_DIA: { valor: TipoDia; etiqueta: string }[] = [
  { valor: "lun_vie", etiqueta: "Lunes a viernes" },
  { valor: "sabado", etiqueta: "Sábado" },
  { valor: "dom_festivo", etiqueta: "Domingo y festivos" },
];

const HHMM = /^([01]\d|2[0-3]):[0-5]\d$/;
const HHMM_O_24 = /^(([01]\d|2[0-3]):[0-5]\d|24:00)$/;
const aMin = (h: string) => (h === "24:00" ? 1440 : minutos(h));

// ---------- horarios ----------
export type FilaHorario = {
  tipoDia: TipoDia;
  /** Sin marcar = sin dato: la app muestra «Información pendiente de actualización». */
  activo: boolean;
  primeraSalida: string;
  ultimaSalida: string;
  cierre: string;
  nota: string;
};
export type ErroresHorario = Partial<Record<"primeraSalida" | "ultimaSalida" | "cierre", string>>;

export function filasDeHorarios(horarios: Horario[]): FilaHorario[] {
  return TIPOS_DIA.map(({ valor }) => {
    const h = horarios.find((x) => x.tipoDia === valor);
    return {
      tipoDia: valor,
      activo: h !== undefined,
      primeraSalida: h?.primeraSalida.slice(0, 5) ?? "",
      ultimaSalida: h?.ultimaSalida.slice(0, 5) ?? "",
      cierre: h?.cierre?.slice(0, 5) ?? "",
      nota: h?.nota ?? "",
    };
  });
}

export function horariosParaEnviar(filas: FilaHorario[]): Horario[] {
  return filas
    .filter((f) => f.activo)
    .map((f) => ({
      tipoDia: f.tipoDia,
      primeraSalida: f.primeraSalida,
      ultimaSalida: f.ultimaSalida,
      cierre: f.cierre || null,
      nota: f.nota.trim() || null,
    }));
}

/** Cierre ≥ última salida y primera ≤ última (docs/03 §11). Una fila sin marcar no se valida. */
export function validarHorario(f: FilaHorario): ErroresHorario {
  const e: ErroresHorario = {};
  if (!f.activo) return e;
  if (!HHMM.test(f.primeraSalida)) e.primeraSalida = "Escribe la primera salida (HH:MM).";
  if (!HHMM.test(f.ultimaSalida)) e.ultimaSalida = "Escribe la última salida (HH:MM).";
  if (!e.primeraSalida && !e.ultimaSalida && minutos(f.primeraSalida) > minutos(f.ultimaSalida)) {
    e.ultimaSalida = "La última salida no puede ser antes de la primera.";
  }
  if (f.cierre) {
    if (!HHMM.test(f.cierre)) e.cierre = "Escribe el cierre (HH:MM).";
    else if (!e.ultimaSalida && minutos(f.cierre) < minutos(f.ultimaSalida)) {
      e.cierre = "El cierre debe ser igual o posterior a la última salida.";
    }
  }
  return e;
}

// ---------- frecuencias ----------
export type FilaFranja = {
  clave: string;
  tipoDia: TipoDia;
  franjaInicio: string;
  franjaFin: string;
  minutosMin: string;
  minutosMax: string;
  nota: string;
};
export type ErroresFranja = Partial<Record<"franjaInicio" | "franjaFin" | "minutosMin" | "minutosMax", string>>;

export function filasDeFrecuencias(frecuencias: Frecuencia[]): FilaFranja[] {
  return frecuencias.map((f, i) => ({
    clave: `f${i}-${f.tipoDia}-${f.franjaInicio}`,
    tipoDia: f.tipoDia,
    franjaInicio: f.franjaInicio.slice(0, 5),
    franjaFin: f.franjaFin.slice(0, 5),
    minutosMin: String(f.minutosMin),
    minutosMax: String(f.minutosMax),
    nota: f.nota ?? "",
  }));
}

export function frecuenciasParaEnviar(filas: FilaFranja[]): Frecuencia[] {
  return filas.map((f) => ({
    tipoDia: f.tipoDia,
    franjaInicio: f.franjaInicio,
    franjaFin: f.franjaFin,
    minutosMin: Number(f.minutosMin),
    minutosMax: Number(f.minutosMax),
    nota: f.nota.trim() || null,
  }));
}

const entero = (v: string) => /^\d+$/.test(v.trim()) && Number(v) >= 1;

/** Fin > inicio, min ≤ max y franjas sin solape dentro de un mismo tipo de día. Devuelve errores por `clave`. */
export function validarFranjas(filas: FilaFranja[]): Record<string, ErroresFranja> {
  const res: Record<string, ErroresFranja> = {};
  const poner = (clave: string, campo: keyof ErroresFranja, msg: string) => {
    res[clave] = { ...res[clave], [campo]: msg };
  };

  for (const f of filas) {
    if (!HHMM.test(f.franjaInicio)) poner(f.clave, "franjaInicio", "Escribe el inicio (HH:MM).");
    if (!HHMM_O_24.test(f.franjaFin)) poner(f.clave, "franjaFin", "Escribe el fin (HH:MM; 24:00 para medianoche).");
    if (!res[f.clave]?.franjaInicio && !res[f.clave]?.franjaFin && aMin(f.franjaFin) <= aMin(f.franjaInicio)) {
      poner(f.clave, "franjaFin", "El fin debe ser posterior al inicio.");
    }
    if (!entero(f.minutosMin)) poner(f.clave, "minutosMin", "Escribe minutos enteros, mínimo 1.");
    if (!entero(f.minutosMax)) poner(f.clave, "minutosMax", "Escribe minutos enteros, mínimo 1.");
    if (!res[f.clave]?.minutosMin && !res[f.clave]?.minutosMax && Number(f.minutosMin) > Number(f.minutosMax)) {
      poner(f.clave, "minutosMax", "El máximo debe ser mayor o igual que el mínimo.");
    }
  }

  for (const { valor } of TIPOS_DIA) {
    const validas = filas
      .filter((f) => f.tipoDia === valor && !res[f.clave]?.franjaInicio && !res[f.clave]?.franjaFin)
      .sort((a, b) => aMin(a.franjaInicio) - aMin(b.franjaInicio));
    for (let i = 1; i < validas.length; i++) {
      const previa = validas[i - 1]!;
      const actual = validas[i]!;
      if (aMin(actual.franjaInicio) < aMin(previa.franjaFin)) {
        poner(actual.clave, "franjaInicio", "Esta franja se cruza con otra del mismo día.");
      }
    }
  }
  return res;
}
