import { obtenerToken } from "./auth";
import { entorno } from "./entorno";
import { ErrorApi, errorDeRed, errorDesdeRespuesta } from "./errores";
import type { components } from "./tipos-api";

type Esq = components["schemas"];
export type VistaPrevia = Esq["VistaPreviaImportacion"];
export type ResultadoImportacion = Esq["ResultadoImportacion"];
export type RutaImportada = Esq["RutaImportada"];
export type ErrorImportacion = Esq["ErrorImportacion"];

/** Límites del contrato §25, para mostrarlos en pantalla y revisar el archivo antes de subirlo. */
export const LIMITES_IMPORTACION = { kb: 200, filas: 400, rutas: 10, puntos: 30 } as const;
export const MAX_BYTES_IMPORTACION = LIMITES_IMPORTACION.kb * 1024;
export const COLUMNAS_IMPORTACION = ["ruta", "orden", "latitud", "longitud", "nombre_punto", "empresa", "codigo_publico"] as const;

const origen = entorno.apiUrl.replace(/\/api\/v1\/?$/, "");
const BASE = "/api/v1/rutas/importacion";

export const MENSAJE_XLSX =
  "Ese archivo parece de Excel (.xlsx). Ábrelo en Excel o Google Sheets y guárdalo como «CSV (delimitado por comas)» antes de subirlo.";

/** Extensiones de hojas de cálculo que no son CSV; el .csv es lo único que se acepta. */
const NO_CSV = /\.(xlsx|xlsm|xlsb|xls|ods|numbers)$/i;

/** Revisión previa en el navegador; devuelve el mensaje a mostrar o `null` si el archivo puede subirse. */
export async function problemaConArchivo(archivo: File): Promise<string | null> {
  if (NO_CSV.test(archivo.name) || /spreadsheet|ms-excel/i.test(archivo.type)) return MENSAJE_XLSX;
  // Un .xlsx renombrado a .csv sigue siendo un ZIP («PK»): el backend lo rechaza, aquí se explica antes.
  try {
    const cabecera = new Uint8Array(await archivo.slice(0, 2).arrayBuffer());
    if (cabecera[0] === 0x50 && cabecera[1] === 0x4b) return MENSAJE_XLSX;
  } catch {
    return "No se pudo leer el archivo. Vuelve a elegirlo.";
  }
  if (!/\.(csv|txt)$/i.test(archivo.name)) return "Sube un archivo con extensión .csv.";
  if (archivo.size === 0) return "El archivo está vacío.";
  if (archivo.size > MAX_BYTES_IMPORTACION) {
    return `El archivo pesa ${(archivo.size / 1024).toFixed(0)} KB y el máximo es ${LIMITES_IMPORTACION.kb} KB.`;
  }
  return null;
}

/** Textos de los motivos 400 del archivo completo (contrato §25); si llega otro, se usa el mensaje del servidor. */
const MOTIVOS_ARCHIVO: Record<string, string> = {
  archivo_vacio: "El archivo está vacío.",
  sin_datos: "El archivo solo tiene el encabezado: no hay filas de datos.",
  archivo_muy_grande: `El archivo supera el máximo de ${LIMITES_IMPORTACION.kb} KB.`,
  formato_no_soportado: MENSAJE_XLSX,
  codificacion: "No se pudo leer el texto del archivo. Guárdalo como CSV (UTF-8 o «CSV delimitado por comas» de Excel).",
  csv_invalido: "El archivo no es un CSV válido.",
  columna_obligatoria: "Falta una columna obligatoria.",
  demasiadas_filas: `El archivo tiene más de ${LIMITES_IMPORTACION.filas} filas de datos.`,
  demasiadas_rutas: `El archivo tiene más de ${LIMITES_IMPORTACION.rutas} rutas.`,
};

export type ProblemaArchivo = { motivo: string; texto: string };

