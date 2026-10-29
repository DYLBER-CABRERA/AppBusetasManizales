import type { ReactNode } from "react";

/** Estado vacío: título + causa + siguiente paso. */
export function Vacio({ titulo, causa, accion }: { titulo: string; causa: string; accion?: ReactNode }) {
  return (
    <div className="rounded-lg border border-dashed border-borde bg-white p-8 text-center">
      <h2 className="text-lg font-bold">{titulo}</h2>
      <p className="mt-1 text-sm">{causa}</p>
      {accion ? <div className="mt-4">{accion}</div> : null}
    </div>
  );
}
