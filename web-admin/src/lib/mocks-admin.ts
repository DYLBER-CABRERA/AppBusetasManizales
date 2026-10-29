// PENDIENTE(decisión): datos de ejemplo de /admin/* mientras el backend responda 501 (hasta B5).
// Los mínimos y máximos son de EJEMPLO (solo «50 a 2000» de la distancia de aviso sale de la documentación);
// los reales los define el backend. Se guarda en localStorage. Se borra al integrar.
// La clave de una fuente GPS NUNCA se guarda: solo se devuelve al crearla (en BD real solo queda el hash).
import { ErrorApi } from "./errores";
import { SERVITURISMO, SIDERAL, SOCOBUSES } from "./mocks";
import type { components } from "./tipos-api";

type Parametro = components["schemas"]["Parametro"];
type EmpresaAdmin = components["schemas"]["EmpresaAdmin"];
type CredencialGps = components["schemas"]["CredencialGps"];
type CredencialGpsCreada = components["schemas"]["CredencialGpsCreada"];

const p = (clave: string, valor: number, descripcion: string, minimo: number, maximo: number): Parametro => ({
  clave, valor, descripcion, minimo, maximo, version: 1,
});

const PARAMETROS_INICIALES: Parametro[] = [
  p("distancia_aviso_llegada_m", 300, "Distancia de aviso de llegada (m)", 50, 2000),
  p("umbral_posicion_obsoleta_s", 60, "Segundos sin señal para marcar la buseta como sin señal", 10, 600),
  p("longitud_max_aviso", 500, "Máximo de caracteres de un aviso", 50, 1000),
  p("intervalo_refresco_cliente_s", 5, "Intervalo de refresco de las apps (s)", 1, 60),
  p("umbral_desvio_m", 100, "Distancia para considerar un desvío (m)", 20, 1000),
  p("enfriamiento_alerta_min", 10, "Minutos entre alertas repetidas", 1, 120),
  p("radio_busqueda_m", 800, "Radio de búsqueda de rutas cercanas (m)", 100, 5000),
  p("radio_caminata_m", 500, "Radio de caminata para planificar (m)", 100, 2000),
  p("radio_hito_m", 300, "Radio de cobertura de un hito (m)", 50, 2000),
  p("velocidad_default_kmh", 20, "Velocidad por defecto del ETA (km/h)", 5, 60),
  p("max_opciones_viaje", 3, "Opciones máximas al planificar un viaje", 1, 10),
  p("dias_max_rodamiento_adelante", 15, "Días máximos hacia adelante para el rodamiento", 1, 60),
  p("rango_max_estadisticas_dias", 365, "Rango máximo de las estadísticas (días)", 1, 730),
];

const LLAVE_PARAMETROS = "busetas_mock_parametros_v1";
const LLAVE_CREDENCIALES = "busetas_mock_credenciales_v1";

function leer<T>(llave: string, vacio: T): T {
  try {
    const s = localStorage.getItem(llave);
    return s ? (JSON.parse(s) as T) : vacio;
  } catch {
    return vacio;
  }
}
function guardar(llave: string, valor: unknown) {
  try {
    localStorage.setItem(llave, JSON.stringify(valor));
  } catch {
    /* sin almacenamiento */
  }
}

export const empresasAdminEjemplo = (): EmpresaAdmin[] => [
  { id: SIDERAL, nombre: "Sideral", estado: "activo", version: 1 },
  { id: SOCOBUSES, nombre: "Socobuses", estado: "activo", version: 1 },
  { id: SERVITURISMO, nombre: "Serviturismo", estado: "activo", version: 1 },
];

export const servidorAdmin = {
  parametros(): Parametro[] {
    return leer<Parametro[]>(LLAVE_PARAMETROS, PARAMETROS_INICIALES);
  },

  actualizarParametro(clave: string, body: { valor: unknown; version: number }): Parametro {
    const lista = this.parametros();
    const i = lista.findIndex((x) => x.clave === clave);
    const actual = lista[i];
    if (!actual) throw new ErrorApi(404, "NO_ENCONTRADO", "No encontramos ese parámetro.");
    if (body.version !== actual.version) {
      throw new ErrorApi(409, "CONFLICTO_VERSION", "Alguien más cambió esto. Recarga para ver los cambios.");
    }
    const v = Number(body.valor);
    if (!Number.isFinite(v) || (actual.minimo != null && v < actual.minimo) || (actual.maximo != null && v > actual.maximo)) {
      throw new ErrorApi(400, "VALIDACION", `Escribe un valor entre ${actual.minimo} y ${actual.maximo}.`);
    }
    const nuevo = { ...actual, valor: v, version: actual.version + 1 };
    lista[i] = nuevo;
    guardar(LLAVE_PARAMETROS, lista);
    return nuevo;
  },

  credenciales(empresaId: string): CredencialGps[] {
    const todas = leer<Record<string, CredencialGps[]>>(LLAVE_CREDENCIALES, {});
    const base: CredencialGps[] =
      empresaId === SERVITURISMO
        ? []
        : [{ id: `ejemplo-cred-${empresaId}`, nombre: "GPS de la flota", activa: true, creadaEn: "2026-10-01T08:00:00-05:00", ultimoUso: null }];
    const lista = todas[empresaId] ?? base;
    // La fuente simulada de las empresas con GPS "envía" ahora mismo: hace 4 s.
    return lista.map((c) => (c.id.startsWith("ejemplo-cred-") && c.activa ? { ...c, ultimoUso: new Date(Date.now() - 4000).toISOString() } : c));
  },

  crearCredencial(empresaId: string, nombre: string): CredencialGpsCreada {
    const todas = leer<Record<string, CredencialGps[]>>(LLAVE_CREDENCIALES, {});
    const lista = this.credenciales(empresaId).map((c) => ({ ...c, ultimoUso: c.id.startsWith("ejemplo-cred-") ? null : c.ultimoUso }));
    const nueva: CredencialGps = {
      id: `cred-${Date.now().toString(36)}`,
      nombre, activa: true, creadaEn: new Date().toISOString(), ultimoUso: null,
    };
    todas[empresaId] = [...lista, nueva];
    guardar(LLAVE_CREDENCIALES, todas);
    const aleatorio = Array.from(crypto.getRandomValues(new Uint8Array(18)), (b) => b.toString(16).padStart(2, "0")).join("");
    return { ...nueva, clave: `ejemplo_${aleatorio}` };
  },

  revocarCredencial(credencialId: string): void {
    const todas = leer<Record<string, CredencialGps[]>>(LLAVE_CREDENCIALES, {});
    for (const e of [SIDERAL, SOCOBUSES, SERVITURISMO]) {
      const lista = todas[e] ?? this.credenciales(e).map((c) => ({ ...c, ultimoUso: null }));
      if (lista.some((c) => c.id === credencialId)) {
        todas[e] = lista.map((c) => (c.id === credencialId ? { ...c, activa: false } : c));
        guardar(LLAVE_CREDENCIALES, todas);
        return;
      }
    }
    throw new ErrorApi(404, "NO_ENCONTRADO", "No encontramos esa fuente.");
  },
};
