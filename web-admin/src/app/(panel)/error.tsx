"use client";

/** Fallo de render dentro del panel: conserva el menú lateral y ofrece reintentar. */
export default function ErrorPanel({ reset }: { error: Error & { digest?: string }; reset: () => void }) {
  return (
    <section className="space-y-4">
      <h1 className="text-2xl font-bold">Algo salió mal</h1>
      <p role="alert" className="rounded bg-ladrillo-claro p-3 text-ladrillo">
        Error: esta sección no se pudo mostrar. Tus datos guardados no se perdieron.
      </p>
      <button type="button" onClick={reset} className="min-h-11 rounded bg-verde px-5 font-semibold text-white hover:bg-verde-oscuro">
        Intentar de nuevo
      </button>
    </section>
  );
}
