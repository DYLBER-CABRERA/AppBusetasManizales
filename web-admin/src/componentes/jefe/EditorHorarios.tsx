"use client";
import { useMutation, useQueryClient } from "@tanstack/react-query";
import { useState } from "react";
import { useToast } from "@/componentes/Toast";
import { ErrorApi } from "@/lib/errores";
import { filasDeHorarios, horariosParaEnviar, TIPOS_DIA, validarHorario, type ErroresHorario, type FilaHorario, type TipoDia } from "@/lib/horarios";
import { guardarHorarios, type HorariosDeServicio } from "@/lib/jefe";

const campo = "mt-1 min-h-11 w-full rounded border border-tinta/40 bg-white px-3";
const mensajeError = "mt-1 text-sm text-ladrillo";

type Props = { servicioId: string; datos: HorariosDeServicio; onConflicto: () => void };

/** Horarios por tipo de día. Un día sin marcar queda «Información pendiente de actualización». */
export function EditorHorarios({ servicioId, datos, onConflicto }: Props) {
  const cliente = useQueryClient();
  const toast = useToast();
  const [filas, setFilas] = useState<FilaHorario[]>(() => filasDeHorarios(datos.horarios));
  const [errores, setErrores] = useState<Partial<Record<TipoDia, ErroresHorario>>>({});
  const [errorServidor, setErrorServidor] = useState<string | null>(null);

  const guardar = useMutation({
    // La versión sale siempre de lo último cargado: cada PUT (de horarios o de frecuencias) la incrementa.
    mutationFn: () => guardarHorarios(servicioId, { horarios: horariosParaEnviar(filas), version: datos.version }),
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

  const cambiar = (tipoDia: TipoDia, parche: Partial<FilaHorario>) => {
    setFilas((fs) => fs.map((f) => (f.tipoDia === tipoDia ? { ...f, ...parche } : f)));
    setErrores((e) => ({ ...e, [tipoDia]: undefined }));
  };

  function enviar(ev: React.FormEvent) {
    ev.preventDefault();
    setErrorServidor(null);
    const nuevos = Object.fromEntries(filas.map((f) => [f.tipoDia, validarHorario(f)])) as Record<TipoDia, ErroresHorario>;
    setErrores(nuevos);
    if (Object.values(nuevos).every((e) => Object.keys(e).length === 0)) guardar.mutate();
  }

  return (
    <form noValidate onSubmit={enviar} className="space-y-4">
      {TIPOS_DIA.map(({ valor, etiqueta }) => {
        const f = filas.find((x) => x.tipoDia === valor)!;
        const e = errores[valor] ?? {};
        return (
          <fieldset key={valor} className="rounded-lg border border-borde bg-white p-4">
            <legend className="px-1 font-bold">{etiqueta}</legend>
            <label className="flex min-h-11 items-center gap-2 font-semibold">
              <input type="checkbox" className="size-5" checked={f.activo} onChange={(ev) => cambiar(valor, { activo: ev.target.checked })} />
              Este día tiene horario
            </label>
            {!f.activo ? <p className="text-sm">Información pendiente de actualización</p> : (
              <div className="mt-2 grid gap-4 md:grid-cols-4">
                <div>
                  <label htmlFor={`pri-${valor}`} className="block text-sm font-semibold">Primera salida</label>
                  <input id={`pri-${valor}`} type="time" value={f.primeraSalida} aria-invalid={!!e.primeraSalida} className={campo}
                    onChange={(ev) => cambiar(valor, { primeraSalida: ev.target.value })} />
                  {e.primeraSalida ? <p className={mensajeError}>{e.primeraSalida}</p> : null}
                </div>
                <div>
                  <label htmlFor={`ult-${valor}`} className="block text-sm font-semibold">Última salida</label>
                  <input id={`ult-${valor}`} type="time" value={f.ultimaSalida} aria-invalid={!!e.ultimaSalida} className={campo}
                    onChange={(ev) => cambiar(valor, { ultimaSalida: ev.target.value })} />
                  {e.ultimaSalida ? <p className={mensajeError}>{e.ultimaSalida}</p> : null}
                </div>
                <div>
                  <label htmlFor={`cie-${valor}`} className="block text-sm font-semibold">Cierre (opcional)</label>
                  <input id={`cie-${valor}`} type="time" value={f.cierre} aria-invalid={!!e.cierre} className={campo}
                    onChange={(ev) => cambiar(valor, { cierre: ev.target.value })} />
                  {e.cierre ? <p className={mensajeError}>{e.cierre}</p> : null}
                </div>
                <div>
                  <label htmlFor={`not-${valor}`} className="block text-sm font-semibold">Nota (opcional)</label>
                  <input id={`not-${valor}`} type="text" value={f.nota} className={campo} onChange={(ev) => cambiar(valor, { nota: ev.target.value })} />
                </div>
              </div>
            )}
          </fieldset>
        );
      })}
      {errorServidor ? <p role="alert" className="rounded bg-ladrillo-claro p-3 text-ladrillo">Error: {errorServidor}</p> : null}
      <button type="submit" disabled={guardar.isPending}
        className="min-h-11 rounded bg-verde px-5 font-semibold text-white hover:bg-verde-oscuro disabled:opacity-60">
        {guardar.isPending ? "Guardando…" : "Guardar horarios"}
      </button>
    </form>
  );
}
