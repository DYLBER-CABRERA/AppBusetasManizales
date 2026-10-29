"use client";
import { zodResolver } from "@hookform/resolvers/zod";
import { useMutation, useQueryClient } from "@tanstack/react-query";
import Link from "next/link";
import { useSearchParams } from "next/navigation";
import { useState } from "react";
import { useForm } from "react-hook-form";
import { z } from "zod";
import { BannerError } from "@/componentes/BannerError";
import { Esqueleto } from "@/componentes/Esqueleto";
import { Modal } from "@/componentes/Modal";
import { useToast } from "@/componentes/Toast";
import { Vacio } from "@/componentes/Vacio";
import { ErrorApi } from "@/lib/errores";
import { DIAS_MAX_RODAMIENTO_ADELANTE, hoyBogota, minutos, sumarDias } from "@/lib/fechas";
import {
  buscarRodamiento, crearRodamiento, guardarTurnos, useBusetas, useClaveEmpresa, useConductores, useServicios,
} from "@/lib/jefe";
import {
  etiquetaServicioSelector, frasesDeReemplazo, textoSolapamientos, turnoAEntrada, turnosVigentes,
  type TurnoEntrada,
} from "@/lib/rodamiento";

const esquema = z
  .object({
    fecha: z.string().min(1, "Elige la fecha del rodamiento."),
    servicioId: z.string().min(1, "Elige una ruta."),
    busetaId: z.string().min(1, "Elige una buseta."),
    conductorId: z.string().min(1, "Elige un conductor."),
    horaSalida: z.string().min(1, "Escribe la hora de salida."),
    horaFin: z.string().min(1, "Escribe la hora de fin."),
  })
  .refine((d) => !d.horaSalida || !d.horaFin || minutos(d.horaFin) > minutos(d.horaSalida), {
    path: ["horaFin"],
    message: "El fin debe ser posterior a la salida.",
  });
type Datos = z.infer<typeof esquema>;

type Pendiente = { rodamientoId: string; version: number; turnos: TurnoEntrada[]; frases: string[] };

const campo = "mt-1 min-h-11 w-full rounded border border-tinta/40 bg-white px-3";
const mensajeError = "mt-1 text-sm text-ladrillo";

