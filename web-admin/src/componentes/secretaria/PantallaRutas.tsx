"use client";
import { useMutation, useQueryClient } from "@tanstack/react-query";
import { useState } from "react";
import { BannerError } from "@/componentes/BannerError";
import { Esqueleto } from "@/componentes/Esqueleto";
import { Modal } from "@/componentes/Modal";
import { useToast } from "@/componentes/Toast";
import { Vacio } from "@/componentes/Vacio";
import { ErrorApi, listaDeDetalles } from "@/lib/errores";
import { useEmpresasPublicas } from "@/lib/jefe";
import {
  CLAVE_RUTAS, detalleRuta, eliminarRuta, retirarServicio, useDetalleRuta, useParaderos, useRutas, versionDeServicio,
  type RutaResumen,
} from "@/lib/secretaria";
import { FormularioRuta } from "./FormularioRuta";
import { TarjetaRuta } from "./TarjetaRuta";

type Servicio = RutaResumen["servicios"][number];
type Objetivo = { clase: "ruta"; ruta: RutaResumen } | { clase: "servicio"; ruta: RutaResumen; servicio: Servicio };
type Futuros = { objetivo: Objetivo; version: number; turnos: Record<string, unknown>[] };

const TURNOS_FUTUROS = "TURNOS_FUTUROS";

