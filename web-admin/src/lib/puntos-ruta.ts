import type { components } from "./tipos-api";

/** Punto tocado en el mapa; `nombre` es opcional (si falta, el backend genera «Paradero <Ruta> N»). */
export type PuntoCapturado = { lat: number; lng: number; nombre?: string };
export type PuntoRuta = components["schemas"]["PuntoRuta"];

// Límites del contrato §23/§24 (30 porque cada punto es una consulta a OSRM; antes 60).
export const MIN_PUNTOS = 2;
export const MAX_PUNTOS = 30;
export const MAX_NOMBRE_PUNTO = 120;
export const DISTANCIA_MIN_M = 10;

const RADIO_TIERRA_M = 6_371_000;

export function distanciaM(a: PuntoCapturado, b: PuntoCapturado): number {
  const rad = (g: number) => (g * Math.PI) / 180;
  const dLat = rad(b.lat - a.lat);
  const dLng = rad(b.lng - a.lng);
  const h = Math.sin(dLat / 2) ** 2 + Math.cos(rad(a.lat)) * Math.cos(rad(b.lat)) * Math.sin(dLng / 2) ** 2;
  return 2 * RADIO_TIERRA_M * Math.asin(Math.sqrt(h));
}

/** El clic cae a menos de 10 m del punto anterior: el backend lo rechazaría como `duplicado_consecutivo`. */
export const muyPegado = (puntos: PuntoCapturado[], nuevo: PuntoCapturado): boolean => {
  const ultimo = puntos[puntos.length - 1];
  return ultimo !== undefined && distanciaM(ultimo, nuevo) < DISTANCIA_MIN_M;
};

/** Longitud del circuito (incluye el tramo que cierra al primer punto), en línea recta. */
export function longitudCircuitoM(puntos: PuntoCapturado[]): number {
  if (puntos.length < 2) return 0;
  let total = 0;
  for (let i = 1; i < puntos.length; i++) total += distanciaM(puntos[i - 1]!, puntos[i]!);
  return total + distanciaM(puntos[puntos.length - 1]!, puntos[0]!);
}

/** Motivos de `error.detalles[].motivo` (contrato §23) y su texto para la Secretaría. */
const MOTIVOS: Record<string, string> = {
  fuera_de_zona: "está fuera de la zona de la ciudad",
  coordenadas_invalidas: "tiene coordenadas inválidas",
  duplicado_consecutivo: "está a menos de 10 m del punto anterior",
  ultimo_igual_al_primero: "está a menos de 10 m del primero; el circuito se cierra solo, quita este punto",
  nombre_invalido: "tiene un nombre inválido (máximo 120 caracteres)",
};

export type ErrorPunto = { indice: number; motivo: string; texto: string };

/** Lee `detalles: [{campo:"puntos[1]", motivo}]` de un 400 VALIDACION; ignora lo que no sea de un punto. */
export function erroresPorPunto(detalles: unknown): ErrorPunto[] {
  if (!Array.isArray(detalles)) return [];
  const salida: ErrorPunto[] = [];
  for (const d of detalles as Record<string, unknown>[]) {
    const m = /^puntos\[(\d+)\]$/.exec(String(d?.campo ?? ""));
    if (!m) continue;
    const indice = Number(m[1]);
    const motivo = String(d.motivo ?? "");
    salida.push({ indice, motivo, texto: `El punto ${indice + 1} ${MOTIVOS[motivo] ?? "no es válido"}.` });
  }
  return salida;
}

/** Validación previa al envío: avisa lo mismo que rechazaría el backend, sin ir a la red. */
export function validarPuntos(puntos: PuntoCapturado[]): ErrorPunto[] {
  const errores: ErrorPunto[] = [];
  if (puntos.length >= 3 && distanciaM(puntos[0]!, puntos[puntos.length - 1]!) < DISTANCIA_MIN_M) {
    errores.push({
      indice: puntos.length - 1, motivo: "ultimo_igual_al_primero",
      texto: `El punto ${puntos.length} ${MOTIVOS.ultimo_igual_al_primero}.`,
    });
  }
  puntos.forEach((p, i) => {
    if (i > 0 && distanciaM(puntos[i - 1]!, p) < DISTANCIA_MIN_M) {
      errores.push({ indice: i, motivo: "duplicado_consecutivo", texto: `El punto ${i + 1} ${MOTIVOS.duplicado_consecutivo}.` });
    }
    if ((p.nombre?.trim().length ?? 0) > MAX_NOMBRE_PUNTO) {
      errores.push({ indice: i, motivo: "nombre_invalido", texto: `El punto ${i + 1} ${MOTIVOS.nombre_invalido}.` });
    }
  });
  return errores;
}

/** Arma los puntos del cuerpo: en el orden tocado, con `nombre` solo si la Secretaría escribió uno. */
export function puntosParaEnvio(puntos: PuntoCapturado[]): PuntoRuta[] {
  return puntos.map((p) => {
    const nombre = p.nombre?.trim();
    return nombre ? { lat: p.lat, lng: p.lng, nombre } : { lat: p.lat, lng: p.lng };
  });
}
