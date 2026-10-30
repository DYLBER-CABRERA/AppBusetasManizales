import Link from "next/link";

export default function NoEncontrada() {
  return (
    <main className="mx-auto max-w-xl space-y-4 p-8">
      <h1 className="text-2xl font-bold">No encontramos esta página</h1>
      <p>La dirección no existe o ya no está disponible.</p>
      <Link href="/login" className="inline-flex min-h-11 items-center rounded bg-verde px-5 font-semibold text-white hover:bg-verde-oscuro">
        Ir al inicio
      </Link>
    </main>
  );
}
