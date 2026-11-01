"use client";
import { useQueryClient } from "@tanstack/react-query";
import { useState } from "react";
import { BannerError } from "@/componentes/BannerError";
import { Esqueleto } from "@/componentes/Esqueleto";
import { Modal } from "@/componentes/Modal";
import { Vacio } from "@/componentes/Vacio";
import { useFrecuenciasDeServicio, useHorariosDeServicio, useServicios } from "@/lib/jefe";
import { etiquetaServicioTabla } from "@/lib/rodamiento";
import { BusetasConductores } from "./BusetasConductores";
import { EditorFrecuencias } from "./EditorFrecuencias";
import { EditorHorarios } from "./EditorHorarios";

type Pestana = "horarios" | "frecuencias" | "flota";
const PESTANAS: { id: Pestana; etiqueta: string }[] = [
  { id: "horarios", etiqueta: "Horarios" },
  { id: "frecuencias", etiqueta: "Frecuencias" },
  { id: "flota", etiqueta: "Busetas y conductores" },
];

export function PantallaHorarios() {
  const cliente = useQueryClient();
  const servicios = useServicios();
  const [elegido, setElegido] = useState("");
  const [pestana, setPestana] = useState<Pestana>("horarios");
  const [recarga, setRecarga] = useState(0);
  const [conflicto, setConflicto] = useState(false);

  const servicio = servicios.data?.find((s) => s.id === elegido) ?? servicios.data?.[0];
  const horarios = useHorariosDeServicio(servicio?.rutaId, servicio?.id);
  const frecuencias = useFrecuenciasDeServicio(servicio?.rutaId, servicio?.id);

  async function recargar() {
    setConflicto(false);
    await cliente.invalidateQueries({ predicate: (q) => q.queryKey[0] === "jefe" && (q.queryKey[2] === "horarios" || q.queryKey[2] === "frecuencias") });
    setRecarga((n) => n + 1);
  }

  return (
    <section className="space-y-6">
      <h1 className="text-2xl font-bold">Horarios y frecuencias</h1>

      {servicios.isError ? <BannerError mensaje={servicios.error.message} onReintentar={() => servicios.refetch()} /> : null}
      {servicios.isPending ? <Esqueleto filas={3} /> : null}

      <div role="tablist" aria-label="Secciones" className="flex gap-2">
        {PESTANAS.map((p) => (
          <button key={p.id} type="button" role="tab" id={`tab-${p.id}`} aria-selected={pestana === p.id} aria-controls={`panel-${p.id}`}
            onClick={() => setPestana(p.id)}
            className={`min-h-11 rounded px-4 font-semibold ${pestana === p.id ? "bg-verde text-white" : "border border-verde text-verde hover:bg-fondo"}`}>
            {p.etiqueta}
          </button>
        ))}
      </div>

      {pestana === "flota" ? (
        <div role="tabpanel" id="panel-flota" aria-labelledby="tab-flota"><BusetasConductores /></div>
      ) : (
        <div role="tabpanel" id={`panel-${pestana}`} aria-labelledby={`tab-${pestana}`} className="space-y-4">
          {servicios.data && servicios.data.length === 0 ? (
            <Vacio titulo="Tu empresa no tiene rutas asignadas" causa="Solo aparecen las rutas que la Secretaría asignó a tu empresa." accion={<span>Pídele a la Secretaría de Movilidad que te asigne una ruta.</span>} />
          ) : null}
          {servicio ? (
            <>
              <div>
                <label htmlFor="servicio-horarios" className="block font-semibold">Ruta</label>
                <select id="servicio-horarios" value={servicio.id} onChange={(e) => { setElegido(e.target.value); setRecarga((n) => n + 1); }}
                  className="mt-1 min-h-11 min-w-72 rounded border border-tinta/40 bg-white px-3">
                  {servicios.data?.map((s) => <option key={s.id} value={s.id}>{etiquetaServicioTabla(s)}</option>)}
                </select>
              </div>

              {pestana === "horarios" ? (
                horarios.isError ? <BannerError mensaje={horarios.error.message} onReintentar={() => horarios.refetch()} />
                : horarios.isPending ? <Esqueleto filas={4} />
                : horarios.data ? (
                  <>
                    {horarios.data.estado !== "completo" ? (
                      <p className="rounded bg-aviso p-3 text-sm">
                        Este servicio tiene el horario {horarios.data.estado === "parcial" ? "incompleto" : "pendiente"}: Información pendiente de actualización
                        {horarios.data.tiposDiaPendientes.length > 0 ? ` (${horarios.data.tiposDiaPendientes.join(", ").replaceAll("_", " ")})` : ""}.
                      </p>
                    ) : null}
                    <EditorHorarios key={`${servicio.id}-${recarga}`} servicioId={servicio.id} datos={horarios.data} onConflicto={() => setConflicto(true)} />
                  </>
                ) : <Vacio titulo="No encontramos el servicio" causa="El servicio ya no aparece en la ruta." />
              ) : frecuencias.isError ? <BannerError mensaje={frecuencias.error.message} onReintentar={() => frecuencias.refetch()} />
                : frecuencias.isPending ? <Esqueleto filas={4} />
                : frecuencias.data ? (
                  <EditorFrecuencias key={`${servicio.id}-${recarga}`} servicioId={servicio.id} datos={frecuencias.data} onConflicto={() => setConflicto(true)} />
                ) : <Vacio titulo="No encontramos el servicio" causa="El servicio ya no aparece en la ruta." />}
            </>
          ) : null}
        </div>
      )}

      <Modal abierto={conflicto} titulo="Alguien más cambió esto" onCerrar={() => setConflicto(false)}
        acciones={<button type="button" onClick={() => void recargar()} className="min-h-11 rounded bg-verde px-5 font-semibold text-white">Recargar</button>}>
        Alguien más cambió esto. Recarga para ver los cambios.
      </Modal>
    </section>
  );
}
