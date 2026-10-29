// PENDIENTE(decisión): datos de ejemplo del doc 01 §2 y §5 mientras el backend responda 501.
// Se usan solo detrás del cliente de API (api.ts) y con NEXT_PUBLIC_USAR_MOCKS=true. Se borran al integrar.
import type { components } from "./tipos-api";

type Perfil = components["schemas"]["Perfil"];
type ServicioRuta = components["schemas"]["ServicioRuta"];
type Rodamiento = components["schemas"]["Rodamiento"];

const SIDERAL = "ejemplo-empresa-sideral";
const SOCOBUSES = "ejemplo-empresa-socobuses";

/** Cuentas de demostración (doc 01 §5). */
export const PERFILES_EJEMPLO: Record<string, Perfil> = {
  "admin@busetasapp.example": {
    usuarioId: "ejemplo-u1", correo: "admin@busetasapp.example", rol: "administrador",
    empresaId: null, empresaNombre: null,
  },
  "movilidad@alcaldia.example": {
    usuarioId: "ejemplo-u2", correo: "movilidad@alcaldia.example", rol: "secretaria_movilidad",
    empresaId: null, empresaNombre: null,
  },
  "jefe@sideral.example": {
    usuarioId: "ejemplo-u3", correo: "jefe@sideral.example", rol: "jefe_operaciones",
    empresaId: SIDERAL, empresaNombre: "Sideral",
  },
  "jefe@socobuses.example": {
    usuarioId: "ejemplo-u4", correo: "jefe@socobuses.example", rol: "jefe_operaciones",
    empresaId: SOCOBUSES, empresaNombre: "Socobuses",
  },
};

export const serviciosEjemplo = (empresaId: string | null | undefined): ServicioRuta[] =>
  empresaId === SOCOBUSES
    ? [
        { id: "ejemplo-s-enea-soco", rutaId: "ejemplo-r-enea", rutaNombre: "La Enea", empresaId: SOCOBUSES, empresaNombre: "Socobuses", codigoPublico: "18", estado: "activo", version: 1 },
        { id: "ejemplo-s-villa-soco", rutaId: "ejemplo-r-villa", rutaNombre: "Villamaría", empresaId: SOCOBUSES, empresaNombre: "Socobuses", codigoPublico: "21", estado: "activo", version: 1 },
      ]
    : [
        { id: "ejemplo-s-cable", rutaId: "ejemplo-r-cable", rutaNombre: "El Cable", empresaId: SIDERAL, empresaNombre: "Sideral", codigoPublico: "39", estado: "activo", version: 1 },
        { id: "ejemplo-s-centro", rutaId: "ejemplo-r-centro", rutaNombre: "Centro", empresaId: SIDERAL, empresaNombre: "Sideral", codigoPublico: "22", estado: "activo", version: 1 },
      ];

/** Rodamiento de mañana de Sideral en borrador, con el solapamiento deliberado del doc 01 §2.7. */
export const rodamientoEjemplo = (fecha: string): Rodamiento => ({
  rodamientoId: "ejemplo-rod-manana", fecha, estado: "borrador", version: 1,
  turnos: [
    { id: "ejemplo-t1", servicioId: "ejemplo-s-cable", busetaId: "ejemplo-b1520", numeroLateral: "1520", conductorId: "ejemplo-c1", horaSalida: "06:00", horaFinEstimada: "06:50", estado: "programado" },
    { id: "ejemplo-t2", servicioId: "ejemplo-s-centro", busetaId: "ejemplo-b1520", numeroLateral: "1520", conductorId: "ejemplo-c2", horaSalida: "06:40", horaFinEstimada: "07:30", estado: "programado" },
    { id: "ejemplo-t3", servicioId: "ejemplo-s-cable", busetaId: "ejemplo-b1544", numeroLateral: "1544", conductorId: "ejemplo-c3", horaSalida: "06:10", horaFinEstimada: "07:00", estado: "programado" },
  ],
  advertencias: [
    {
      codigo: "solapamiento_buseta",
      mensaje: "La buseta 1520 sale a las 06:40 y todavía está en el turno de las 06:00 a las 06:50.",
      turnoIds: ["ejemplo-t1", "ejemplo-t2"],
    },
  ],
});
