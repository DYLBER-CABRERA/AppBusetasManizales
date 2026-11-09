"use client";
import { useMutation, useQueryClient } from "@tanstack/react-query";
import Link from "next/link";
import { useEffect, useRef, useState } from "react";
import { BannerError } from "@/componentes/BannerError";
import { Esqueleto } from "@/componentes/Esqueleto";
import { useToast } from "@/componentes/Toast";
import { Vacio } from "@/componentes/Vacio";
import {
  COLUMNAS_IMPORTACION, confirmarImportacion, descargarPlantilla, ESTADO_RUTA, LIMITES_IMPORTACION, problemaConArchivo,
  problemasDeArchivo, textoErrorImportacion, vistaPreviaImportacion,
  type ErrorImportacion, type ResultadoImportacion, type VistaPrevia,
} from "@/lib/importacion-rutas";
import { CLAVE_PARADEROS, CLAVE_RUTAS } from "@/lib/secretaria";

const botonPrimario = "min-h-11 rounded bg-verde px-5 font-semibold text-white hover:bg-verde-oscuro disabled:opacity-50";
const botonSecundario = "min-h-11 rounded border border-verde px-4 font-semibold text-verde hover:bg-fondo disabled:opacity-50";

function ListaErrores({ errores }: { errores: ErrorImportacion[] }) {
  if (errores.length === 0) return <span aria-hidden="true">—</span>;
  return (
    <ul className="list-disc space-y-1 pl-4 text-ladrillo">
      {errores.map((e, i) => <li key={i}>{textoErrorImportacion(e)}</li>)}
    </ul>
  );
}

function ListaAvisos({ avisos }: { avisos: string[] }) {
  if (avisos.length === 0) return <span aria-hidden="true">—</span>;
  return <ul className="list-disc space-y-1 pl-4">{avisos.map((a, i) => <li key={i}>{a}</li>)}</ul>;
}

const cifra = (n: number | null | undefined) => (n == null ? "—" : String(n));

