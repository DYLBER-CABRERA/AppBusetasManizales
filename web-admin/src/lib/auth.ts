import { olvidarEmpresa } from "./contexto-empresa";
import { entorno } from "./entorno";
import { supabaseNavegador } from "./supabase";
import type { components } from "./tipos-api";

export type Perfil = components["schemas"]["Perfil"];
export type Rol = "pasajero" | "jefe_operaciones" | "secretaria_movilidad" | "administrador";

export const COOKIE_MOCK = "busetas_sesion_ejemplo";

/** Carpeta inicial de cada rol. */
export const RUTA_INICIAL: Record<Rol, string> = {
  jefe_operaciones: "/jefe/rodamiento",
  secretaria_movilidad: "/secretaria/rutas",
  administrador: "/admin/usuarios",
  pasajero: "/login",
};

/** Secciones a las que entra cada rol; el administrador es superconjunto (BR-07). */
export function puedeEntrar(rol: string, ruta: string): boolean {
  if (rol === "administrador") return /^\/(admin|secretaria|jefe)(\/|$)/.test(ruta);
  if (rol === "jefe_operaciones") return /^\/jefe(\/|$)/.test(ruta);
  if (rol === "secretaria_movilidad") return /^\/secretaria(\/|$)/.test(ruta);
  return false;
}

export function rutaInicial(rol: string): string {
  return RUTA_INICIAL[rol as Rol] ?? "/login";
}

// ---- sesión de ejemplo (PENDIENTE: se elimina cuando el backend responda /yo y haya Supabase) ----
export function correoSesionEjemplo(): string | null {
  if (typeof document === "undefined") return null;
  const m = document.cookie.match(new RegExp(`(?:^|; )${COOKIE_MOCK}=([^;]*)`));
  return m?.[1] ? decodeURIComponent(m[1]) : null;
}

export function hayCredencialesSupabase(): boolean {
  return supabaseNavegador() !== null;
}

export async function obtenerToken(): Promise<string | null> {
  const sb = supabaseNavegador();
  if (!sb) return null;
  const { data } = await sb.auth.getSession();
  return data.session?.access_token ?? null;
}

export async function iniciarSesion(correo: string, contrasena: string): Promise<void> {
  const sb = supabaseNavegador();
  if (sb) {
    const { error } = await sb.auth.signInWithPassword({ email: correo, password: contrasena });
    if (error) throw new Error("Correo o contraseña incorrectos.");
    return;
  }
  if (!entorno.usarMocks) {
    throw new Error("Falta configurar Supabase (NEXT_PUBLIC_SUPABASE_URL y NEXT_PUBLIC_SUPABASE_ANON_KEY).");
  }
  document.cookie = `${COOKIE_MOCK}=${encodeURIComponent(correo)}; path=/; SameSite=Lax`;
}

export async function cerrarSesion(): Promise<void> {
  olvidarEmpresa();
  await supabaseNavegador()?.auth.signOut();
  document.cookie = `${COOKIE_MOCK}=; path=/; max-age=0`;
}
