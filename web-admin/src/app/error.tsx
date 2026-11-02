"use client";

/** Último recurso: un fallo inesperado de render no deja la pantalla en blanco. */
export default function ErrorGlobal({ reset }: { error: Error & { digest?: string }; reset: () => void }) {
  return (
    <main className="mx-auto max-w-xl space-y-4 p-8">
      <h1 className="text-2xl font-bold">Algo salió mal</h1>
      <p role="alert" className="rounded bg-ladrillo-claro p-3 text-ladrillo">
        Error: la pantalla no se pudo mostrar. Tus datos guardados no se perdieron.
      </p>
      <button type="button" onClick={reset} className="min-h-11 rounded bg-verde px-5 font-semibold text-white hover:bg-verde-oscuro">
        Intentar de nuevo
      </button>
    </main>
  );
}