export function PantallaAsignar() {
  const params = useSearchParams();
  const cliente = useQueryClient();
  const toast = useToast();
  const clave = useClaveEmpresa();
  const hoy = hoyBogota();
  const maxima = sumarDias(hoy, DIAS_MAX_RODAMIENTO_ADELANTE);
  const pedida = params.get("fecha");
  const fechaInicial = pedida && pedida >= hoy && pedida <= maxima ? pedida : sumarDias(hoy, 1);

  const servicios = useServicios();
  const busetas = useBusetas();
  const conductores = useConductores();

  const [pendiente, setPendiente] = useState<Pendiente | null>(null);
  const [modalVersion, setModalVersion] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [guardado, setGuardado] = useState<{ fecha: string; solapamientos: number } | null>(null);

  const { register, handleSubmit, reset, getValues, formState: { errors } } = useForm<Datos>({
    resolver: zodResolver(esquema),
    defaultValues: { fecha: fechaInicial, servicioId: "", busetaId: "", conductorId: "", horaSalida: "", horaFin: "" },
  });

  const enviar = useMutation({
    mutationFn: async ({ d, confirmar }: { d: Datos; confirmar: boolean }) => {
      const nuevo: TurnoEntrada = {
        servicioId: d.servicioId, busetaId: d.busetaId, conductorId: d.conductorId,
        horaSalida: d.horaSalida, horaFinEstimada: d.horaFin,
      };
      const existente = await buscarRodamiento(d.fecha);
      if (!existente) return crearRodamiento({ fecha: d.fecha, turnos: [nuevo] });
      if (existente.estado !== "borrador") {
        throw new ErrorApi(409, "CONFLICTO_NEGOCIO", "El rodamiento de esta fecha ya está publicado y no se puede cambiar.");
      }
      const vigentes = turnosVigentes(existente);
      // Un turno con la misma ruta y hora de salida se reemplaza, no se duplica.
      const turnos = [
        ...vigentes.filter((t) => !(t.servicioId === nuevo.servicioId && t.horaSalida.slice(0, 5) === nuevo.horaSalida)).map(turnoAEntrada),
        nuevo,
      ];
      try {
        return await guardarTurnos(existente.rodamientoId, { turnos, version: existente.version, confirmarReemplazo: confirmar });
      } catch (e) {
        if (e instanceof ErrorApi && e.esConflictoNegocio) {
          const frases = frasesDeReemplazo(vigentes, [nuevo], { busetas: busetas.data ?? [], conductores: conductores.data ?? [] });
          if (frases.length > 0) {
            setPendiente({ rodamientoId: existente.rodamientoId, version: existente.version, turnos, frases });
            throw new ErrorApi(409, "REEMPLAZO_PENDIENTE", "");
          }
        }
        throw e;
      }
    },
    onSuccess: async (r) => {
      setPendiente(null);
      setError(null);
      setGuardado({ fecha: r.fecha, solapamientos: r.advertencias.length });
      await cliente.invalidateQueries({ queryKey: ["jefe", clave, "rodamiento"] });
      toast("Guardado");
      reset({ ...getValues(), horaSalida: "", horaFin: "" });
    },
    onError: (e) => {
      if (e instanceof ErrorApi && e.codigo === "REEMPLAZO_PENDIENTE") return;
      if (e instanceof ErrorApi && e.esConflictoVersion) return setModalVersion(true);
      setError(e instanceof Error ? e.message : "No se pudo guardar la asignación.");
    },
  });

  const reemplazar = useMutation({
    mutationFn: (p: Pendiente) =>
      guardarTurnos(p.rodamientoId, { turnos: p.turnos, version: p.version, confirmarReemplazo: true }),
    onSuccess: async (r) => {
      setPendiente(null);
      setError(null);
      setGuardado({ fecha: r.fecha, solapamientos: r.advertencias.length });
      await cliente.invalidateQueries({ queryKey: ["jefe", clave, "rodamiento"] });
      toast("Guardado");
      reset({ ...getValues(), horaSalida: "", horaFin: "" });
    },
    onError: (e) => {
      setPendiente(null);
      if (e instanceof ErrorApi && e.esConflictoVersion) return setModalVersion(true);
      setError(e instanceof Error ? e.message : "No se pudo reemplazar la asignación.");
    },
  });

  const consultas = [servicios, busetas, conductores];
  const fallo = consultas.find((c) => c.isError)?.error;
  const cargando = consultas.some((c) => c.isPending);

  return (
    <section className="max-w-xl">
      <h1 className="mb-4 text-2xl font-bold">Asignar buseta y conductor</h1>

      {fallo ? (
        <div className="mb-4">
          <BannerError mensaje={fallo.message} onReintentar={() => consultas.forEach((c) => void c.refetch())} />
        </div>
      ) : null}
      {cargando && !fallo ? <Esqueleto filas={5} /> : null}

      {servicios.data && servicios.data.length === 0 ? (
        <Vacio
          titulo="Tu empresa no tiene rutas asignadas"
          causa="Solo aparecen las rutas que la Secretaría asignó a tu empresa."
          accion={<span>Pídele a la Secretaría de Movilidad que te asigne una ruta.</span>}
        />
      ) : null}

      {servicios.data && servicios.data.length > 0 && busetas.data && conductores.data ? (
        <form
          noValidate
          onSubmit={handleSubmit((d) => { setGuardado(null); setError(null); enviar.mutate({ d, confirmar: false }); })}
          className="space-y-4 rounded-lg bg-white p-6"
        >
          <div>
            <label htmlFor="fecha" className="block font-semibold">Fecha del rodamiento</label>
            <input id="fecha" type="date" min={hoy} max={maxima} className={campo} {...register("fecha")} />
            {errors.fecha ? <p className={mensajeError}>{errors.fecha.message}</p> : null}
          </div>
          <div>
            <label htmlFor="servicioId" className="block font-semibold">Ruta</label>
            <select id="servicioId" className={campo} {...register("servicioId")}>
              <option value="">Elige una ruta</option>
              {servicios.data.map((s) => <option key={s.id} value={s.id}>{etiquetaServicioSelector(s)}</option>)}
            </select>
            <p className="mt-1 text-sm">Solo aparecen las rutas que la Secretaría asignó a tu empresa.</p>
            {errors.servicioId ? <p className={mensajeError}>{errors.servicioId.message}</p> : null}
          </div>
          <div>
            <label htmlFor="busetaId" className="block font-semibold">Buseta (número lateral)</label>
            <select id="busetaId" className={campo} {...register("busetaId")}>
              <option value="">Elige una buseta</option>
              {busetas.data.map((b) => <option key={b.id} value={b.id}>{b.numeroLateral}</option>)}
            </select>
            {errors.busetaId ? <p className={mensajeError}>{errors.busetaId.message}</p> : null}
          </div>
          <div>
            <label htmlFor="conductorId" className="block font-semibold">Conductor</label>
            <select id="conductorId" className={campo} {...register("conductorId")}>
              <option value="">Elige un conductor</option>
              {conductores.data.map((c) => <option key={c.id} value={c.id}>{c.nombre}</option>)}
            </select>
            {errors.conductorId ? <p className={mensajeError}>{errors.conductorId.message}</p> : null}
          </div>
          <div className="flex gap-4">
            <div className="flex-1">
              <label htmlFor="horaSalida" className="block font-semibold">Salida</label>
              <input id="horaSalida" type="time" className={campo} {...register("horaSalida")} />
              {errors.horaSalida ? <p className={mensajeError}>{errors.horaSalida.message}</p> : null}
            </div>
            <div className="flex-1">
              <label htmlFor="horaFin" className="block font-semibold">Fin estimado</label>
              <input id="horaFin" type="time" className={campo} {...register("horaFin")} />
              {errors.horaFin ? <p className={mensajeError}>{errors.horaFin.message}</p> : null}
            </div>
          </div>

          {error ? <p role="alert" className="rounded bg-ladrillo-claro p-3 text-ladrillo">Error: {error}</p> : null}
          {guardado ? (
            <p role="status" className="rounded bg-aviso p-3">
              Turno agregado al borrador.{" "}
              {guardado.solapamientos > 0 ? `${textoSolapamientos(guardado.solapamientos)} Corrígelo en el rodamiento. ` : ""}
              <Link href={`/jefe/rodamiento?fecha=${guardado.fecha}`} className="font-semibold text-verde underline">
                Ver rodamiento
              </Link>
            </p>
          ) : null}

          <button type="submit" disabled={enviar.isPending}
            className="min-h-11 w-full rounded bg-verde font-semibold text-white hover:bg-verde-oscuro disabled:opacity-60">
            {enviar.isPending ? "Guardando…" : "Guardar asignación"}
          </button>
          <p className="text-sm">Una buseta puede tener varias rutas en el día.</p>
        </form>
      ) : null}

      <Modal abierto={pendiente !== null} titulo="Reemplazar asignación" onCerrar={() => setPendiente(null)}
        acciones={
          <>
            <button type="button" onClick={() => setPendiente(null)}
              className="min-h-11 rounded border border-tinta px-5 font-semibold">Cancelar</button>
            <button type="button" disabled={reemplazar.isPending} onClick={() => pendiente && reemplazar.mutate(pendiente)}
              className="min-h-11 rounded bg-verde px-5 font-semibold text-white">Reemplazar</button>
          </>
        }>
        {pendiente?.frases.map((f, i) => <p key={i} className="mb-2">{f}</p>)}
      </Modal>

      <Modal abierto={modalVersion} titulo="Alguien más cambió esto" onCerrar={() => setModalVersion(false)}
        acciones={<button type="button" onClick={() => setModalVersion(false)}
          className="min-h-11 rounded bg-verde px-5 font-semibold text-white">Recargar</button>}>
        Alguien más cambió esto. Recarga para ver los cambios. Vuelve a guardar la asignación.
      </Modal>
    </section>
  );
}
