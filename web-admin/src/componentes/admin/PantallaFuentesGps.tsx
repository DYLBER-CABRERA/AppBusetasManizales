"use client";
import { useMutation, useQueryClient } from "@tanstack/react-query";
import { useEffect, useState } from "react";
import { BannerError } from "@/componentes/BannerError";
import { Esqueleto } from "@/componentes/Esqueleto";
import { Modal } from "@/componentes/Modal";
import { useToast } from "@/componentes/Toast";
import { Vacio } from "@/componentes/Vacio";
import {
  claveCredenciales, crearCredencial, revocarCredencial, useCredenciales, useEmpresasAdmin,
  type CredencialGps, type EmpresaAdmin,
} from "@/lib/admin";
import { haceTexto } from "@/lib/fechas";
import type { components } from "@/lib/tipos-api";

type CredencialCreada = components["schemas"]["CredencialGpsCreada"];

function useAhora(ms: number) {
  const [ahora, setAhora] = useState(() => Date.now());
  useEffect(() => {
    const t = setInterval(() => setAhora(Date.now()), ms);
    return () => clearInterval(t);
  }, [ms]);
  return ahora;
}

function TarjetaEmpresa({ empresa, onClaveNueva }: { empresa: EmpresaAdmin; onClaveNueva: (c: CredencialCreada, empresa: string) => void }) {
  const cliente = useQueryClient();
  const toast = useToast();
  const ahora = useAhora(1000);
  const credenciales = useCredenciales(empresa.id);
  const [nombre, setNombre] = useState("");
  const [errorNombre, setErrorNombre] = useState<string | null>(null);
  const [aRevocar, setARevocar] = useState<CredencialGps | null>(null);
  const [errorAccion, setErrorAccion] = useState<string | null>(null);

  const crear = useMutation({
    mutationFn: (n: string) => crearCredencial(empresa.id, n),
    onSuccess: async (creada) => {
      setNombre("");
      setErrorAccion(null);
      onClaveNueva(creada, empresa.nombre);
      crear.reset(); // la clave no debe quedarse en la caché de la consulta
      await cliente.invalidateQueries({ queryKey: claveCredenciales(empresa.id) });
      toast("Generada");
    },
    onError: (e) => setErrorAccion(e.message),
  });

  const revocar = useMutation({
    mutationFn: (id: string) => revocarCredencial(id),
    onSuccess: async () => {
      setARevocar(null);
      setErrorAccion(null);
      await cliente.invalidateQueries({ queryKey: claveCredenciales(empresa.id) });
      toast("Revocada");
    },
    onError: (e) => {
      setARevocar(null);
      setErrorAccion(e.message);
    },
  });

  function enviar(ev: React.FormEvent) {
    ev.preventDefault();
    const n = nombre.trim();
    if (!n) return setErrorNombre("Escribe un nombre para la fuente.");
    if (n.length > 80) return setErrorNombre("El nombre admite hasta 80 caracteres.");
    setErrorNombre(null);
    crear.mutate(n);
  }

  const idCampo = `nombre-fuente-${empresa.id}`;

  return (
    <article className="rounded-lg border border-borde bg-white p-5" aria-labelledby={`emp-${empresa.id}`}>
      <h2 id={`emp-${empresa.id}`} className="mb-3 text-lg font-bold">{empresa.nombre}</h2>

      {credenciales.isError ? (
        <BannerError mensaje={credenciales.error.message} onReintentar={() => credenciales.refetch()} />
      ) : null}
      {credenciales.isPending ? <Esqueleto filas={2} /> : null}
      {credenciales.data && credenciales.data.length === 0 ? (
        <Vacio titulo="Sin claves de fuente GPS" causa={`${empresa.nombre} todavía no tiene una fuente que envíe posiciones.`}
          accion={<span>Genera una clave nueva abajo.</span>} />
      ) : null}
      {credenciales.data && credenciales.data.length > 0 ? (
        <table className="w-full text-left">
          <caption className="sr-only">Fuentes GPS de {empresa.nombre}</caption>
          <thead className="bg-fondo text-sm">
            <tr>
              <th scope="col" className="p-3">Fuente</th>
              <th scope="col" className="p-3">Estado</th>
              <th scope="col" className="p-3">Último envío</th>
              <th scope="col" className="p-3"><span className="sr-only">Acciones</span></th>
            </tr>
          </thead>
          <tbody>
            {credenciales.data.map((c) => (
              <tr key={c.id} className="border-t border-borde">
                <td className="p-3 font-semibold">{c.nombre}</td>
                <td className="p-3">{c.activa ? "Activa" : "Revocada"}</td>
                <td className="p-3">{c.ultimoUso ? `Último envío ${haceTexto(c.ultimoUso, ahora)}` : "Sin envíos"}</td>
                <td className="p-3 text-right">
                  <button type="button" disabled={!c.activa} onClick={() => setARevocar(c)}
                    className="min-h-11 rounded border border-ladrillo px-4 font-semibold text-ladrillo hover:bg-ladrillo-claro disabled:opacity-50">
                    Revocar
                  </button>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      ) : null}

      {errorAccion ? <p role="alert" className="mt-3 rounded bg-ladrillo-claro p-3 text-ladrillo">Error: {errorAccion}</p> : null}

      <form noValidate onSubmit={enviar} className="mt-4 flex flex-wrap items-start gap-3">
        <div>
          <label htmlFor={idCampo} className="block text-sm font-semibold">Nombre de la fuente</label>
          <input id={idCampo} type="text" maxLength={120} value={nombre} aria-invalid={!!errorNombre}
            onChange={(e) => { setNombre(e.target.value); setErrorNombre(null); }}
            className="min-h-11 w-72 rounded border border-tinta/40 bg-white px-3" />
          {errorNombre ? <p className="mt-1 text-sm text-ladrillo">{errorNombre}</p> : null}
        </div>
        <button type="submit" disabled={crear.isPending}
          className="mt-6 min-h-11 rounded bg-verde px-5 font-semibold text-white hover:bg-verde-oscuro disabled:opacity-50">
          {crear.isPending ? "Generando…" : "Generar clave nueva"}
        </button>
      </form>

      <Modal abierto={aRevocar !== null} titulo="Revocar clave" onCerrar={() => setARevocar(null)}
        acciones={
          <>
            <button type="button" onClick={() => setARevocar(null)}
              className="min-h-11 rounded border border-tinta px-5 font-semibold">Cancelar</button>
            <button type="button" disabled={revocar.isPending} onClick={() => aRevocar && revocar.mutate(aRevocar.id)}
              className="min-h-11 rounded bg-ladrillo px-5 font-semibold text-white">Revocar</button>
          </>
        }>
        La fuente «{aRevocar?.nombre}» dejará de poder enviar posiciones de {empresa.nombre}. No se puede deshacer.
      </Modal>
    </article>
  );
}

export function PantallaFuentesGps() {
  const empresas = useEmpresasAdmin();
  const activas = empresas.data?.filter((e) => e.estado === "activo");
  const toast = useToast();
  // La clave vive solo aquí, en memoria, mientras el modal está abierto: nunca en caché ni en el almacenamiento.
  const [nueva, setNueva] = useState<{ credencial: CredencialCreada; empresa: string } | null>(null);

  async function copiar() {
    if (!nueva) return;
    try {
      await navigator.clipboard.writeText(nueva.credencial.clave);
      toast("Copiada");
    } catch {
      toast("No se pudo copiar: selecciónala y cópiala a mano");
    }
  }

  return (
    <section className="space-y-6">
      <h1 className="text-2xl font-bold">Fuentes GPS</h1>
      <p className="text-sm">Cada empresa envía sus posiciones con una clave propia. Se compara por hash: la clave solo se ve al crearla.</p>

      {empresas.isError ? <BannerError mensaje={empresas.error.message} onReintentar={() => empresas.refetch()} /> : null}
      {empresas.isPending ? <Esqueleto filas={4} /> : null}
      {activas && activas.length === 0 ? (
        <Vacio titulo="No hay empresas" causa="Sin empresas no hay fuentes GPS." accion={<span>Crea una empresa en la sección Empresas.</span>} />
      ) : null}
      {activas?.map((e) => (
        <TarjetaEmpresa key={e.id} empresa={e} onClaveNueva={(credencial, empresa) => setNueva({ credencial, empresa })} />
      ))}

      <Modal abierto={nueva !== null} sinEscape titulo="Clave nueva" onCerrar={() => setNueva(null)}
        acciones={
          <>
            <button type="button" onClick={copiar}
              className="min-h-11 rounded border border-verde px-5 font-semibold text-verde">Copiar</button>
            <button type="button" onClick={() => setNueva(null)}
              className="min-h-11 rounded bg-verde px-5 font-semibold text-white">Ya la copié</button>
          </>
        }>
        <p className="mb-2 font-semibold">Copia la clave ahora. No podrás verla otra vez.</p>
        <p className="mb-2">Fuente «{nueva?.credencial.nombre}» de {nueva?.empresa}:</p>
        <code className="block break-all rounded bg-fondo p-3 text-base select-all">{nueva?.credencial.clave}</code>
      </Modal>
    </section>
  );
}
