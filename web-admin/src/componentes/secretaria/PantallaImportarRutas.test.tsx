import { readFileSync } from "node:fs";
import path from "node:path";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { ProveedorToast } from "@/componentes/Toast";
import type { ResultadoImportacion, RutaImportada, VistaPrevia } from "@/lib/importacion-rutas";
import { PantallaImportarRutas } from "./PantallaImportarRutas";

// jsdom no trae Blob.arrayBuffer (los navegadores sí): se completa solo para las pruebas.
if (!Blob.prototype.arrayBuffer) {
  Blob.prototype.arrayBuffer = function (this: Blob) {
    return new Promise<ArrayBuffer>((resolver, rechazar) => {
      const lector = new FileReader();
      lector.onload = () => resolver(lector.result as ArrayBuffer);
      lector.onerror = () => rechazar(lector.error);
      lector.readAsArrayBuffer(this);
    });
  };
}

vi.mock("@/lib/auth", () => ({ obtenerToken: async () => "token-de-prueba" }));

// Los dos CSV de ejemplo del backend (contrato §25). Las respuestas son las del contrato: aquí se prueba el cliente.
const EJEMPLOS = path.resolve(__dirname, "../../../../backend/supabase/semillas/ejemplos");
const csv = (nombre: string) => {
  const bytes = readFileSync(path.join(EJEMPLOS, nombre));
  return new File([new Uint8Array(bytes)], nombre, { type: "text/csv" });
};

const valida: RutaImportada = {
  nombre: "Ejemplo Fátima a Chipre (datos de ejemplo)", estado: "valida", puntos: 4, empresa: "Sideral", codigoPublico: "77",
  paraderosNuevos: 4, paraderosReutilizados: 0, errores: [],
  avisos: ["El trazado por calles se calcula al confirmar; si un tramo no tiene ruta real quedará en línea recta."],
};
const fueraDeZona: RutaImportada = {
  nombre: "Ejemplo con punto fuera de zona (datos de ejemplo)", estado: "con_errores", puntos: 2, empresa: "Sideral",
  codigoPublico: null, paraderosNuevos: null, paraderosReutilizados: null, avisos: [],
  errores: [{ fila: 5, columna: "latitud", motivo: "fuera_de_zona", mensaje: "El punto está fuera de la zona de Manizales y Villamaría." }],
};
const empresaInventada: RutaImportada = {
  nombre: "Ejemplo con empresa desconocida (datos de ejemplo)", estado: "con_errores", puntos: 2, empresa: "Empresa Inventada",
  codigoPublico: null, paraderosNuevos: null, paraderosReutilizados: null, avisos: [],
  errores: [{ fila: null, columna: "empresa", motivo: "empresa_desconocida", mensaje: "La empresa «Empresa Inventada» no existe." }],
};
const previa = (rutas: RutaImportada[]): VistaPrevia => ({
  totalFilas: 7, seCrearian: rutas.filter((r) => r.estado === "valida").length,
  resumen: {
    validas: rutas.filter((r) => r.estado === "valida").length,
    conErrores: rutas.filter((r) => r.estado === "con_errores").length,
    duplicadas: rutas.filter((r) => r.estado === "duplicada").length,
  },
  columnasIgnoradas: [], erroresGenerales: [], rutas,
});

const respuesta = (estado: number, cuerpo: unknown) =>
  new Response(JSON.stringify(cuerpo), { status: estado, headers: { "Content-Type": "application/json" } });

function montar() {
  const cliente = new QueryClient({ defaultOptions: { queries: { retry: false }, mutations: { retry: false } } });
  render(
    <QueryClientProvider client={cliente}>
      <ProveedorToast><PantallaImportarRutas /></ProveedorToast>
    </QueryClientProvider>,
  );
  // El diálogo del navegador filtra por `accept`, pero se puede elegir «todos los archivos»: se prueba ese caso.
  return userEvent.setup({ applyAccept: false });
}
const subir = (u: ReturnType<typeof userEvent.setup>, f: File) =>
  u.upload(screen.getByLabelText("Archivo CSV"), f);

