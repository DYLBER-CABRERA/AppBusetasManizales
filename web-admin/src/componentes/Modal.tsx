"use client";
import { useEffect, useRef, type ReactNode } from "react";

/** Diálogo accesible (elemento <dialog> nativo: foco atrapado, Esc cierra). */
export function Modal({
  abierto, titulo, onCerrar, children, acciones, sinEscape = false,
}: { abierto: boolean; titulo: string; onCerrar: () => void; children: ReactNode; acciones: ReactNode; sinEscape?: boolean }) {
  const ref = useRef<HTMLDialogElement>(null);
  useEffect(() => {
    const d = ref.current;
    if (!d) return;
    if (abierto && !d.open) d.showModal();
    if (!abierto && d.open) d.close();
  }, [abierto]);
  return (
    <dialog
      ref={ref}
      onClose={onCerrar}
      onCancel={sinEscape ? (e) => e.preventDefault() : undefined}
      aria-labelledby="modal-titulo"
      className="m-auto w-full max-w-md rounded-lg p-6 text-tinta backdrop:bg-tinta/50"
    >
      <h2 id="modal-titulo" className="text-lg font-bold">{titulo}</h2>
      <div className="mt-2 text-sm">{children}</div>
      <div className="mt-5 flex justify-end gap-3">{acciones}</div>
    </dialog>
  );
}
