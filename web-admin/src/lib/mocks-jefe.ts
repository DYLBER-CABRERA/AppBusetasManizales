// PENDIENTE(decisión): servidor de ejemplo del jefe (doc 01 §2.6 y §2.7) mientras el backend responda 501.
// Replica a propósito las reglas del contrato (versión, reemplazo, solapamientos, publicar) para poder
// recorrer el flujo en la demo. Se guarda en localStorage para probar el 409 con dos pestañas.
// Se borra al integrar con el backend real.
import { empresaEfectiva } from "./contexto-empresa";
import { ErrorApi } from "./errores";
import { hoyBogota, minutos, sumarDias } from "./fechas";
import { SERVITURISMO, SIDERAL, SOCOBUSES } from "./mocks";
import type { components } from "./tipos-api";

type Buseta = components["schemas"]["Buseta"];
type Conductor = components["schemas"]["Conductor"];
type Empresa = components["schemas"]["Empresa"];
type Rodamiento = components["schemas"]["Rodamiento"];
type Turno = components["schemas"]["Turno"];
type TurnoEntrada = components["schemas"]["TurnoEntrada"];
type Advertencia = components["schemas"]["Advertencia"];

export const empresasEjemplo = (): Empresa[] => [
  { id: SIDERAL, nombre: "Sideral" },
  { id: SOCOBUSES, nombre: "Socobuses" },
  { id: SERVITURISMO, nombre: "Serviturismo" },
];

const bus = (n: string): Buseta => ({ id: `ejemplo-b${n}`, numeroLateral: n, estado: "activa", version: 1 });
const con = (id: string, nombre: string): Conductor => ({ id: `ejemplo-c-${id}`, nombre, estado: "activo", version: 1 });

export function busetasEjemplo(empresaId: string | undefined): Buseta[] {
  if (empresaId === SOCOBUSES) return [bus("3101"), bus("3102")];
  if (empresaId === SERVITURISMO) return [bus("2683"), bus("2676")];
  return [bus("1520"), bus("1544"), bus("1388")];
}

export function conductoresEjemplo(empresaId: string | undefined): Conductor[] {
  if (empresaId === SOCOBUSES) return [con("pedro", "Pedro S."), con("ana", "Ana M."), con("luz", "Luz D.")];
  if (empresaId === SERVITURISMO) return [con("hugo", "Hugo T."), con("sara", "Sara V."), con("nico", "Nicolás B.")];
  return [con("carlos", "Carlos R."), con("marta", "Marta L."), con("julian", "Julián P."), con("laura", "Laura G.")];
}

// ---------- almacén ----------
type Almacen = Record<string, Rodamiento>; // clave: `${empresaId}|${fecha}`
const LLAVE = "busetas_mock_rodamientos_v1";

function leer(): Almacen {
  try {
    return JSON.parse(localStorage.getItem(LLAVE) ?? "{}") as Almacen;
  } catch {
    return {};
  }
}
function guardar(a: Almacen) {
  try {
    localStorage.setItem(LLAVE, JSON.stringify(a));
  } catch {
    /* sin almacenamiento: el ejemplo se pierde al recargar */
  }
}

let contador = 0;
const nuevoId = () => `ejemplo-t-${Date.now().toString(36)}-${contador++}`;

function empresaActual(): string {
  return empresaEfectiva()?.id ?? SIDERAL;
}

function numero(empresaId: string, busetaId: string) {
  return busetasEjemplo(empresaId).find((b) => b.id === busetaId)?.numeroLateral;
}
function nombreConductor(empresaId: string, id: string | null | undefined) {
  return conductoresEjemplo(empresaId).find((c) => c.id === id)?.nombre;
}

