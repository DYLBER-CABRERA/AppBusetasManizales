"use client";
import { zodResolver } from "@hookform/resolvers/zod";
import { useMutation, useQueryClient } from "@tanstack/react-query";
import { useMemo, useState } from "react";
import { useForm } from "react-hook-form";
import { z } from "zod";
import { BannerError } from "@/componentes/BannerError";
import { Esqueleto } from "@/componentes/Esqueleto";
import { Modal } from "@/componentes/Modal";
import { useToast } from "@/componentes/Toast";
import { Vacio } from "@/componentes/Vacio";
import { actualizarParametro, CLAVE_PARAMETROS, useParametros, type Parametro } from "@/lib/admin";
import { ErrorApi } from "@/lib/errores";

const numero = new Intl.NumberFormat("es-CO");

function mensajeRango(p: Parametro): string {
  if (p.minimo != null && p.maximo != null) return `Escribe un valor entre ${numero.format(p.minimo)} y ${numero.format(p.maximo)}.`;
  return "Escribe un número válido.";
}

function FilaParametro({ parametro, onConflicto }: { parametro: Parametro; onConflicto: () => void }) {
  const cliente = useQueryClient();
  const toast = useToast();
  const [errorServidor, setErrorServidor] = useState<string | null>(null);

  const esquema = useMemo(
    () =>
      z.object({
        valor: z.string().refine((v) => {
          const n = Number(v);
          if (v.trim() === "" || !Number.isFinite(n)) return false;
          return (parametro.minimo == null || n >= parametro.minimo) && (parametro.maximo == null || n <= parametro.maximo);
        }, mensajeRango(parametro)),
      }),
    [parametro],
  );
  const { register, handleSubmit, formState: { errors, isDirty } } = useForm<{ valor: string }>({
    resolver: zodResolver(esquema),
    defaultValues: { valor: String(parametro.valor) },
  });

  const guardar = useMutation({
    mutationFn: (valor: number) => actualizarParametro(parametro.clave, { valor, version: parametro.version }),
    onSuccess: (nuevo) => {
      setErrorServidor(null);
      cliente.setQueryData<Parametro[]>(CLAVE_PARAMETROS, (lista) => lista?.map((x) => (x.clave === nuevo.clave ? nuevo : x)));
      toast("Guardado");
    },
    onError: (e) => {
      if (e instanceof ErrorApi && e.esConflictoVersion) return onConflicto();
      setErrorServidor(e.message);
    },
  });

  const id = `parametro-${parametro.clave}`;
  const error = errors.valor?.message ?? errorServidor;
  const editable = typeof parametro.valor === "number";

  return (
    <tr className="border-t border-borde align-top">
      <td className="p-3">
        <label htmlFor={id} className="font-semibold">{parametro.descripcion}</label>
        <p className="text-xs"><code>{parametro.clave}</code></p>
      </td>
      <td className="p-3">
        {editable ? (
          <form noValidate onSubmit={handleSubmit((d) => guardar.mutate(Number(d.valor)))} className="flex items-start gap-2">
            <div>
              <input id={id} type="text" inputMode="decimal" aria-invalid={!!error}
                aria-describedby={`${id}-ayuda`}
                className="min-h-11 w-32 rounded border border-tinta/40 bg-white px-3"
                {...register("valor", { onChange: () => setErrorServidor(null) })} />
              <p id={`${id}-ayuda`} className={`mt-1 text-sm ${error ? "text-ladrillo" : ""}`}>
                {error ??
                  (parametro.minimo != null && parametro.maximo != null
                    ? `Entre ${numero.format(parametro.minimo)} y ${numero.format(parametro.maximo)}.${
                        parametro.clave === "distancia_aviso_llegada_m" ? " Se aplica a las alertas nuevas." : ""
                      }`
                    : "")}
              </p>
            </div>
            <button type="submit" disabled={!isDirty || guardar.isPending}
              className="min-h-11 rounded bg-verde px-4 font-semibold text-white hover:bg-verde-oscuro disabled:opacity-50">
              {guardar.isPending ? "Guardando…" : "Guardar"}
            </button>
          </form>
        ) : (
          <div id={id}>
            <code className="break-all text-sm">{typeof parametro.valor === "object" ? JSON.stringify(parametro.valor) : String(parametro.valor)}</code>
            <p className="mt-1 text-sm">
              {/* PENDIENTE(decisión): editor de caja_ciudad (el backend exige un objeto con las mismas claves). */}
              Solo lectura en esta versión.
            </p>
          </div>
        )}
      </td>
    </tr>
  );
}

export function PantallaParametros() {
  const parametros = useParametros();
  const [conflicto, setConflicto] = useState(false);

  return (
    <section>
      <h1 className="mb-2 text-2xl font-bold">Parámetros</h1>
      <p className="mb-4 text-sm">Un cambio puede tardar hasta 60 s en reflejarse en las apps.</p>
      {parametros.isError ? (
        <div className="mb-4">
          <BannerError mensaje={parametros.error.message} onReintentar={() => parametros.refetch()} />
        </div>
      ) : null}
      {parametros.isPending ? <Esqueleto filas={6} /> : null}
      {parametros.data && parametros.data.length === 0 ? (
        <Vacio titulo="No hay parámetros" causa="El backend no devolvió ningún parámetro global." />
      ) : null}
      {parametros.data && parametros.data.length > 0 ? (
        <div className="overflow-x-auto rounded-lg border border-borde bg-white">
          <table className="w-full text-left">
            <caption className="sr-only">Parámetros globales</caption>
            <thead className="bg-fondo text-sm">
              <tr>
                <th scope="col" className="p-3">Parámetro</th>
                <th scope="col" className="p-3">Valor</th>
              </tr>
            </thead>
            <tbody>
              {parametros.data.map((p) => (
                // La versión en la clave reinicia el formulario tras guardar o recargar.
                <FilaParametro key={`${p.clave}-${p.version}`} parametro={p} onConflicto={() => setConflicto(true)} />
              ))}
            </tbody>
          </table>
        </div>
      ) : null}

      <Modal abierto={conflicto} titulo="Alguien más cambió esto" onCerrar={() => setConflicto(false)}
        acciones={
          <button type="button" onClick={() => { setConflicto(false); void parametros.refetch(); }}
            className="min-h-11 rounded bg-verde px-5 font-semibold text-white">Recargar</button>
        }>
        Alguien más cambió esto. Recarga para ver los cambios.
      </Modal>
    </section>
  );
}
