"use client";
import { useState } from "react";
import { Modal } from "@/componentes/Modal";
import { useToast } from "@/componentes/Toast";

type Props = {
  /** El secreto a mostrar; `null` mantiene el modal cerrado. */
  secreto: string | null;
  titulo: string;
  advertencia: string;
  detalle: string;
  confirmacion: string;
  /** Solo se llama desde el botón «Cerrar», una vez copiado o confirmado el secreto. */
  onCerrar: () => void;
};

/**
 * Un secreto que el backend devuelve una sola vez (clave de fuente GPS, contraseña de una cuenta nueva).
 * Este modal no se cierra con Esc, con clic fuera ni con otra tecla: solo con «Cerrar», que se habilita
 * tras copiar o confirmar que se guardó. Pásale una `key` distinta por secreto para que el estado empiece limpio.
 */
export function ModalSecretoUnico({ secreto, titulo, advertencia, detalle, confirmacion, onCerrar }: Props) {
  const toast = useToast();
  const [copiada, setCopiada] = useState(false);
  const [confirmada, setConfirmada] = useState(false);

  async function copiar() {
    if (!secreto) return;
    try {
      await navigator.clipboard.writeText(secreto);
      setCopiada(true);
      toast("Copiada");
    } catch {
      toast("No se pudo copiar: selecciónala y cópiala a mano");
    }
  }

  const puedeCerrar = copiada || confirmada;

  return (
    <Modal abierto={secreto !== null} obligatorio titulo={titulo} onCerrar={() => {}}
      acciones={
        <>
          <button type="button" data-foco-inicial onClick={copiar}
            className="min-h-11 rounded border border-verde px-5 font-semibold text-verde">Copiar</button>
          <button type="button" disabled={!puedeCerrar} onClick={onCerrar}
            className="min-h-11 rounded bg-verde px-5 font-semibold text-white disabled:opacity-50">Cerrar</button>
        </>
      }>
      <p className="mb-2 font-semibold">{advertencia}</p>
      <p className="mb-2">{detalle}</p>
      <code className="block break-all rounded bg-fondo p-3 text-base select-all">{secreto}</code>
      <label className="mt-3 flex min-h-11 items-center gap-2">
        <input type="checkbox" className="size-5" checked={confirmada} onChange={(e) => setConfirmada(e.target.checked)} />
        {confirmacion}
      </label>
      <p className="mt-1 text-xs">El botón Cerrar se habilita al copiar o al marcar esta casilla.</p>
    </Modal>
  );
}
