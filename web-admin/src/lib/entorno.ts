// Variables públicas. Solo claves anónimas: la service_role jamás llega a esta app.
export const entorno = {
  supabaseUrl: process.env.NEXT_PUBLIC_SUPABASE_URL ?? "",
  supabaseAnonKey: process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY ?? "",
  apiUrl: process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000/api/v1",
  wsUrl: process.env.NEXT_PUBLIC_WS_URL ?? "ws://localhost:8000",
  tileUrl:
    process.env.NEXT_PUBLIC_MAP_TILE_URL ?? "https://tile.openstreetmap.org/{z}/{x}/{y}.png",
};

export const supabaseConfigurado = Boolean(entorno.supabaseUrl && entorno.supabaseAnonKey);
