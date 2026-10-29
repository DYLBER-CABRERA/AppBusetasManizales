"use client";
import { useMutation, useQueryClient } from "@tanstack/react-query";
import { useState } from "react";
import { BannerError } from "@/componentes/BannerError";
import { Esqueleto } from "@/componentes/Esqueleto";
import { Modal } from "@/componentes/Modal";
import { useToast } from "@/componentes/Toast";
import { Vacio } from "@/componentes/Vacio";
import { ErrorApi, listaDeDetalles } from "@/lib/errores";
import {
  CLAVE_PARADEROS, crearParadero, editarParadero, eliminarParadero, useParaderos, type Paradero,
} from "@/lib/secretaria";
import { MapaParaderos } from "./MapaParaderos";
import type { PuntoMapa } from "./MapaParaderosInterno";

const campo = "mt-1 min-h-11 w-full rounded border border-tinta/40 bg-white px-3";
const TURNOS = "RUTAS_USAN_PARADERO";

export function PantallaParaderos() {
  const cliente = useQueryClient();
  const toast = useToast();
  const paraderos = useParaderos();

  const [editando, setEditando] = useState<Paradero | null>(null);
  const [nombre, setNombre] = useState("");
  const [direccion, setDireccion] = useState("");
  const [punto, setPunto] = useState<PuntoMapa | null>(null);
  const [errorNombre, setErrorNombre] = useState<string | null>(null);
  const [errorPunto, setErrorPunto] = useState<string | null>(null);
  const [errorServidor, setErrorServidor] = useState<string | null>(null);
  const [conflictoVersion, setConflictoVersion] = useState(false);

  const [aEliminar, setAEliminar] = useState<Paradero | null>(null);
  const [usado, setUsado] = useState<{ paradero: Paradero; rutas: string[] } | null>(null);

  function limpiar() {
    setEditando(null);
    setNombre("");
    setDireccion("");
    setPunto(null);
    setErrorNombre(null);
    setErrorPunto(null);
    setErrorServidor(null);
  }

  function elegir(p: Paradero) {
    setEditando(p);
    setNombre(p.nombre);
    setDireccion(p.direccion ?? "");
    setPunto({ lat: p.lat, lng: p.lng });
    setErrorNombre(null);
    setErrorPunto(null);
    setErrorServidor(null);
  }

  const guardar = useMutation({
    mutationFn: () => {
      const cuerpo = { nombre: nombre.trim(), lat: punto!.lat, lng: punto!.lng, direccion: direccion.trim() || null };
      return editando ? editarParadero(editando.id, { ...cuerpo, version: editando.version }) : crearParadero(cuerpo);
    },
    onSuccess: async () => {
      limpiar();
      await cliente.invalidateQueries({ queryKey: CLAVE_PARADEROS });
      toast("Guardado");
    },
    onError: (e) => {
      if (e instanceof ErrorApi && e.esConflictoVersion) return setConflictoVersion(true);
      if (e instanceof ErrorApi && e.esConflictoNegocio) {
        return setErrorServidor(`Ya existe un paradero llamado ${nombre.trim()} a menos de 20 m. Edítalo o cambia el nombre.`);
      }
      setErrorServidor(e.message);
    },
  });

  const eliminar = useMutation({
    mutationFn: async ({ p, confirmar }: { p: Paradero; confirmar: boolean }) => {
      try {
        await eliminarParadero(p.id, p.version, confirmar);
      } catch (e) {
        const rutas = listaDeDetalles(e, "rutas");
        if (e instanceof ErrorApi && e.esConflictoNegocio && !confirmar && rutas.length > 0) {
          setUsado({ paradero: p, rutas: rutas.map((r) => String(r.nombre ?? r.rutaId ?? "")) });
          throw new ErrorApi(409, TURNOS, "");
        }
        throw e;
      }
    },
    onSuccess: async () => {
      setAEliminar(null);
      setUsado(null);
      if (editando) limpiar();
      await cliente.invalidateQueries({ queryKey: CLAVE_PARADEROS });
      toast("Eliminado");
    },
    onError: (e) => {
      setAEliminar(null);
      if (e instanceof ErrorApi && e.codigo === TURNOS) return;
      setUsado(null);
      if (e instanceof ErrorApi && e.esConflictoVersion) return setConflictoVersion(true);
      setErrorServidor(e.message);
    },
  });

  function enviar(ev: React.FormEvent) {
    ev.preventDefault();
    setErrorServidor(null);
    const sinNombre = nombre.trim() === "";
    const largo = nombre.trim().length > 120;
    setErrorNombre(sinNombre ? "Escribe el nombre del paradero." : largo ? "El nombre admite hasta 120 caracteres." : null);
    setErrorPunto(punto ? null : "Toca el mapa para fijar la ubicación del paradero.");
    if (sinNombre || largo || !punto) return;
    guardar.mutate();
  }

  return (
    <section className="space-y-6">
      <h1 className="text-2xl font-bold">Paraderos</h1>

      {paraderos.isError ? <BannerError mensaje={paraderos.error.message} onReintentar={() => paraderos.refetch()} /> : null}
      {paraderos.isPending ? <Esqueleto filas={5} /> : null}

      {paraderos.data ? (
        <div className="grid gap-6 lg:grid-cols-[1fr_22rem]">
          <div>
            <MapaParaderos paraderos={paraderos.data} punto={punto} onPunto={setPunto}
              onElegir={(id) => { const p = paraderos.data.find((x) => x.id === id); if (p) elegir(p); }} />
            <p className="mt-1 text-xs">Toca el mapa para fijar la ubicación. Toca un paradero existente para editarlo.</p>
          </div>

          <form noValidate onSubmit={enviar} className="space-y-4 rounded-lg border border-borde bg-white p-5 self-start">
            <h2 className="text-lg font-bold">{editando ? `Editar ${editando.nombre}` : "Nuevo paradero"}</h2>
            <div>
              <label htmlFor="nombre-paradero" className="block font-semibold">Nombre</label>
              <input id="nombre-paradero" type="text" value={nombre} aria-invalid={!!errorNombre} className={campo}
                onChange={(e) => { setNombre(e.target.value); setErrorNombre(null); }} />
              {errorNombre ? <p className="mt-1 text-sm text-ladrillo">{errorNombre}</p> : null}
            </div>
            <div>
              <label htmlFor="direccion-paradero" className="block font-semibold">Dirección (opcional)</label>
              <input id="direccion-paradero" type="text" value={direccion} className={campo} onChange={(e) => setDireccion(e.target.value)} />
            </div>
            <p className="text-sm" aria-live="polite">
              Ubicación: {punto ? `${punto.lat.toFixed(5)}, ${punto.lng.toFixed(5)}` : "sin fijar"}
            </p>
            {errorPunto ? <p className="text-sm text-ladrillo">{errorPunto}</p> : null}
            {errorServidor ? <p role="alert" className="rounded bg-ladrillo-claro p-3 text-ladrillo">Error: {errorServidor}</p> : null}
            <div className="flex gap-3">
              <button type="submit" disabled={guardar.isPending}
                className="min-h-11 rounded bg-verde px-5 font-semibold text-white hover:bg-verde-oscuro disabled:opacity-60">
                {guardar.isPending ? "Guardando…" : "Guardar paradero"}
              </button>
              {editando || punto || nombre ? (
                <button type="button" onClick={limpiar} className="min-h-11 rounded border border-tinta px-4 font-semibold">Cancelar</button>
              ) : null}
            </div>
          </form>
        </div>
      ) : null}

      {paraderos.data && paraderos.data.length === 0 ? (
        <Vacio titulo="Todavía no hay paraderos" causa="No hay paraderos activos registrados." accion={<span>Toca el mapa y guarda el primero.</span>} />
      ) : null}

      {paraderos.data && paraderos.data.length > 0 ? (
        <div className="overflow-x-auto rounded-lg border border-borde bg-white">
          <table className="w-full text-left">
            <caption className="sr-only">Paraderos activos</caption>
            <thead className="bg-fondo text-sm">
              <tr>
                <th scope="col" className="p-3">Nombre</th>
                <th scope="col" className="p-3">Ubicación</th>
                <th scope="col" className="p-3"><span className="sr-only">Acciones</span></th>
              </tr>
            </thead>
            <tbody>
              {paraderos.data.map((p) => (
                <tr key={p.id} className="border-t border-borde">
                  <td className="p-3 font-semibold">{p.nombre}</td>
                  <td className="p-3 text-sm">{p.lat.toFixed(5)}, {p.lng.toFixed(5)}</td>
                  <td className="p-3 text-right">
                    <button type="button" onClick={() => elegir(p)} aria-label={`Editar ${p.nombre}`}
                      className="mr-2 min-h-11 rounded border border-verde px-4 font-semibold text-verde hover:bg-fondo">Editar</button>
                    <button type="button" onClick={() => setAEliminar(p)} aria-label={`Eliminar ${p.nombre}`}
                      className="min-h-11 rounded border border-ladrillo px-4 font-semibold text-ladrillo hover:bg-ladrillo-claro">Eliminar</button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      ) : null}

      <Modal abierto={aEliminar !== null} titulo="Eliminar paradero" onCerrar={() => setAEliminar(null)}
        acciones={
          <>
            <button type="button" onClick={() => setAEliminar(null)} className="min-h-11 rounded border border-tinta px-5 font-semibold">Cancelar</button>
            <button type="button" disabled={eliminar.isPending}
              onClick={() => aEliminar && eliminar.mutate({ p: aEliminar, confirmar: false })}
              className="min-h-11 rounded bg-ladrillo px-5 font-semibold text-white">Eliminar</button>
          </>
        }>
        ¿Eliminar el paradero «{aEliminar?.nombre}»?
      </Modal>

      <Modal abierto={usado !== null} titulo="Paradero en uso" onCerrar={() => setUsado(null)}
        acciones={
          <>
            <button type="button" onClick={() => setUsado(null)} className="min-h-11 rounded border border-tinta px-5 font-semibold">Cancelar</button>
            <button type="button" disabled={eliminar.isPending}
              onClick={() => usado && eliminar.mutate({ p: usado.paradero, confirmar: true })}
              className="min-h-11 rounded bg-ladrillo px-5 font-semibold text-white">Confirmar</button>
          </>
        }>
        <p className="mb-2">«{usado?.paradero.nombre}» lo usan estas rutas:</p>
        <ul className="mb-2 list-disc pl-5">{usado?.rutas.map((r, i) => <li key={i}>{r}</li>)}</ul>
        <p>Al darlo de baja no se quita de esas rutas. Edítalas después para cambiar su recorrido.</p>
      </Modal>

      <Modal abierto={conflictoVersion} titulo="Alguien más cambió esto" onCerrar={() => setConflictoVersion(false)}
        acciones={
          <button type="button" className="min-h-11 rounded bg-verde px-5 font-semibold text-white"
            onClick={() => { setConflictoVersion(false); limpiar(); void paraderos.refetch(); }}>Recargar</button>
        }>
        Alguien más cambió esto. Recarga para ver los cambios.
      </Modal>
    </section>
  );
}
