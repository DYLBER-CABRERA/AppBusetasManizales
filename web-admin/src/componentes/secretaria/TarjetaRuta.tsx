"use client";
import { useMutation, useQueryClient } from "@tanstack/react-query";
import { useState } from "react";
import { Modal } from "@/componentes/Modal";
import { useToast } from "@/componentes/Toast";
import { ErrorApi } from "@/lib/errores";
import { asignarServicio, CLAVE_RUTAS, type Empresa, type RutaResumen } from "@/lib/secretaria";

type Servicio = RutaResumen["servicios"][number];

type Props = {
  ruta: RutaResumen;
  empresas: Empresa[];
  onEditar: () => void;
  onEliminar: () => void;
  onQuitarServicio: (s: Servicio) => void;
};

const boton = "min-h-11 rounded border border-verde px-4 font-semibold text-verde hover:bg-fondo";

export function TarjetaRuta({ ruta, empresas, onEditar, onEliminar, onQuitarServicio }: Props) {
  const cliente = useQueryClient();
  const toast = useToast();
  const [asignando, setAsignando] = useState(false);
  const [empresaId, setEmpresaId] = useState("");
  const [codigo, setCodigo] = useState("");
  const [compartida, setCompartida] = useState(false);
  const [errorServidor, setErrorServidor] = useState<string | null>(null);

  const libres = empresas.filter((e) => !ruta.servicios.some((s) => s.empresaId === e.id));

  const asignar = useMutation({
    mutationFn: (confirmar: boolean) =>
      asignarServicio(ruta.id, { empresaId, codigoPublico: codigo.trim() || null, confirmarCompartida: confirmar }),
    onSuccess: async () => {
      setCompartida(false);
      setAsignando(false);
      setEmpresaId("");
      setCodigo("");
      setErrorServidor(null);
      await cliente.invalidateQueries({ queryKey: CLAVE_RUTAS });
      toast("Asignada");
    },
    onError: (e, confirmar) => {
      // La ruta siempre tiene ya una empresa: sin confirmar, el 409 es el aviso de ruta compartida.
      if (e instanceof ErrorApi && e.esConflictoNegocio && !confirmar) return setCompartida(true);
      setCompartida(false);
      setErrorServidor(e.message);
    },
  });

  return (
    <article className="rounded-lg border border-borde bg-white p-5" aria-labelledby={`ruta-${ruta.id}`}>
      <div className="flex flex-wrap items-start justify-between gap-3">
        <div>
          <h3 id={`ruta-${ruta.id}`} className="text-lg font-bold">
            {ruta.nombre}
            {ruta.esVariante ? <span className="ml-2 text-sm font-normal">(variante)</span> : null}
          </h3>
          <p className="text-sm">Recorrido circular</p>
        </div>
        <div className="flex flex-wrap gap-2">
          <button type="button" className={boton} onClick={onEditar} aria-label={`Editar ${ruta.nombre}`}>Editar</button>
          <button type="button" className={boton} onClick={() => setAsignando((a) => !a)} aria-expanded={asignando}>
            Asignar empresa
          </button>
          <button type="button" onClick={onEliminar} aria-label={`Eliminar ${ruta.nombre}`}
            className="min-h-11 rounded border border-ladrillo px-4 font-semibold text-ladrillo hover:bg-ladrillo-claro">
            Eliminar
          </button>
        </div>
      </div>

      <ul className="mt-3 flex flex-wrap gap-2" aria-label={`Empresas de ${ruta.nombre}`}>
        {ruta.servicios.map((s) => (
          <li key={s.servicioId} className="flex items-center gap-2 rounded bg-fondo py-1 pl-3 pr-1">
            <span>{s.empresaNombre} · {s.codigoPublico ?? "sin código"}</span>
            <button type="button" onClick={() => onQuitarServicio(s)}
              aria-label={`Quitar ${s.empresaNombre} de ${ruta.nombre}`}
              className="min-h-11 rounded px-3 text-sm font-semibold text-ladrillo underline">
              Quitar
            </button>
          </li>
        ))}
        {ruta.servicios.length === 0 ? <li className="text-sm">Ninguna empresa opera esta ruta.</li> : null}
      </ul>

      {asignando ? (
        <form noValidate className="mt-4 flex flex-wrap items-end gap-3 rounded bg-fondo p-3"
          onSubmit={(ev) => { ev.preventDefault(); if (empresaId) { setErrorServidor(null); asignar.mutate(false); } }}>
          <div>
            <label htmlFor={`emp-${ruta.id}`} className="block text-sm font-semibold">Empresa</label>
            <select id={`emp-${ruta.id}`} value={empresaId} onChange={(e) => setEmpresaId(e.target.value)}
              className="min-h-11 rounded border border-tinta/40 bg-white px-3">
              <option value="">Elige una empresa…</option>
              {libres.map((e) => <option key={e.id} value={e.id}>{e.nombre}</option>)}
            </select>
          </div>
          <div>
            <label htmlFor={`cod-${ruta.id}`} className="block text-sm font-semibold">Código público (opcional)</label>
            <input id={`cod-${ruta.id}`} type="text" maxLength={20} value={codigo} onChange={(e) => setCodigo(e.target.value)}
              className="min-h-11 w-32 rounded border border-tinta/40 bg-white px-3" />
          </div>
          <button type="submit" disabled={!empresaId || asignar.isPending}
            className="min-h-11 rounded bg-verde px-5 font-semibold text-white disabled:opacity-50">
            {asignar.isPending ? "Asignando…" : "Asignar"}
          </button>
          {libres.length === 0 ? <p className="text-sm">Todas las empresas ya operan esta ruta.</p> : null}
        </form>
      ) : null}
      {errorServidor ? <p role="alert" className="mt-3 rounded bg-ladrillo-claro p-3 text-ladrillo">Error: {errorServidor}</p> : null}

      <Modal abierto={compartida} titulo="Ruta compartida" onCerrar={() => setCompartida(false)}
        acciones={
          <>
            <button type="button" onClick={() => setCompartida(false)} className="min-h-11 rounded border border-tinta px-5 font-semibold">Cancelar</button>
            <button type="button" disabled={asignar.isPending} onClick={() => asignar.mutate(true)}
              className="min-h-11 rounded bg-verde px-5 font-semibold text-white">Confirmar compartida</button>
          </>
        }>
        Esta ruta ya la opera otra empresa. Si también la opera esta empresa, cada una tendrá su propio horario y frecuencia.
      </Modal>
    </article>
  );
}