function advertenciasDe(empresaId: string, turnos: Turno[]): Advertencia[] {
  const res: Advertencia[] = [];
  const vivos = turnos.filter((t) => t.estado !== "cancelado" && t.horaFinEstimada);
  for (let i = 0; i < vivos.length; i++) {
    for (let j = i + 1; j < vivos.length; j++) {
      const a = vivos[i]!;
      const b = vivos[j]!;
      if (!(minutos(b.horaSalida) < minutos(a.horaFinEstimada!) && minutos(a.horaSalida) < minutos(b.horaFinEstimada!))) continue;
      const [antes, despues] = minutos(a.horaSalida) <= minutos(b.horaSalida) ? [a, b] : [b, a];
      const tramo = `en el turno de las ${antes.horaSalida} a las ${antes.horaFinEstimada}`;
      if (a.busetaId === b.busetaId) {
        res.push({
          codigo: "solapamiento_buseta",
          mensaje: `La buseta ${numero(empresaId, a.busetaId)} sale a las ${despues.horaSalida} y todavía está ${tramo}.`,
          turnoIds: [antes.id!, despues.id!],
        });
      }
      if (a.conductorId && a.conductorId === b.conductorId) {
        res.push({
          codigo: "solapamiento_conductor",
          mensaje: `El conductor ${nombreConductor(empresaId, a.conductorId)} sale a las ${despues.horaSalida} y todavía está ${tramo}.`,
          turnoIds: [antes.id!, despues.id!],
        });
      }
    }
  }
  return res;
}

function armar(empresaId: string, fecha: string, estado: Rodamiento["estado"], version: number, turnos: Turno[], id?: string): Rodamiento {
  return { rodamientoId: id ?? `ejemplo-rod-${fecha}`, fecha, estado, version, turnos, advertencias: advertenciasDe(empresaId, turnos) };
}

function turno(s: string, b: string, c: string, salida: string, fin: string): Turno {
  return { id: nuevoId(), servicioId: s, busetaId: b, numeroLateral: b.replace("ejemplo-b", ""), conductorId: c, horaSalida: salida, horaFinEstimada: fin, estado: "programado" };
}

/** Semilla del doc 01 §2.7: hoy publicado y mañana de Sideral en borrador con un solapamiento deliberado. */
function sembrar(a: Almacen) {
  const hoy = hoyBogota();
  const manana = sumarDias(hoy, 1);
  const kHoy = `${SIDERAL}|${hoy}`;
  const kMan = `${SIDERAL}|${manana}`;
  if (!a[kHoy]) {
    a[kHoy] = armar(SIDERAL, hoy, "publicado", 1, [
      turno("ejemplo-s-cable", "ejemplo-b1520", "ejemplo-c-carlos", "05:00", "13:00"),
      turno("ejemplo-s-centro", "ejemplo-b1520", "ejemplo-c-carlos", "13:00", "22:00"),
      turno("ejemplo-s-cable", "ejemplo-b1544", "ejemplo-c-marta", "04:30", "23:30"),
      turno("ejemplo-s-centro", "ejemplo-b1388", "ejemplo-c-julian", "04:30", "23:30"),
    ]);
  }
  if (!a[kMan]) {
    a[kMan] = armar(SIDERAL, manana, "borrador", 1, [
      turno("ejemplo-s-cable", "ejemplo-b1520", "ejemplo-c-carlos", "06:00", "06:50"),
      turno("ejemplo-s-centro", "ejemplo-b1520", "ejemplo-c-marta", "06:40", "07:30"),
      turno("ejemplo-s-cable", "ejemplo-b1544", "ejemplo-c-julian", "06:10", "07:00"),
      turno("ejemplo-s-centro", "ejemplo-b1388", "ejemplo-c-laura", "06:20", "07:10"),
    ]);
  }
}

function almacen(): Almacen {
  const a = leer();
  sembrar(a);
  guardar(a);
  return a;
}

const clave = (e: string, f: string) => `${e}|${f}`;
const buscarPorId = (a: Almacen, id: string) => Object.entries(a).find(([, r]) => r.rodamientoId === id);

