"use client";
import { useMutation, useQueryClient } from "@tanstack/react-query";
import { useState } from "react";
import { useToast } from "@/componentes/Toast";
import { ErrorApi } from "@/lib/errores";
import {
  filasDeFrecuencias, frecuenciasParaEnviar, TIPOS_DIA, validarFranjas, type ErroresFranja, type FilaFranja, type TipoDia,
} from "@/lib/horarios";
import { guardarFrecuencias, type FrecuenciasDeServicio } from "@/lib/jefe";

const campo = "mt-1 min-h-11 w-full rounded border border-tinta/40 bg-white px-2";
const mensajeError = "mt-1 text-sm text-ladrillo";

type Props = { servicioId: string; datos: FrecuenciasDeServicio; onConflicto: () => void };

/** Frecuencias por tipo de día y franja horaria. */
export function EditorFrecuencias({ servicioId, datos, onConflicto }: Props) {
  const cliente = useQueryClient();
  const toast = useToast();
  const [filas, setFilas] = useState<FilaFranja[]>(() => filasDeFrecuencias(datos.frecuencias));
  const [errores, setErrores] = useState<Record<string, ErroresFranja>>({});
  const [errorServidor, setErrorServidor] = useState<string | null>(null);

  const guardar = useMutation({
    mutationFn: () => guardarFrecuencias(servicioId, { frecuencias: frecuenciasParaEnviar(filas), version: datos.version }),
    onSuccess: async () => {
      setErrorServidor(null);
      await cliente.invalidateQueries({ predicate: (q) => q.queryKey[0] === "jefe" && (q.queryKey[2] === "horarios" || q.queryKey[2] === "frecuencias") });
      toast("Guardado");
    },
    onError: (e) => {
      if (e instanceof ErrorApi && e.esConflictoVersion) return onConflicto();
      setErrorServidor(e.message);
    },
  });

  const cambiar = (clave: string, parche: Partial<FilaFranja>) => {
    setFilas((fs) => fs.map((f) => (f.clave === clave ? { ...f, ...parche } : f)));
    setErrores((e) => ({ ...e, [clave]: {} }));
  };
  const agregar = (tipoDia: TipoDia) =>
    setFilas((fs) => [...fs, { clave: crypto.randomUUID(), tipoDia, franjaInicio: "", franjaFin: "", minutosMin: "", minutosMax: "", nota: "" }]);
  const quitar = (clave: string) => setFilas((fs) => fs.filter((f) => f.clave !== clave));

  function enviar(ev: React.FormEvent) {
    ev.preventDefault();
    setErrorServidor(null);
    const nuevos = validarFranjas(filas);
    setErrores(nuevos);
    if (Object.keys(nuevos).length === 0) guardar.mutate();
  }

  return (
    <form noValidate onSubmit={enviar} className="space-y-4">
      {TIPOS_DIA.map(({ valor, etiqueta }) => {
        const delDia = filas.filter((f) => f.tipoDia === valor);
        return (
          <fieldset key={valor} className="rounded-lg border border-borde bg-white p-4">
            <legend className="px-1 font-bold">{etiqueta}</legend>
            {delDia.length === 0 ? <p className="text-sm">Sin frecuencias para este día.</p> : null}
            <div className="space-y-3">
              {delDia.map((f, i) => {
                const e = errores[f.clave] ?? {};
                const id = (n: string) => `${n}-${f.clave}`;
                return (
                  <div key={f.clave} className="grid items-start gap-3 rounded bg-fondo p-3 md:grid-cols-[repeat(4,1fr)_auto]" role="group" aria-label={`Franja ${i + 1} de ${etiqueta}`}>
                    <div>
                      <label htmlFor={id("ini")} className="block text-sm font-semibold">Desde</label>
                      <input id={id("ini")} type="time" value={f.franjaInicio} aria-invalid={!!e.franjaInicio} className={campo}
                        onChange={(ev) => cambiar(f.clave, { franjaInicio: ev.target.value })} />
                      {e.franjaInicio ? <p className={mensajeError}>{e.franjaInicio}</p> : null}
                    </div>
                    <div>
                      <label htmlFor={id("fin")} className="block text-sm font-semibold">Hasta (24:00 = medianoche)</label>
                      <input id={id("fin")} type="text" inputMode="numeric" placeholder="HH:MM" maxLength={5} value={f.franjaFin} aria-invalid={!!e.franjaFin} className={campo}
                        onChange={(ev) => cambiar(f.clave, { franjaFin: ev.target.value })} />
                      {e.franjaFin ? <p className={mensajeError}>{e.franjaFin}</p> : null}
                    </div>
                    <div>
                      <label htmlFor={id("min")} className="block text-sm font-semibold">Cada (mín.)</label>
                      <input id={id("min")} type="text" inputMode="numeric" value={f.minutosMin} aria-invalid={!!e.minutosMin} className={campo}
                        onChange={(ev) => cambiar(f.clave, { minutosMin: ev.target.value })} />
                      {e.minutosMin ? <p className={mensajeError}>{e.minutosMin}</p> : null}
                    </div>
                    <div>
                      <label htmlFor={id("max")} className="block text-sm font-semibold">Cada (máx.)</label>
                      <input id={id("max")} type="text" inputMode="numeric" value={f.minutosMax} aria-invalid={!!e.minutosMax} className={campo}
                        onChange={(ev) => cambiar(f.clave, { minutosMax: ev.target.value })} />
                      {e.minutosMax ? <p className={mensajeError}>{e.minutosMax}</p> : null}
                    </div>
                    <button type="button" onClick={() => quitar(f.clave)} aria-label={`Quitar franja ${i + 1} de ${etiqueta}`}
                      className="mt-6 min-h-11 rounded border border-ladrillo px-3 font-semibold text-ladrillo">Quitar</button>
                  </div>
                );
              })}
            </div>
            <button type="button" onClick={() => agregar(valor)} className="mt-3 min-h-11 rounded border border-verde px-4 font-semibold text-verde hover:bg-fondo">
              Agregar franja
            </button>
          </fieldset>
        );
      })}
      {errorServidor ? <p role="alert" className="rounded bg-ladrillo-claro p-3 text-ladrillo">Error: {errorServidor}</p> : null}
      <button type="submit" disabled={guardar.isPending}
        className="min-h-11 rounded bg-verde px-5 font-semibold text-white hover:bg-verde-oscuro disabled:opacity-60">
        {guardar.isPending ? "Guardando…" : "Guardar frecuencias"}
      </button>
    </form>
  );
}
