"use client";
import { useState } from "react";
import { BannerError } from "@/componentes/BannerError";
import { Esqueleto } from "@/componentes/Esqueleto";
import { useToast } from "@/componentes/Toast";
import { textoCoordenadas } from "@/lib/puntos-ruta";
import { useDetalleRuta } from "@/lib/secretaria";
import { MapaVistaRuta } from "./MapaVistaRuta";

/** Vista de solo lectura de una ruta: trazado real en el mapa, paraderos en orden (con coordenadas) y datos generales. */
export function VistaRuta({ rutaId, onCerrar }: { rutaId: string; onCerrar: () => void }) {
  const detalle = useDetalleRuta(rutaId);
  const ruta = detalle.data;
  const toast = useToast();
  const [seleccionado, setSeleccionado] = useState<{ id: string; clave: number } | null>(null);
  const paradas = ruta ? [...ruta.paraderos].sort((a, b) => a.orden - b.orden) : [];

  /** Una línea por paradero, «lat, lng, nombre»: se puede pegar tal cual en «Agregar por coordenadas». */
  async function copiarCoordenadas() {
    const texto = paradas.map((p) => `${textoCoordenadas(p.lat, p.lng)}, ${p.nombre}`).join("\n");
    try {
      await navigator.clipboard.writeText(texto);
      toast("Coordenadas copiadas");
    } catch {
      toast("No se pudo copiar. Selecciona las coordenadas de la lista y cópialas a mano.");
    }
  }

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
            <MapaVistaRuta ruta={ruta} alto={460} seleccionado={seleccionado} />
            <p className="mt-1 text-xs">
              Línea azul: trazado de la ruta (circular, vuelve al primer paradero). Círculos verdes numerados: paraderos en orden.
              Toca un paradero para ver su latitud y longitud.
            </p>
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
              <div className="flex flex-wrap items-center justify-between gap-2">
                <h3 className="font-semibold">Paraderos ({ruta.paraderos.length})</h3>
                {ruta.paraderos.length > 0 ? (
                  <button type="button" onClick={copiarCoordenadas}
                    className="min-h-11 rounded border border-tinta/40 px-3 text-sm font-semibold hover:bg-fondo">
                    Copiar coordenadas
                  </button>
                ) : null}
              </div>
              <p className="text-xs">Toca un paradero para verlo en el mapa. Las coordenadas son latitud, longitud.</p>
              <ol className="mt-1 max-h-72 space-y-1 overflow-y-auto">
                {paradas.map((p) => (
                  <li key={p.paraderoId}>
                    <button type="button" onClick={() => setSeleccionado({ id: p.paraderoId, clave: Date.now() })}
                      aria-pressed={seleccionado?.id === p.paraderoId}
                      className={`flex min-h-11 w-full gap-2 rounded px-3 py-1 text-left text-sm hover:bg-borde ${seleccionado?.id === p.paraderoId ? "bg-borde" : "bg-fondo"}`}>
                      <span className="w-6 shrink-0 text-right font-bold">{p.orden}.</span>
                      <span className="flex-1">
                        <span className="block">{p.nombre}</span>
                        <span className="block font-mono text-xs">{textoCoordenadas(p.lat, p.lng)}</span>
                      </span>
                    </button>
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
