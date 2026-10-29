import { createBrowserClient } from "@supabase/ssr";
import type { SupabaseClient } from "@supabase/supabase-js";
import { entorno, supabaseConfigurado } from "./entorno";

let cliente: SupabaseClient | null = null;

/** Cliente de Supabase SOLO para Auth. Los datos van por la API del backend. */
export function supabaseNavegador(): SupabaseClient | null {
  if (!supabaseConfigurado) return null;
  cliente ??= createBrowserClient(entorno.supabaseUrl, entorno.supabaseAnonKey);
  return cliente;
}
