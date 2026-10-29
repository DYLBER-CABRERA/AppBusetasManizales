import createClient, { type Middleware } from "openapi-fetch";
import { correoSesionEjemplo, obtenerToken } from "./auth";
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

// PENDIENTE(decisión): el contrato publicado aún no declara `empresaId` en los endpoints del jefe.
// Acordado: parámetro opcional, válido solo para el administrador (BR-07). Mientras no esté en
// contrato/openapi.json se agrega aquí como parámetro de consulta; el jefe nunca lo envía.
const ENDPOINTS_DEL_JEFE = ["/api/v1/mis-servicios", "/api/v1/busetas", "/api/v1/conductores", "/api/v1/rodamientos"];

const adjuntarEmpresa: Middleware = {
  onRequest({ request, schemaPath }) {
    const empresaId = empresaParaApi();
    if (!empresaId || !ENDPOINTS_DEL_JEFE.some((p) => schemaPath.startsWith(p))) return request;
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

/**
 * Convierte la respuesta de openapi-fetch en datos o en `ErrorApi` traducido.
 * PENDIENTE(decisión): con NEXT_PUBLIC_USAR_MOCKS=true, si el backend responde 501/red caída
 * (o 401 con sesión de ejemplo) se devuelve `ejemplo()`. Quitar al integrar con el backend real.
 */
export async function consultar<T>(llamada: () => Promise<Resultado<T>>, ejemplo?: () => T | Promise<T>): Promise<T> {
  let r: Resultado<T>;
  try {
    r = await llamada();
  } catch {
    if (ejemplo && entorno.usarMocks) return ejemplo();
    throw errorDeRed();
  }
  if (r.response.ok && r.data !== undefined) return r.data;
  if (r.response.ok) return undefined as T; // 204 sin cuerpo
  const estado = r.response.status;
  const usarEjemplo =
    ejemplo && entorno.usarMocks && (estado === 501 || (estado === 401 && correoSesionEjemplo() !== null));
  if (usarEjemplo) return ejemplo();
  throw errorDesdeRespuesta(estado, r.error);
}

export { ErrorApi };