export function PantallaRutas() {
  const cliente = useQueryClient();
  const toast = useToast();
  const rutas = useRutas();
  const paraderos = useParaderos();
  const empresas = useEmpresasPublicas();

  const [nueva, setNueva] = useState(false);
  const [editarId, setEditarId] = useState<string | null>(null);
  const [recarga, setRecarga] = useState(0);
  const detalle = useDetalleRuta(editarId);

  const [objetivo, setObjetivo] = useState<Objetivo | null>(null);
  const [futuros, setFuturos] = useState<Futuros | null>(null);
  const [errorAccion, setErrorAccion] = useState<string | null>(null);
  const [conflictoVersion, setConflictoVersion] = useState(false);

  const eliminar = useMutation({
    mutationFn: async ({ destino, confirmar, version }: { destino: Objetivo; confirmar: boolean; version?: number }) => {
      let v = version;
      if (v === undefined) {
        v = destino.clase === "ruta"
          ? (await detalleRuta(destino.ruta.id)).version
          : await versionDeServicio(destino.ruta.id, destino.servicio.servicioId);
      }
      if (v === undefined) throw new ErrorApi(404, "NO_ENCONTRADO", "No encontramos esa empresa en la ruta.");
      try {
        if (destino.clase === "ruta") await eliminarRuta(destino.ruta.id, v, confirmar);
        else await retirarServicio(destino.servicio.servicioId, v, confirmar);
      } catch (e) {
        const turnos = listaDeDetalles(e, "turnosFuturos");
        if (e instanceof ErrorApi && e.esConflictoNegocio && !confirmar && turnos.length > 0) {
          setFuturos({ objetivo: destino, version: v, turnos });
          throw new ErrorApi(409, TURNOS_FUTUROS, "");
        }
        throw e;
      }
      return destino;
    },
    onSuccess: async (destino) => {
      setObjetivo(null);
      setFuturos(null);
      setErrorAccion(null);
      await cliente.invalidateQueries({ queryKey: CLAVE_RUTAS });
      toast(destino.clase === "ruta" ? "Eliminada" : "Retirada");
    },
    onError: (e) => {
      setObjetivo(null);
      if (e instanceof ErrorApi && e.codigo === TURNOS_FUTUROS) return;
      setFuturos(null);
      if (e instanceof ErrorApi && e.esConflictoVersion) return setConflictoVersion(true);
      setErrorAccion(e.message);
    },
  });

  const cargando = rutas.isPending || paraderos.isPending || empresas.isPending;
  const fallo = [rutas, paraderos, empresas].find((q) => q.isError)?.error;
  const hayDatos = rutas.data && paraderos.data && empresas.data;

  const nombreObjetivo = (o: Objetivo) => o.ruta.nombre;
  const verboModal1 = objetivo?.clase === "servicio" ? "Quitar" : "Eliminar";

  return (
    <section className="space-y-6">
      <div className="flex items-center justify-between gap-4">
        <h1 className="text-2xl font-bold">Rutas</h1>
        {!nueva && editarId === null ? (
          <button type="button" onClick={() => setNueva(true)}
            className="min-h-11 rounded bg-verde px-5 font-semibold text-white hover:bg-verde-oscuro">
            Registrar ruta
          </button>
        ) : null}
      </div>

      {fallo ? (
        <BannerError mensaje={fallo.message} onReintentar={() => [rutas, paraderos, empresas].forEach((q) => void q.refetch())} />
      ) : null}
      {errorAccion ? <p role="alert" className="rounded bg-ladrillo-claro p-3 text-ladrillo">Error: {errorAccion}</p> : null}
      {cargando && !fallo ? <Esqueleto filas={5} /> : null}

      {hayDatos && nueva ? (
        <FormularioRuta paraderos={paraderos.data} empresas={empresas.data} rutas={rutas.data}
          onListo={() => setNueva(false)} onCancelar={() => setNueva(false)} onConflictoVersion={() => {}} />
      ) : null}

      {hayDatos && editarId !== null ? (
        detalle.data ? (
          <FormularioRuta key={`${editarId}-${recarga}`} ruta={detalle.data} paraderos={paraderos.data}
            empresas={empresas.data} rutas={rutas.data}
            onListo={() => setEditarId(null)} onCancelar={() => setEditarId(null)}
            onConflictoVersion={() => setConflictoVersion(true)} />
        ) : detalle.isError ? (
          <BannerError mensaje={detalle.error.message} onReintentar={() => detalle.refetch()} />
        ) : (
          <Esqueleto filas={4} />
        )
      ) : null}

      {hayDatos && rutas.data.length === 0 ? (
        <Vacio titulo="Todavía no hay rutas" causa="Aún no se ha registrado ninguna ruta activa."
          accion={<span>Usa «Registrar ruta» para crear la primera.</span>} />
      ) : null}

      {hayDatos ? (
        <div className="grid gap-4 xl:grid-cols-2">
          {rutas.data.map((r) => (
            <TarjetaRuta key={r.id} ruta={r} empresas={empresas.data}
              onEditar={() => { setNueva(false); setEditarId(r.id); }}
              onEliminar={() => setObjetivo({ clase: "ruta", ruta: r })}
              onQuitarServicio={(s) => setObjetivo({ clase: "servicio", ruta: r, servicio: s })} />
          ))}
        </div>
      ) : null}

      <Modal abierto={objetivo !== null} titulo={objetivo?.clase === "servicio" ? "Quitar empresa" : "Eliminar ruta"}
        onCerrar={() => setObjetivo(null)}
        acciones={
          <>
            <button type="button" onClick={() => setObjetivo(null)} className="min-h-11 rounded border border-tinta px-5 font-semibold">Cancelar</button>
            <button type="button" disabled={eliminar.isPending}
              onClick={() => objetivo && eliminar.mutate({ destino: objetivo, confirmar: false })}
              className="min-h-11 rounded bg-ladrillo px-5 font-semibold text-white">{verboModal1}</button>
          </>
        }>
        {objetivo?.clase === "servicio"
          ? `¿Quitar a ${objetivo.servicio.empresaNombre} de la ruta «${nombreObjetivo(objetivo)}»? Esa empresa dejará de operarla.`
          : objetivo ? `¿Eliminar la ruta «${nombreObjetivo(objetivo)}»? Dejará de verse para los pasajeros.` : null}
      </Modal>

      <Modal abierto={futuros !== null} titulo="Turnos futuros" onCerrar={() => setFuturos(null)}
        acciones={
          <>
            <button type="button" onClick={() => setFuturos(null)} className="min-h-11 rounded border border-tinta px-5 font-semibold">Cancelar</button>
            <button type="button" disabled={eliminar.isPending}
              onClick={() => futuros && eliminar.mutate({ destino: futuros.objetivo, confirmar: true, version: futuros.version })}
              className="min-h-11 rounded bg-ladrillo px-5 font-semibold text-white">Confirmar</button>
          </>
        }>
        <p className="mb-2">
          {futuros?.objetivo.clase === "servicio" ? "El servicio" : "La ruta"} tiene turnos futuros programados:
        </p>
        <ul className="mb-2 max-h-40 list-disc overflow-y-auto pl-5">
          {futuros?.turnos.map((t, i) => (
            <li key={i}>{String(t.fecha ?? "")} · {String(t.horaSalida ?? "").slice(0, 5)} · buseta {String(t.buseta ?? "")}</li>
          ))}
        </ul>
        <p className="font-semibold">Al eliminarla se cancelan los turnos futuros.</p>
      </Modal>

      <Modal abierto={conflictoVersion} titulo="Alguien más cambió esto" onCerrar={() => setConflictoVersion(false)}
        acciones={
          <button type="button" className="min-h-11 rounded bg-verde px-5 font-semibold text-white"
            onClick={async () => {
              setConflictoVersion(false);
              await Promise.all([cliente.invalidateQueries({ queryKey: CLAVE_RUTAS }), detalle.refetch()]);
              setRecarga((n) => n + 1);
            }}>
            Recargar
          </button>
        }>
        Alguien más cambió esto. Recarga para ver los cambios.
      </Modal>
    </section>
  );
}
