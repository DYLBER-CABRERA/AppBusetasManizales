"use client";
import { useMutation, useQueryClient } from "@tanstack/react-query";
import Link from "next/link";
import { useState } from "react";
import { BannerError } from "@/componentes/BannerError";
import { Esqueleto } from "@/componentes/Esqueleto";
import { Modal } from "@/componentes/Modal";
import { useToast } from "@/componentes/Toast";
import { Vacio } from "@/componentes/Vacio";
import { useParametros } from "@/lib/admin";
import { CLAVE_AVISOS, useAvisosVigentes } from "@/lib/avisos";
import { useServicios } from "@/lib/jefe";
import { usePerfil } from "@/lib/perfil";
import { publicarAviso, retirarAviso, useRutas, type Aviso } from "@/lib/secretaria";

// PENDIENTE(decisión): el jefe no puede leer `longitud_max_aviso`; se usa el valor por defecto (500).
// El administrador sí lo lee. El backend valida de todos modos.
const LONGITUD_POR_DEFECTO = 500;

const campo = "mt-1 min-h-11 w-full rounded border border-tinta/40 bg-white px-3";
const mensajeError = "mt-1 text-sm text-ladrillo";
const ETIQUETA_ORIGEN: Record<string, string> = { empresa: "Empresa", movilidad: "Movilidad", aplicativo: "Aplicativo" };

