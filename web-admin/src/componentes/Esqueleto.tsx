export function Esqueleto({ filas = 4 }: { filas?: number }) {
  return (
    <div role="status" aria-label="Cargando" className="space-y-3">
      {Array.from({ length: filas }, (_, i) => (
        <div key={i} className="h-10 animate-pulse rounded bg-borde/60" />
      ))}
      <span className="sr-only">Cargando…</span>
    </div>
  );
}
