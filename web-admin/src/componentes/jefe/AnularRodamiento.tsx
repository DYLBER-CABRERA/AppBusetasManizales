"use client";
import { useMutation, useQueryClient } from "@tanstack/react-query";
import { useState } from "react";
import { Modal } from "@/componentes/Modal";
import { useToast } from "@/componentes/Toast";
import { ErrorApi } from "@/lib/errores";
import { anularRodamiento } from "@/lib/jefe";

type Props = { rodamientoId: string; version: number; claveConsulta: readonly unknown[]; fechaTexto: string; onConflicto: () => void };

/** Anular el rodamiento (desde borrador o publicado) con confirmación; en 409 de versión pide recargar. */
export function AnularRodamiento({ rodamientoId, version, claveConsulta, fechaTexto, onConflicto }: Props) {
  const cliente = useQueryClient();
  const toast = useToast();
  const [abierto, setAbierto] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const anular = useMutation({
    mutationFn: () => anularRodamiento(rodamientoId, version),
    onSuccess: async () => {
      setAbierto(false);
      await cliente.invalidateQueries({ queryKey: claveConsulta });
      toast("Anulado");
    },
    onError: (e) => {
      if (e instanceof ErrorApi && e.esConflictoVersion) {
        setAbierto(false);
        return onConflicto();
      }
      setError(e.message);
    },
  });

  return (
    <div className="mt-6">
      <button type="button" onClick={() => { setError(null); setAbierto(true); }}
        className="min-h-11 rounded border border-ladrillo px-5 font-semibold text-ladrillo hover:bg-ladrillo-claro">
        Anular rodamiento
      </button>
      <Modal abierto={abierto} titulo="¿Anular el rodamiento?" onCerrar={() => setAbierto(false)}
        acciones={
          <>
            <button type="button" onClick={() => setAbierto(false)} className="min-h-11 rounded border border-tinta px-5 font-semibold">Cancelar</button>
            <button type="button" disabled={anular.isPending} onClick={() => anular.mutate()}
              className="min-h-11 rounded bg-ladrillo px-5 font-semibold text-white disabled:opacity-60">
              {anular.isPending ? "Anulando…" : "Anular"}
            </button>
          </>
        }>
        <p>Se anulará el rodamiento del {fechaTexto}. Después podrás crear uno nuevo para esa fecha.</p>
        {error ? <p role="alert" className="mt-3 rounded bg-ladrillo-claro p-3 text-ladrillo">Error: {error}</p> : null}
      </Modal>
    </div>
  );
}
