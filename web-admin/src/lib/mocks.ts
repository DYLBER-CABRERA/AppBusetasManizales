// PENDIENTE(decisión): datos de ejemplo del doc 01 §2 y §5 mientras el backend responda 501.
// Se usan solo detrás del cliente de API (api.ts) y con NEXT_PUBLIC_USAR_MOCKS=true. Se borran al integrar.
import type { components } from "./tipos-api";

type Perfil = components["schemas"]["Perfil"];
type ServicioRuta = components["schemas"]["ServicioRuta"];

export const SIDERAL = "ejemplo-empresa-sideral";
export const SOCOBUSES = "ejemplo-empresa-socobuses";
export const SERVITURISMO = "ejemplo-empresa-serviturismo";

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
  empresaId === SERVITURISMO
    ? [
        { id: "ejemplo-s-enea-servi", rutaId: "ejemplo-r-enea", rutaNombre: "La Enea", empresaId: SERVITURISMO, empresaNombre: "Serviturismo", estado: "activo", version: 1 },
        { id: "ejemplo-s-villa-servi", rutaId: "ejemplo-r-villa", rutaNombre: "Villamaría", empresaId: SERVITURISMO, empresaNombre: "Serviturismo", estado: "activo", version: 1 },
      ]
    : empresaId === SOCOBUSES
    ? [
        { id: "ejemplo-s-enea-soco", rutaId: "ejemplo-r-enea", rutaNombre: "La Enea", empresaId: SOCOBUSES, empresaNombre: "Socobuses", codigoPublico: "18", estado: "activo", version: 1 },
        { id: "ejemplo-s-villa-soco", rutaId: "ejemplo-r-villa", rutaNombre: "Villamaría", empresaId: SOCOBUSES, empresaNombre: "Socobuses", codigoPublico: "21", estado: "activo", version: 1 },
      ]
    : [
        { id: "ejemplo-s-cable", rutaId: "ejemplo-r-cable", rutaNombre: "El Cable", empresaId: SIDERAL, empresaNombre: "Sideral", codigoPublico: "39", estado: "activo", version: 1 },
        { id: "ejemplo-s-centro", rutaId: "ejemplo-r-centro", rutaNombre: "Centro", empresaId: SIDERAL, empresaNombre: "Sideral", codigoPublico: "22", estado: "activo", version: 1 },
      ];

