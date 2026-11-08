"use client";
import { BannerError } from "@/componentes/BannerError";
import { Esqueleto } from "@/componentes/Esqueleto";
import { useDetalleRuta } from "@/lib/secretaria";
import { MapaVistaRuta } from "./MapaVistaRuta";

/** Vista de solo lectura de una ruta: trazado real en el mapa, paraderos en orden y datos generales. */
export function VistaRuta({ rutaId, onCerrar }: { rutaId: string; onCerrar: () => void }) {
  const detalle = useDetalleRuta(rutaId);
  const ruta = detalle.data;

  return (
    <section aria-label="Detalle de la ruta" className="space-y-4 rounded-lg border border-borde bg-white p-6">
      <div className="flex flex-wrap items-start justify-between gap-3">
        <h2 className="text-xl font-bold">{ruta ? `Ruta ${ruta.nombre}` : "Ruta"}</h2>
        <button type="button" onClick={onCerrar} className="min-h-11 rounded border border-tinta px-5 font-semibold">Cerrar</button>
      </div>

      {detalle.isError ? <BannerError mensaje={detalle.error.message} onReintentar={() => detalle.refetch()} /> : null}
      {detalle.isPending ? <Esqueleto filas={6} /> : null}

      {ruta ? (
        <div className="grid gap-4 lg:grid-cols-[2fr_1fr]">
          <div>
            <MapaVistaRuta ruta={ruta} alto={460} />
            <p className="mt-1 text-xs">Línea azul: trazado de la ruta (circular, vuelve al primer paradero). Círculos verdes numerados: paraderos en orden.</p>
          </div>
          <div className="space-y-4">
            <dl className="space-y-1 text-sm">
              <div className="flex gap-2"><dt className="font-semibold">Nombre:</dt><dd>{ruta.nombre}{ruta.esVariante ? " (variante)" : ""}</dd></div>
              <div className="flex gap-2"><dt className="font-semibold">Recorrido:</dt><dd>Circular</dd></div>
              <div className="flex gap-2">
                <dt className="font-semibold">Longitud:</dt>
                <dd>{ruta.longitudM != null ? `${(ruta.longitudM / 1000).toFixed(1)} km` : "Sin dato"}</dd>
              </div>
              {ruta.descripcion ? <div className="flex gap-2"><dt className="font-semibold">Descripción:</dt><dd>{ruta.descripcion}</dd></div> : null}
            </dl>
            <div>
              <h3 className="font-semibold">Empresas y servicios</h3>
              {ruta.servicios.length === 0 ? (
                <p className="text-sm">Ninguna empresa opera esta ruta.</p>
              ) : (
                <ul className="mt-1 space-y-1">
                  {ruta.servicios.map((s) => (
                    <li key={s.servicioId} className="rounded bg-fondo px-3 py-1 text-sm">
                      {s.empresaNombre} · código {s.codigoPublico ?? "sin código"}
                    </li>
                  ))}
                </ul>
              )}
            </div>
            <div>
              <h3 className="font-semibold">Paraderos ({ruta.paraderos.length})</h3>
              <ol className="mt-1 max-h-64 space-y-1 overflow-y-auto">
                {[...ruta.paraderos].sort((a, b) => a.orden - b.orden).map((p) => (
                  <li key={p.paraderoId} className="flex gap-2 rounded bg-fondo px-3 py-1 text-sm">
                    <span className="w-6 text-right font-bold">{p.orden}.</span>
                    <span>{p.nombre}</span>
                  </li>
                ))}
              </ol>
            </div>
          </div>
        </div>
      ) : null}
    </section>
  );
}