let fetchMock: ReturnType<typeof vi.fn>;
beforeEach(() => {
  fetchMock = vi.fn();
  vi.stubGlobal("fetch", fetchMock);
});
afterEach(() => vi.unstubAllGlobals());

describe("Importar rutas desde archivo", () => {
  it("sin archivo muestra el estado vacío, los límites y la plantilla", () => {
    montar();
    expect(screen.getByText("Aún no elegiste un archivo")).toBeTruthy();
    expect(screen.getByText(/200 KB · 400 filas · 10 rutas por archivo · 30 puntos por ruta/)).toBeTruthy();
    expect(screen.getByRole("button", { name: "Descargar plantilla" })).toBeTruthy();
  });

  it("un .xlsx se rechaza con la instrucción de guardarlo como CSV y no llama al servidor", async () => {
    const u = montar();
    await u.upload(
      screen.getByLabelText("Archivo CSV"),
      new File([new Uint8Array([0x50, 0x4b, 3, 4])], "rutas.xlsx"),
    );
    expect((await screen.findByRole("alert")).textContent).toContain("CSV (delimitado por comas)");
    expect(fetchMock).not.toHaveBeenCalled();
  });

  it("CSV válido: envía los bytes crudos como text/csv y habilita «Crear 1 ruta»", async () => {
    fetchMock.mockResolvedValueOnce(respuesta(200, previa([valida])));
    const u = montar();
    const f = csv("importacion_rutas_ejemplo.csv");
    await subir(u, f);

    expect(await screen.findByText(valida.nombre)).toBeTruthy();
    const [url, init] = fetchMock.mock.calls[0] as [string, RequestInit];
    expect(url).toMatch(/\/api\/v1\/rutas\/importacion\/vista-previa$/);
    expect(init.method).toBe("POST");
    expect(new Headers(init.headers).get("Content-Type")).toBe("text/csv");
    expect(new Headers(init.headers).get("Authorization")).toBe("Bearer token-de-prueba");
    expect(init.body).toBeInstanceOf(ArrayBuffer);
    expect((init.body as ArrayBuffer).byteLength).toBe(f.size);
    expect((screen.getByRole("button", { name: "Crear 1 ruta" }) as HTMLButtonElement).disabled).toBe(false);
  });

  it("CSV con errores: muestra resumen, fila y columna de cada error, y deja crear solo la válida", async () => {
    fetchMock.mockResolvedValueOnce(respuesta(200, previa([valida, fueraDeZona, empresaInventada])));
    const u = montar();
    await subir(u, csv("importacion_rutas_con_errores_ejemplo.csv"));

    expect(await screen.findByText("Fila 5 · latitud: El punto está fuera de la zona de Manizales y Villamaría.")).toBeTruthy();
    expect(screen.getByText("Toda la ruta · empresa: La empresa «Empresa Inventada» no existe.")).toBeTruthy();
    expect(screen.getByText("Con errores").nextSibling?.textContent).toBe("2");
    expect((screen.getByRole("button", { name: "Crear 1 ruta" }) as HTMLButtonElement).disabled).toBe(false);
  });

  it("sin ninguna ruta válida el botón de confirmar queda deshabilitado", async () => {
    fetchMock.mockResolvedValueOnce(respuesta(200, previa([fueraDeZona])));
    const u = montar();
    await subir(u, csv("importacion_rutas_con_errores_ejemplo.csv"));

    const boton = (await screen.findByRole("button", { name: "Crear 0 rutas" })) as HTMLButtonElement;
    expect(boton.disabled).toBe(true);
    expect(screen.getByText(/No hay rutas válidas para crear/)).toBeTruthy();
  });

  it("confirmar: un solo envío aunque se haga doble clic, y lista creadas con enlace a «Ver» y avisos", async () => {
    const creada = { nombre: valida.nombre, rutaId: "11111111-2222-3333-4444-555555555555", puntos: 4,
      avisos: ["Tramo 3→4 sin ruta real, se usó línea recta."] };
    const resultado: ResultadoImportacion = {
      creadas: [creada], omitidas: [fueraDeZona], erroresGenerales: [], columnasIgnoradas: [], totalFilas: 7,
      resumen: { creadas: 1, omitidas: 1 },
    };
    let terminar: (r: Response) => void = () => {};
    fetchMock
      .mockResolvedValueOnce(respuesta(200, previa([valida, fueraDeZona])))
      .mockReturnValueOnce(new Promise<Response>((res) => { terminar = res; }));
    const u = montar();
    await subir(u, csv("importacion_rutas_con_errores_ejemplo.csv"));

    const crear = await screen.findByRole("button", { name: "Crear 1 ruta" });
    await u.dblClick(crear);
    expect(await screen.findByText(/Puede tardar hasta 60 segundos/)).toBeTruthy();
    expect(fetchMock).toHaveBeenCalledTimes(2); // vista previa + una sola confirmación
    expect(String(fetchMock.mock.calls[1]![0])).toMatch(/\/rutas\/importacion\/confirmar$/);

    terminar(respuesta(201, resultado));
    expect(await screen.findByText("Se creó 1 ruta · 1 omitida")).toBeTruthy();
    expect(screen.getByText("Tramo 3→4 sin ruta real, se usó línea recta.")).toBeTruthy();
    expect(screen.getByRole("link", { name: "Ver ruta" }).getAttribute("href")).toBe(`/secretaria/rutas?ver=${creada.rutaId}`);
    expect(screen.getByText("Fila 5 · latitud: El punto está fuera de la zona de Manizales y Villamaría.")).toBeTruthy();
  });

  it("reenviar el mismo archivo (200, todas duplicadas) dice que no se creó ninguna ruta", async () => {
    const duplicada: RutaImportada = { ...valida, estado: "duplicada", paraderosNuevos: null, paraderosReutilizados: null, avisos: [],
      errores: [{ fila: null, columna: "ruta", motivo: "ruta_duplicada", mensaje: "Ya existe una ruta con ese nombre; no se modifica." }] };
    fetchMock
      .mockResolvedValueOnce(respuesta(200, previa([valida])))
      .mockResolvedValueOnce(respuesta(200, {
        creadas: [], omitidas: [duplicada], erroresGenerales: [], columnasIgnoradas: [], totalFilas: 4,
        resumen: { creadas: 0, omitidas: 1 },
      }));
    const u = montar();
    await subir(u, csv("importacion_rutas_ejemplo.csv"));
    await u.click(await screen.findByRole("button", { name: "Crear 1 ruta" }));

    expect(await screen.findByText(/No se creó ninguna ruta/)).toBeTruthy();
    expect(screen.getByText(/Ya existe una ruta con ese nombre/)).toBeTruthy();
  });

  it("un 400 del archivo completo muestra el motivo en español", async () => {
    fetchMock.mockResolvedValueOnce(respuesta(400, { error: {
      codigo: "VALIDACION", mensaje: "Archivo inválido", reintentable: false,
      detalles: [{ fila: 1, columna: "latitud", motivo: "columna_obligatoria" }, { motivo: "demasiadas_rutas" }],
    } }));
    const u = montar();
    await subir(u, csv("importacion_rutas_ejemplo.csv"));

    expect(await screen.findByText("Falta una columna obligatoria. Columna «latitud».")).toBeTruthy();
    expect(screen.getByText("El archivo tiene más de 10 rutas.")).toBeTruthy();
  });

  it("403 muestra «No tienes permiso» y error de red ofrece Reintentar", async () => {
    fetchMock.mockResolvedValueOnce(respuesta(403, { error: { codigo: "NO_AUTORIZADO", mensaje: "x" } }));
    const u = montar();
    await subir(u, csv("importacion_rutas_ejemplo.csv"));
    expect(await screen.findByText("No tienes permiso para esta sección")).toBeTruthy();

    fetchMock.mockRejectedValueOnce(new TypeError("Failed to fetch")).mockResolvedValueOnce(respuesta(200, previa([valida])));
    await subir(u, csv("importacion_rutas_ejemplo.csv"));
    await waitFor(() => expect(screen.getByRole("button", { name: "Reintentar" })).toBeTruthy());
    await u.click(screen.getByRole("button", { name: "Reintentar" }));
    expect(await screen.findByText(valida.nombre)).toBeTruthy();
  });
});
