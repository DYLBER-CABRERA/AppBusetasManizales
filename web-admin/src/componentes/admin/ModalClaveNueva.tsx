"use client";
import { useState } from "react";
import { Modal } from "@/componentes/Modal";
import { useToast } from "@/componentes/Toast";
import type { components } from "@/lib/tipos-api";

type CredencialCreada = components["schemas"]["CredencialGpsCreada"];

type Props = {
  credencial: CredencialCreada | null;
  empresa: string;
  /** Solo se llama desde el botón «Cerrar», una vez copiada o confirmada la clave. */
  onCerrar: () => void;
};

/**
 * La clave de una fuente GPS se muestra una sola vez. Este modal no se cierra con Esc, con clic fuera
 * ni con otra tecla: solo con «Cerrar», que se habilita tras copiar la clave o confirmar que se guardó.
 * Pásale `key={credencial?.id}` para que el estado de copiado empiece limpio con cada clave.
 */
export function ModalClaveNueva({ credencial, empresa, onCerrar }: Props) {
  const toast = useToast();
  const [copiada, setCopiada] = useState(false);
  const [confirmada, setConfirmada] = useState(false);

  async function copiar() {
    if (!credencial) return;
    try {
      await navigator.clipboard.writeText(credencial.clave);
      setCopiada(true);
      toast("Copiada");
    } catch {
      toast("No se pudo copiar: selecciónala y cópiala a mano");
    }
  }

  const puedeCerrar = copiada || confirmada;

  return (
    <Modal abierto={credencial !== null} obligatorio titulo="Clave nueva" onCerrar={() => {}}
      acciones={
        <>
          <button type="button" data-foco-inicial onClick={copiar}
            className="min-h-11 rounded border border-verde px-5 font-semibold text-verde">Copiar</button>
          <button type="button" disabled={!puedeCerrar} onClick={onCerrar}
            className="min-h-11 rounded bg-verde px-5 font-semibold text-white disabled:opacity-50">Cerrar</button>
        </>
      }>
      <p className="mb-2 font-semibold">Copia la clave ahora. No podrás verla otra vez.</p>
      <p className="mb-2">Fuente «{credencial?.nombre}» de {empresa}:</p>
      <code className="block break-all rounded bg-fondo p-3 text-base select-all">{credencial?.clave}</code>
      <label className="mt-3 flex min-h-11 items-center gap-2">
        <input type="checkbox" className="size-5" checked={confirmada} onChange={(e) => setConfirmada(e.target.checked)} />
        Ya guardé la clave en un lugar seguro
      </label>
      <p className="mt-1 text-xs">El botón Cerrar se habilita al copiar la clave o al marcar esta casilla.</p>
    </Modal>
  );
}