/** Lee `detalles: [{fila, columna, motivo}]` de un 400 VALIDACION del archivo completo. */
export function problemasDeArchivo(e: unknown): ProblemaArchivo[] {
  if (!(e instanceof ErrorApi) || e.codigo !== "VALIDACION" || !Array.isArray(e.detalles)) return [];
  return (e.detalles as Record<string, unknown>[]).map((d) => {
    const motivo = String(d.motivo ?? "");
    const base = MOTIVOS_ARCHIVO[motivo] ?? e.message;
    const columna = typeof d.columna === "string" && d.columna ? ` Columna «${d.columna}».` : "";
    const fila = typeof d.fila === "number" ? ` Fila ${d.fila}.` : "";
    return { motivo, texto: `${base}${motivo === "columna_obligatoria" ? columna : fila}`.trim() };
  });
}

async function llamar(ruta: string, init: RequestInit): Promise<Response> {
  const token = await obtenerToken();
  const cabeceras = new Headers(init.headers);
  if (token) cabeceras.set("Authorization", `Bearer ${token}`);
  let r: Response;
  try {
    r = await fetch(`${origen}${BASE}${ruta}`, { ...init, headers: cabeceras });
  } catch {
    throw errorDeRed();
  }
  if (r.ok) return r;
  throw errorDesdeRespuesta(r.status, await r.json().catch(() => undefined));
}

/**
 * El CSV viaja como cuerpo crudo (`text/csv`, no multipart). Se envían los bytes tal cual, sin decodificar:
 * el backend detecta UTF-8 o Windows-1252, y leerlo como texto aquí dañaría las tildes de un CSV de Excel.
 */
async function enviarArchivo<T>(ruta: string, archivo: File): Promise<T> {
  let cuerpo: ArrayBuffer;
  try {
    cuerpo = await archivo.arrayBuffer();
  } catch {
    throw new ErrorApi(400, "VALIDACION", "No se pudo leer el archivo (¿cambió o se movió?). Vuelve a elegirlo.");
  }
  const r = await llamar(ruta, { method: "POST", headers: { "Content-Type": "text/csv" }, body: cuerpo });
  return (await r.json()) as T;
}

/** No guarda nada ni llama a OSRM: solo valida. */
export const vistaPreviaImportacion = (archivo: File) => enviarArchivo<VistaPrevia>("/vista-previa", archivo);

/** Crea las rutas válidas, con trazado por calles (puede tardar hasta ~60 s). 201 o 200 traen el mismo cuerpo. */
export const confirmarImportacion = (archivo: File) => enviarArchivo<ResultadoImportacion>("/confirmar", archivo);

/** Descarga la plantilla (`GET …/plantilla`) con la sesión del usuario, no con un enlace directo. */
export async function descargarPlantilla(): Promise<void> {
  const r = await llamar("/plantilla", { method: "GET" });
  const url = URL.createObjectURL(await r.blob());
  const enlace = document.createElement("a");
  enlace.href = url;
  enlace.download = "plantilla_importacion_rutas.csv";
  document.body.appendChild(enlace);
  enlace.click();
  enlace.remove();
  URL.revokeObjectURL(url);
}

export const ESTADO_RUTA: Record<RutaImportada["estado"], { etiqueta: string; clase: string }> = {
  valida: { etiqueta: "✓ Válida", clase: "bg-fondo text-verde-oscuro" },
  con_errores: { etiqueta: "✕ Con errores", clase: "bg-ladrillo-claro text-ladrillo" },
  duplicada: { etiqueta: "≡ Duplicada", clase: "bg-fondo text-tinta" },
};

/** Texto de un error de ruta o de fila: «Fila 5 · latitud: mensaje». */
export const textoErrorImportacion = (e: ErrorImportacion): string =>
  `${e.fila != null ? `Fila ${e.fila}` : "Toda la ruta"}${e.columna ? ` · ${e.columna}` : ""}: ${e.mensaje}`;
