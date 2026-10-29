export type Seccion = { href: string; etiqueta: string };
export type Grupo = { clave: "jefe" | "secretaria" | "admin"; titulo: string; secciones: Seccion[] };

export const GRUPOS: Grupo[] = [
  {
    clave: "jefe",
    titulo: "Jefe de operaciones",
    secciones: [
      { href: "/jefe/rodamiento", etiqueta: "Rodamiento" },
      { href: "/jefe/asignar", etiqueta: "Asignar" },
      { href: "/jefe/horarios", etiqueta: "Horarios" },
      { href: "/jefe/avisos", etiqueta: "Avisos" },
      { href: "/jefe/excel", etiqueta: "Excel" },
      { href: "/jefe/uso", etiqueta: "Uso" },
    ],
  },
  {
    clave: "secretaria",
    titulo: "Secretaría de Movilidad",
    secciones: [
      { href: "/secretaria/rutas", etiqueta: "Rutas" },
      { href: "/secretaria/paraderos", etiqueta: "Paraderos" },
      { href: "/secretaria/movilidad", etiqueta: "Cambios de movilidad" },
    ],
  },
  {
    clave: "admin",
    titulo: "Administrador",
    secciones: [
      { href: "/admin/usuarios", etiqueta: "Usuarios" },
      { href: "/admin/empresas", etiqueta: "Empresas" },
      { href: "/admin/parametros", etiqueta: "Parámetros" },
      { href: "/admin/fuentes-gps", etiqueta: "Fuentes GPS" },
      { href: "/admin/avisos", etiqueta: "Avisos" },
      { href: "/admin/demo", etiqueta: "Panel de demo" },
    ],
  },
];

/** Grupos visibles según el rol; el administrador ve todos (BR-07). */
export function gruposDeRol(rol: string): Grupo[] {
  if (rol === "administrador") return [...GRUPOS].reverse();
  if (rol === "jefe_operaciones") return GRUPOS.filter((g) => g.clave === "jefe");
  if (rol === "secretaria_movilidad") return GRUPOS.filter((g) => g.clave === "secretaria");
  return [];
}

export const ETIQUETA_ROL: Record<string, string> = {
  jefe_operaciones: "Jefe de operaciones",
  secretaria_movilidad: "Secretaría de Movilidad",
  administrador: "Administrador",
  pasajero: "Pasajero",
};
