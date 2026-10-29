/** Error de red/servidor: banner rojo con Reintentar; el contenido ya cargado se conserva en la pantalla. */
export function BannerError({ mensaje, onReintentar }: { mensaje: string; onReintentar?: () => void }) {
  return (
    <div role="alert" className="flex items-center justify-between gap-4 rounded-lg bg-ladrillo px-4 py-3 text-white">
      <span>{mensaje}</span>
      {onReintentar ? (
        <button
          type="button"
          onClick={onReintentar}
          className="min-h-11 rounded border border-white px-4 font-semibold hover:bg-white/15"
        >
          Reintentar
        </button>
      ) : null}
    </div>
  );
}
