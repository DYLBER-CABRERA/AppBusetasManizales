import { Vacio } from "./Vacio";

/** Marcador de pantallas que aún no se construyen (se reemplaza en W1–W4). */
export function PantallaPendiente({ titulo, bloque }: { titulo: string; bloque: string }) {
  return (
    <section>
      <h1 className="mb-4 text-2xl font-bold">{titulo}</h1>
      <Vacio titulo="Pantalla en construcción" causa={`Se construye en el bloque ${bloque}.`} />
    </section>
  );
}
