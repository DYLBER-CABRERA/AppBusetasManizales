"use client";
import { useEffect, useId, useRef, type ReactNode } from "react";

type Props = {
  abierto: boolean;
  titulo: string;
  onCerrar: () => void;
  children: ReactNode;
  acciones: ReactNode;
  /**
   * Modal que solo se cierra con un botón explícito de la pantalla (p. ej. la clave que se muestra una vez).
   * Bloquea Esc y, si el navegador lo cierra de todos modos, lo vuelve a abrir.
   */
  obligatorio?: boolean;
};

/**
 * Diálogo accesible (elemento <dialog> nativo: foco atrapado, el resto de la página inerte).
 * Al abrir, el foco va al elemento con `data-foco-inicial` (o al primer control).
 */
export function Modal({ abierto, titulo, onCerrar, children, acciones, obligatorio = false }: Props) {
  const ref = useRef<HTMLDialogElement>(null);
  const idTitulo = useId();

  function abrir(d: HTMLDialogElement) {
    d.showModal();
    d.querySelector<HTMLElement>("[data-foco-inicial]")?.focus();
  }

  useEffect(() => {
    const d = ref.current;
    if (!d) return;
    if (abierto && !d.open) abrir(d);
    if (!abierto && d.open) d.close();
  }, [abierto]);

  function alCerrarElNavegador() {
    const d = ref.current;
    // Chromium cierra un <dialog> cancelado con un segundo Esc sin volver a avisar (`cancel`):
    // si debía seguir abierto, se reabre.
    if (obligatorio && abierto && d && !d.open) return abrir(d);
    onCerrar();
  }

  return (
    <dialog
      ref={ref}
      onClose={alCerrarElNavegador}
      onCancel={obligatorio ? (e) => e.preventDefault() : undefined}
      onKeyDown={
        obligatorio
          ? (e) => {
              if (e.key === "Escape") {
                e.preventDefault();
                e.stopPropagation();
              }
            }
          : undefined
      }
      aria-labelledby={idTitulo}
      className="m-auto w-full max-w-md rounded-lg p-6 text-tinta backdrop:bg-tinta/50"
    >
      <h2 id={idTitulo} className="text-lg font-bold">{titulo}</h2>
      <div className="mt-2 text-sm">{children}</div>
      <div className="mt-5 flex justify-end gap-3">{acciones}</div>
    </dialog>
  );
}