/** Resumen y tabla de la vista previa (contrato §25): una fila por ruta. */
function TablaVistaPrevia({ vista }: { vista: VistaPrevia }) {
  return (
    <div className="space-y-4">
      <dl className="grid gap-3 sm:grid-cols-3">
        {[
          ["Válidas", vista.resumen.validas, "Se crearán al confirmar"],
          ["Con errores", vista.resumen.conErrores, "No se crearán"],
          ["Duplicadas", vista.resumen.duplicadas, "Ya existen; no se modifican"],
        ].map(([titulo, valor, nota]) => (
          <div key={String(titulo)} className="rounded-lg border border-borde bg-white p-4">
            <dt className="text-sm font-semibold">{titulo}</dt>
            <dd className="text-3xl font-bold">{valor}</dd>
            <p className="text-xs">{nota}</p>
          </div>
        ))}
      </dl>
      <p className="text-sm">{vista.totalFilas} filas de datos leídas.</p>

      {vista.columnasIgnoradas.length > 0 ? (
        <p role="status" className="rounded border border-amarillo bg-white p-3 text-sm">
          Columnas ignoradas (no se reconocen): {vista.columnasIgnoradas.map((c) => `«${c}»`).join(", ")}.
        </p>
      ) : null}

      {vista.erroresGenerales.length > 0 ? (
        <div role="alert" className="rounded bg-ladrillo-claro p-3 text-ladrillo">
          <p className="font-semibold">Filas que no se pueden asignar a una ruta</p>
          <ListaErrores errores={vista.erroresGenerales} />
        </div>
      ) : null}

      {vista.rutas.length > 0 ? (
        <div className="overflow-x-auto rounded-lg border border-borde bg-white">
          <table className="w-full min-w-[56rem] text-left text-sm">
            <caption className="sr-only">Rutas del archivo con su estado, empresa, puntos, paraderos, avisos y errores</caption>
            <thead className="bg-fondo">
              <tr>
                {["Ruta", "Estado", "Empresa", "Puntos", "Paraderos nuevos", "Reutilizados", "Avisos", "Errores"].map((c) => (
                  <th key={c} scope="col" className="px-3 py-2 font-semibold">{c}</th>
                ))}
              </tr>
            </thead>
            <tbody>
              {vista.rutas.map((r, i) => (
                <tr key={`${r.nombre}-${i}`} className="border-t border-borde align-top">
                  <th scope="row" className="px-3 py-2 font-semibold">{r.nombre}</th>
                  <td className="px-3 py-2">
                    <span className={`inline-block rounded px-2 py-1 font-semibold ${ESTADO_RUTA[r.estado].clase}`}>
                      {ESTADO_RUTA[r.estado].etiqueta}
                    </span>
                  </td>
                  <td className="px-3 py-2">{r.empresa ?? "—"}{r.codigoPublico ? ` · ${r.codigoPublico}` : ""}</td>
                  <td className="px-3 py-2">{r.puntos}</td>
                  <td className="px-3 py-2">{cifra(r.paraderosNuevos)}</td>
                  <td className="px-3 py-2">{cifra(r.paraderosReutilizados)}</td>
                  <td className="px-3 py-2"><ListaAvisos avisos={r.avisos} /></td>
                  <td className="px-3 py-2"><ListaErrores errores={r.errores} /></td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      ) : null}
    </div>
  );
}

/** Resultado de confirmar: rutas creadas (con enlace a «Ver») y rutas omitidas con sus errores. */
function ResultadoConfirmacion({ resultado, onOtro }: { resultado: ResultadoImportacion; onOtro: () => void }) {
  const { creadas, omitidas } = resultado;
  return (
    <div className="space-y-4">
      <h2 className="text-xl font-bold">
        {creadas.length > 0
          ? `Se ${creadas.length === 1 ? "creó 1 ruta" : `crearon ${creadas.length} rutas`}`
          : "No se creó ninguna ruta"}
        {omitidas.length > 0 ? ` · ${omitidas.length} omitida${omitidas.length === 1 ? "" : "s"}` : ""}
      </h2>
      {creadas.length === 0 ? (
        <p className="text-sm">Todas las rutas del archivo se omitieron (por ejemplo, porque ya existen). Revisa los motivos abajo.</p>
      ) : (
        <ul className="space-y-2" aria-label="Rutas creadas">
          {creadas.map((c) => (
            <li key={c.rutaId} className="rounded-lg border border-borde bg-white p-4">
              <div className="flex flex-wrap items-center justify-between gap-3">
                <p className="font-semibold">{c.nombre} <span className="font-normal">· {c.puntos} puntos</span></p>
                <Link href={`/secretaria/rutas?ver=${c.rutaId}`} className={`${botonSecundario} inline-flex items-center`}>
                  Ver ruta
                </Link>
              </div>
              {c.avisos.length > 0 ? (
                <ul role="status" className="mt-2 list-disc space-y-1 rounded border border-amarillo bg-fondo p-2 pl-6 text-sm">
                  {c.avisos.map((a, i) => <li key={i}>{a}</li>)}
                </ul>
              ) : (
                <p className="mt-1 text-sm">Trazado completo por calles.</p>
              )}
            </li>
          ))}
        </ul>
      )}
      {omitidas.length > 0 ? (
        <div>
          <h3 className="font-semibold">Rutas omitidas</h3>
          <ul className="mt-2 space-y-2">
            {omitidas.map((o, i) => (
              <li key={`${o.nombre}-${i}`} className="rounded-lg border border-borde bg-white p-4">
                <p className="font-semibold">{o.nombre} <span className={`ml-2 rounded px-2 py-1 text-sm ${ESTADO_RUTA[o.estado].clase}`}>{ESTADO_RUTA[o.estado].etiqueta}</span></p>
                <div className="mt-1 text-sm"><ListaErrores errores={o.errores} /></div>
              </li>
            ))}
          </ul>
        </div>
      ) : null}
      {resultado.erroresGenerales.length > 0 ? (
        <div role="alert" className="rounded bg-ladrillo-claro p-3 text-ladrillo">
          <p className="font-semibold">Filas que no se pudieron asignar a una ruta</p>
          <ListaErrores errores={resultado.erroresGenerales} />
        </div>
      ) : null}
      <div className="flex flex-wrap gap-3">
        <button type="button" className={botonPrimario} onClick={onOtro}>Importar otro archivo</button>
        <Link href="/secretaria/rutas" className={`${botonSecundario} inline-flex items-center`}>Volver a Rutas</Link>
      </div>
    </div>
  );
}

/** Progreso de la confirmación: crear con trazado por calles (OSRM) puede tardar hasta ~60 s. */
function ProgresoConfirmacion() {
  const [segundos, setSegundos] = useState(0);
  useEffect(() => {
    const id = setInterval(() => setSegundos((s) => s + 1), 1000);
    return () => clearInterval(id);
  }, []);
  return (
    <div role="status" aria-live="polite" className="rounded-lg border border-verde bg-white p-4">
      <p className="font-semibold">Creando las rutas y trazando por calles… {segundos} s</p>
      <p className="text-sm">Puede tardar hasta 60 segundos. No cierres ni recargues esta página.</p>
      <div className="mt-3 h-2 overflow-hidden rounded bg-fondo" aria-hidden="true">
        <div className="h-full w-1/3 animate-pulse rounded bg-verde" />
      </div>
    </div>
  );
}

export function PantallaImportarRutas() {
  const cliente = useQueryClient();
  const toast = useToast();
  const [archivo, setArchivo] = useState<File | null>(null);
  const [problema, setProblema] = useState<string | null>(null);
  const [resultado, setResultado] = useState<ResultadoImportacion | null>(null);
  const [descargando, setDescargando] = useState(false);
  const [errorPlantilla, setErrorPlantilla] = useState<string | null>(null);
  const entrada = useRef<HTMLInputElement>(null);
  const confirmando = useRef(false); // evita el doble envío aunque el clic llegue dos veces antes de repintar

  const revisar = useMutation({ mutationFn: vistaPreviaImportacion });
  const confirmar = useMutation({
    mutationFn: confirmarImportacion,
    onSuccess: async (r) => {
      setResultado(r);
      if (r.creadas.length > 0) {
        await Promise.all([
          cliente.invalidateQueries({ queryKey: CLAVE_RUTAS }),
          cliente.invalidateQueries({ queryKey: CLAVE_PARADEROS }),
        ]);
        toast("Importadas");
      }
    },
    onSettled: () => { confirmando.current = false; },
  });

  const ocupado = revisar.isPending || confirmar.isPending;
  const vista = revisar.data;
  const hayValidas = (vista?.resumen.validas ?? 0) >= 1;

  async function elegir(f: File | undefined) {
    revisar.reset();
    confirmar.reset();
    setResultado(null);
    setProblema(null);
    setArchivo(null);
    if (!f) return;
    const p = await problemaConArchivo(f);
    if (p) return setProblema(p);
    setArchivo(f);
    revisar.mutate(f);
  }

  function reiniciar() {
    revisar.reset();
    confirmar.reset();
    setResultado(null);
    setProblema(null);
    setArchivo(null);
    if (entrada.current) entrada.current.value = "";
  }

  function crear() {
    if (!archivo || confirmando.current || !hayValidas) return;
    confirmando.current = true;
    confirmar.mutate(archivo);
  }

  async function bajarPlantilla() {
    setErrorPlantilla(null);
    setDescargando(true);
    try {
      await descargarPlantilla();
    } catch (e) {
      setErrorPlantilla(e instanceof Error ? e.message : "No se pudo descargar la plantilla.");
    } finally {
      setDescargando(false);
    }
  }

  // Un 400 del archivo completo trae motivos por fila/columna; cualquier otro error va al banner con Reintentar.
  const errorActivo = confirmar.error ?? revisar.error;
  const problemasArchivo = errorActivo ? problemasDeArchivo(errorActivo) : [];

  return (
    <section className="space-y-6">
      <div className="flex flex-wrap items-center justify-between gap-4">
        <h1 className="text-2xl font-bold">Importar rutas desde archivo</h1>
        <Link href="/secretaria/rutas" className={`${botonSecundario} inline-flex items-center`}>Volver a Rutas</Link>
      </div>

      {resultado ? (
        <ResultadoConfirmacion resultado={resultado} onOtro={reiniciar} />
      ) : (
        <>
          <div className="space-y-3 rounded-lg border border-borde bg-white p-5">
            <p>
              Sube un archivo <strong>.csv</strong> con una fila por punto de cada ruta. Primero se revisa sin guardar nada;
              después decides si crear las rutas válidas.
            </p>
            <p className="text-sm">
              Columnas: {COLUMNAS_IMPORTACION.map((c) => <code key={c} className="mr-1 rounded bg-fondo px-1">{c}</code>)}
            </p>
            <p className="text-sm">
              Límites: {LIMITES_IMPORTACION.kb} KB · {LIMITES_IMPORTACION.filas} filas · {LIMITES_IMPORTACION.rutas} rutas por archivo ·{" "}
              {LIMITES_IMPORTACION.puntos} puntos por ruta.
            </p>
            <p className="text-sm">Si tu archivo es de Excel (.xlsx), guárdalo antes como «CSV (delimitado por comas)».</p>
            <div className="flex flex-wrap items-end gap-4">
              <button type="button" className={botonSecundario} onClick={bajarPlantilla} disabled={descargando}>
                {descargando ? "Descargando…" : "Descargar plantilla"}
              </button>
              <div>
                <label htmlFor="archivo-rutas" className="block font-semibold">Archivo CSV</label>
                <input id="archivo-rutas" ref={entrada} type="file" accept=".csv,text/csv" disabled={ocupado}
                  onChange={(e) => void elegir(e.target.files?.[0])}
                  className="mt-1 block min-h-11 text-sm file:mr-3 file:min-h-11 file:rounded file:border-0 file:bg-verde file:px-4 file:font-semibold file:text-white disabled:opacity-50" />
              </div>
            </div>
            {errorPlantilla ? <p role="alert" className="text-sm text-ladrillo">Error: {errorPlantilla}</p> : null}
          </div>

          {problema ? <p role="alert" className="rounded bg-ladrillo-claro p-3 text-ladrillo">{problema}</p> : null}

          {problemasArchivo.length > 0 ? (
            <div role="alert" className="rounded bg-ladrillo-claro p-3 text-ladrillo">
              <p className="font-semibold">El archivo no se pudo procesar</p>
              <ul className="list-disc space-y-1 pl-5">
                {problemasArchivo.map((p, i) => <li key={i}>{p.texto}</li>)}
              </ul>
            </div>
          ) : errorActivo ? (
            <BannerError mensaje={errorActivo.message}
              onReintentar={archivo ? () => (confirmar.error ? crear() : revisar.mutate(archivo)) : undefined} />
          ) : null}

          {!archivo && !problema && !errorActivo ? (
            <Vacio titulo="Aún no elegiste un archivo"
              causa="Descarga la plantilla, llénala con tus rutas y súbela para ver la vista previa."
              accion={<span className="text-sm">Nada se guarda hasta que confirmes.</span>} />
          ) : null}

          {revisar.isPending ? <Esqueleto filas={5} /> : null}

          {vista ? (
            <>
              <TablaVistaPrevia vista={vista} />
              {confirmar.isPending ? <ProgresoConfirmacion /> : null}
              <div className="flex flex-wrap items-center gap-3">
                <button type="button" className={botonPrimario} onClick={crear} disabled={!hayValidas || ocupado}>
                  {confirmar.isPending
                    ? "Creando rutas…"
                    : `Crear ${vista.resumen.validas} ruta${vista.resumen.validas === 1 ? "" : "s"}`}
                </button>
                <button type="button" className={botonSecundario} onClick={reiniciar} disabled={ocupado}>Elegir otro archivo</button>
                {!hayValidas ? (
                  <p className="text-sm">No hay rutas válidas para crear. Corrige el archivo y vuelve a subirlo.</p>
                ) : null}
              </div>
            </>
          ) : null}
        </>
      )}
    </section>
  );
}
