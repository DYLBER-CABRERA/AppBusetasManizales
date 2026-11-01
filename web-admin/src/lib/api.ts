import createClient, { type Middleware } from "openapi-fetch";
import { obtenerToken } from "./auth";
import { empresaParaApi } from "./contexto-empresa";
import { entorno } from "./entorno";
import { ErrorApi, errorDeRed, errorDesdeRespuesta } from "./errores";
import type { paths } from "./tipos-api";

// Las rutas del contrato ya traen el prefijo /api/v1; baseUrl apunta solo al origen.
const origen = entorno.apiUrl.replace(/\/api\/v1\/?$/, "");

const adjuntarJwt: Middleware = {
  async onRequest({ request }) {
    const token = await obtenerToken();
    if (token) request.headers.set("Authorization", `Bearer ${token}`);
    return request;
  },
};

// Contrato §12: la operación del jefe y la edición de horarios/frecuencias aceptan `empresaId` opcional.
// El jefe lo ignora (usa su token); el administrador debe indicarlo y actúa como jefe de esa empresa.
// Aquí se agrega a esas rutas solo cuando el administrador eligió una empresa (contexto-empresa.ts).
const OPERACION_DEL_JEFE = [
  /^\/api\/v1\/mis-servicios/,
  /^\/api\/v1\/busetas/,
  /^\/api\/v1\/conductores/,
  /^\/api\/v1\/rodamientos/,
  /^\/api\/v1\/servicios\/\{servicio_id\}\/(horarios|frecuencias)$/,
];

const adjuntarEmpresa: Middleware = {
  onRequest({ request, schemaPath }) {
    const empresaId = empresaParaApi();
    if (!empresaId || !OPERACION_DEL_JEFE.some((r) => r.test(schemaPath))) return request;
    const url = new URL(request.url);
    url.searchParams.set("empresaId", empresaId);
    return new Request(url, request);
  },
};

/** Cliente tipado desde contrato/openapi.json. Nunca registra tokens ni cabeceras. */
export const api = createClient<paths>({ baseUrl: origen });
api.use(adjuntarJwt);
api.use(adjuntarEmpresa);

type Resultado<T> = { data?: T; error?: unknown; response: Response };

/** Convierte la respuesta de openapi-fetch en datos o en `ErrorApi` traducido (CLAUDE.md §6). */
export async function consultar<T>(llamada: () => Promise<Resultado<T>>): Promise<T> {
  let r: Resultado<T>;
  try {
    r = await llamada();
  } catch {
    throw errorDeRed();
  }
  if (r.response.ok && r.data !== undefined) return r.data;
  if (r.response.ok) return undefined as T; // 204 sin cuerpo
  throw errorDesdeRespuesta(r.response.status, r.error);
}

export { ErrorApi };