function validarFecha(fecha: string) {
  const hoy = hoyBogota();
  if (fecha < hoy || fecha > sumarDias(hoy, 15)) {
    throw new ErrorApi(400, "VALIDACION", "La fecha debe estar entre hoy y 15 días adelante.");
  }
}

function aplicarTurnos(empresaId: string, previos: Turno[], entrada: TurnoEntrada[]): Turno[] {
  return entrada.map((e) => {
    const igual = previos.find((p) => p.servicioId === e.servicioId && p.horaSalida === e.horaSalida);
    return {
      id: igual?.id ?? nuevoId(),
      servicioId: e.servicioId,
      busetaId: e.busetaId,
      numeroLateral: numero(empresaId, e.busetaId),
      conductorId: e.conductorId ?? null,
      horaSalida: e.horaSalida,
      horaFinEstimada: e.horaFinEstimada ?? null,
      estado: "programado" as const,
    };
  });
}

export const servidorJefe = {
  listar(fecha: string): Rodamiento[] {
    const r = almacen()[clave(empresaActual(), fecha)];
    return r ? [r] : [];
  },

  crear(body: { fecha: string; turnos: TurnoEntrada[] }): Rodamiento {
    const emp = empresaActual();
    const a = almacen();
    validarFecha(body.fecha);
    if (a[clave(emp, body.fecha)]) {
      throw new ErrorApi(409, "CONFLICTO_NEGOCIO", "Ya existe un rodamiento para esa fecha.");
    }
    const r = armar(emp, body.fecha, "borrador", 1, aplicarTurnos(emp, [], body.turnos), `ejemplo-rod-${emp}-${body.fecha}`);
    a[clave(emp, body.fecha)] = r;
    guardar(a);
    return r;
  },

  actualizar(id: string, body: { turnos: TurnoEntrada[]; version: number; confirmarReemplazo?: boolean }): Rodamiento {
    const emp = empresaActual();
    const a = almacen();
    const hallado = buscarPorId(a, id);
    if (!hallado) throw new ErrorApi(404, "NO_ENCONTRADO", "No encontramos ese rodamiento.");
    const [k, actual] = hallado;
    if (body.version !== actual.version) {
      throw new ErrorApi(409, "CONFLICTO_VERSION", "Alguien más cambió esto. Recarga para ver los cambios.");
    }
    if (actual.estado === "publicado") {
      throw new ErrorApi(409, "CONFLICTO_NEGOCIO", "El rodamiento ya está publicado.");
    }
    const cambia = body.turnos.some((e) =>
      actual.turnos.some(
        (p) =>
          p.servicioId === e.servicioId && p.horaSalida === e.horaSalida &&
          (p.busetaId !== e.busetaId || (p.conductorId ?? null) !== (e.conductorId ?? null)),
      ),
    );
    if (cambia && !body.confirmarReemplazo) {
      throw new ErrorApi(409, "CONFLICTO_NEGOCIO", "El turno ya tenía una asignación. Confirma el reemplazo.");
    }
    const nuevo = armar(emp, actual.fecha, "borrador", actual.version + 1, aplicarTurnos(emp, actual.turnos, body.turnos), id);
    a[k] = nuevo;
    guardar(a);
    return nuevo;
  },

  publicar(id: string, version: number): Rodamiento {
    const a = almacen();
    const hallado = buscarPorId(a, id);
    if (!hallado) throw new ErrorApi(404, "NO_ENCONTRADO", "No encontramos ese rodamiento.");
    const [k, actual] = hallado;
    if (version !== actual.version) {
      throw new ErrorApi(409, "CONFLICTO_VERSION", "Alguien más cambió esto. Recarga para ver los cambios.");
    }
    if (actual.advertencias.length > 0) {
      throw new ErrorApi(409, "CONFLICTO_NEGOCIO", "Corrige el solapamiento para poder publicar.");
    }
    const publicado: Rodamiento = { ...actual, estado: "publicado", version: actual.version + 1 };
    a[k] = publicado;
    guardar(a);
    return publicado;
  },
};