/** Avisos: del jefe (origen `empresa`, de su empresa) o del administrador (origen `aplicativo`). */
export function PantallaAvisos({ modo }: { modo: "jefe" | "admin" }) {
  const cliente = useQueryClient();
  const toast = useToast();
  const { data: perfil } = usePerfil();
  const esAdminEnJefe = modo === "jefe" && perfil?.rol === "administrador";

  const servicios = useServicios();
  const rutasTodas = useRutas();
  const parametros = useParametros();
  const avisos = useAvisosVigentes();

  const [titulo, setTitulo] = useState("");
  const [cuerpo, setCuerpo] = useState("");
  const [rutaIds, setRutaIds] = useState<string[]>([]);
  const [errores, setErrores] = useState<Record<string, string>>({});
  const [errorServidor, setErrorServidor] = useState<string | null>(null);
  const [aRetirar, setARetirar] = useState<Aviso | null>(null);

  const limite =
    modo === "admin"
      ? Number(parametros.data?.find((p) => p.clave === "longitud_max_aviso")?.valor ?? LONGITUD_POR_DEFECTO)
      : LONGITUD_POR_DEFECTO;

  const rutasDisponibles =
    modo === "jefe"
      ? [...new Map((servicios.data ?? []).map((s) => [s.rutaId, s.rutaNombre ?? "Ruta"])).entries()].map(([id, nombre]) => ({ id, nombre }))
      : (rutasTodas.data ?? []).map((r) => ({ id: r.id, nombre: r.nombre }));
  const nombreRuta = (id: string) => rutasTodas.data?.find((r) => r.id === id)?.nombre ?? rutasDisponibles.find((r) => r.id === id)?.nombre ?? "Ruta";

  const visibles = (avisos.data ?? []).filter((a) =>
    modo === "admin" ? true : a.origen === "empresa" && a.empresaId === perfil?.empresaId,
  );

  const publicar = useMutation({
    mutationFn: () => publicarAviso({ titulo: titulo.trim(), cuerpo: cuerpo.trim(), rutaIds, paraderoIds: [] }),
    onSuccess: async () => {
      setTitulo(""); setCuerpo(""); setRutaIds([]); setErrores({}); setErrorServidor(null);
      await cliente.invalidateQueries({ queryKey: CLAVE_AVISOS });
      toast("Publicado");
    },
    onError: (e) => setErrorServidor(e.message),
  });

  const retirar = useMutation({
    mutationFn: (id: string) => retirarAviso(id),
    onSuccess: async () => {
      setARetirar(null);
      await cliente.invalidateQueries({ queryKey: CLAVE_AVISOS });
      toast("Retirado");
    },
    onError: (e) => { setARetirar(null); setErrorServidor(e.message); },
  });

  function enviar(ev: React.FormEvent) {
    ev.preventDefault();
    setErrorServidor(null);
    const e: Record<string, string> = {};
    if (!titulo.trim()) e.titulo = "Escribe un título.";
    else if (titulo.trim().length > 120) e.titulo = "El título admite hasta 120 caracteres.";
    if (!cuerpo.trim()) e.cuerpo = "Escribe el mensaje.";
    else if (cuerpo.trim().length > limite) e.cuerpo = `El mensaje supera el máximo de ${limite} caracteres.`;
    if (modo === "jefe" && rutaIds.length === 0) e.rutas = "Elige al menos una ruta que afecta el aviso.";
    setErrores(e);
    if (Object.keys(e).length === 0) publicar.mutate();
  }

  if (esAdminEnJefe) {
    return (
      <Vacio titulo="Los avisos del aplicativo se publican en otra sección"
        causa="Como administrador publicas con origen «aplicativo»; los avisos de empresa los publica su jefe."
        accion={<Link href="/admin/avisos" className="font-semibold text-verde underline">Ir a Avisos del aplicativo</Link>} />
    );
  }

  const cargando = avisos.isPending || (modo === "jefe" ? servicios.isPending : rutasTodas.isPending);
  const fallo = [avisos, modo === "jefe" ? servicios : rutasTodas].find((q) => q.isError)?.error;

  return (
    <section className="max-w-3xl space-y-6">
      <h1 className="text-2xl font-bold">{modo === "jefe" ? "Publicar aviso de la empresa" : "Publicar aviso del aplicativo"}</h1>

      {fallo ? <BannerError mensaje={fallo.message} onReintentar={() => { void avisos.refetch(); void servicios.refetch(); void rutasTodas.refetch(); }} /> : null}
      {cargando && !fallo ? <Esqueleto filas={4} /> : null}

      <form noValidate onSubmit={enviar} className="space-y-4 rounded-lg bg-white p-6">
        <div>
          <label htmlFor="titulo-aviso" className="block font-semibold">Título</label>
          <input id="titulo-aviso" type="text" value={titulo} aria-invalid={!!errores.titulo} className={campo}
            onChange={(e) => setTitulo(e.target.value)} />
          {errores.titulo ? <p className={mensajeError}>{errores.titulo}</p> : null}
        </div>
        <div>
          <label htmlFor="mensaje-aviso" className="block font-semibold">Mensaje</label>
          <textarea id="mensaje-aviso" rows={4} value={cuerpo} aria-invalid={!!errores.cuerpo} aria-describedby="contador-aviso"
            className={`${campo} py-2`} onChange={(e) => setCuerpo(e.target.value)} />
          <p id="contador-aviso" className={`mt-1 text-sm ${cuerpo.length > limite ? "text-ladrillo" : ""}`}>
            {cuerpo.length} de {limite} caracteres
          </p>
          {errores.cuerpo ? <p className={mensajeError}>{errores.cuerpo}</p> : null}
        </div>
        <fieldset>
          <legend className="font-semibold">{modo === "jefe" ? "Rutas que afecta" : "Rutas que afecta (opcional)"}</legend>
          <div className="mt-1 flex flex-wrap gap-2">
            {rutasDisponibles.map((r) => (
              <label key={r.id} className="flex min-h-11 items-center gap-2 rounded bg-fondo px-3">
                <input type="checkbox" className="size-5" checked={rutaIds.includes(r.id)}
                  onChange={() => setRutaIds((l) => (l.includes(r.id) ? l.filter((x) => x !== r.id) : [...l, r.id]))} />
                {r.nombre}
              </label>
            ))}
          </div>
          {errores.rutas ? <p className={mensajeError}>{errores.rutas}</p> : null}
        </fieldset>
        {errorServidor ? <p role="alert" className="rounded bg-ladrillo-claro p-3 text-ladrillo">Error: {errorServidor}</p> : null}
        <button type="submit" disabled={publicar.isPending}
          className="min-h-11 w-full rounded bg-verde font-semibold text-white hover:bg-verde-oscuro disabled:opacity-60">
          {publicar.isPending ? "Publicando…" : "Publicar aviso"}
        </button>
      </form>

      <div>
        <h2 className="mb-2 text-lg font-bold">{modo === "jefe" ? "Avisos de tu empresa" : "Avisos vigentes"}</h2>
        {avisos.data && visibles.length === 0 ? (
          <Vacio titulo="No hay avisos vigentes" causa="Todavía no se ha publicado ninguno, o ya vencieron." />
        ) : null}
        <ul className="space-y-3">
          {visibles.map((a) => (
            <li key={a.id} className="flex items-start justify-between gap-4 rounded-lg border border-borde bg-white p-4">
              <div>
                <p className="font-bold">
                  {a.titulo}
                  {modo === "admin" ? <span className="ml-2 text-sm font-normal">({ETIQUETA_ORIGEN[a.origen] ?? a.origen}{a.empresaNombre ? ` · ${a.empresaNombre}` : ""})</span> : null}
                </p>
                <p className="text-sm">{a.cuerpo}</p>
                {a.rutaIds.length > 0 ? <p className="mt-1 text-xs">{a.rutaIds.map(nombreRuta).join(", ")}</p> : null}
              </div>
              <button type="button" onClick={() => setARetirar(a)} aria-label={`Retirar ${a.titulo}`}
                className="min-h-11 shrink-0 rounded border border-ladrillo px-4 font-semibold text-ladrillo hover:bg-ladrillo-claro">
                Retirar
              </button>
            </li>
          ))}
        </ul>
      </div>

      <Modal abierto={aRetirar !== null} titulo="Retirar aviso" onCerrar={() => setARetirar(null)}
        acciones={
          <>
            <button type="button" onClick={() => setARetirar(null)} className="min-h-11 rounded border border-tinta px-5 font-semibold">Cancelar</button>
            <button type="button" disabled={retirar.isPending} onClick={() => aRetirar && retirar.mutate(aRetirar.id)}
              className="min-h-11 rounded bg-ladrillo px-5 font-semibold text-white">Retirar</button>
          </>
        }>
        ¿Retirar «{aRetirar?.titulo}»? Dejará de verse para los pasajeros.
      </Modal>
    </section>
  );
}
