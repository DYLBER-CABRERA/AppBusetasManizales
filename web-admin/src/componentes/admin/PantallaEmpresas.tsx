"use client";
import { useMutation, useQueryClient } from "@tanstack/react-query";
import { useState } from "react";
import { BannerError } from "@/componentes/BannerError";
import { Esqueleto } from "@/componentes/Esqueleto";
import { Modal } from "@/componentes/Modal";
import { useToast } from "@/componentes/Toast";
import { Vacio } from "@/componentes/Vacio";
import { CLAVE_EMPRESAS_ADMIN, crearEmpresa, editarEmpresa, useEmpresasAdmin, type EmpresaAdmin } from "@/lib/admin";
import { ErrorApi } from "@/lib/errores";

const campo = "mt-1 min-h-11 w-full rounded border border-tinta/40 bg-white px-3";

export function PantallaEmpresas() {
  const cliente = useQueryClient();
  const toast = useToast();
  const empresas = useEmpresasAdmin();

  const [editando, setEditando] = useState<EmpresaAdmin | "nueva" | null>(null);
  const [nombre, setNombre] = useState("");
  const [estado, setEstado] = useState<EmpresaAdmin["estado"]>("activo");
  const [errorNombre, setErrorNombre] = useState<string | null>(null);
  const [errorServidor, setErrorServidor] = useState<string | null>(null);
  const [conflictoVersion, setConflictoVersion] = useState(false);

  function abrir(e: EmpresaAdmin | "nueva") {
    setEditando(e);
    setErrorNombre(null);
    setErrorServidor(null);
    setNombre(e === "nueva" ? "" : e.nombre);
    setEstado(e === "nueva" ? "activo" : e.estado);
  }

  const guardar = useMutation({
    mutationFn: () =>
      editando === "nueva"
        ? crearEmpresa(nombre.trim())
        : editarEmpresa((editando as EmpresaAdmin).id, { nombre: nombre.trim(), estado, version: (editando as EmpresaAdmin).version }),
    onSuccess: async () => {
      const nueva = editando === "nueva";
      setEditando(null);
      await cliente.invalidateQueries({ queryKey: CLAVE_EMPRESAS_ADMIN });
      toast(nueva ? "Creada" : "Guardado");
    },
    onError: (e) => {
      if (e instanceof ErrorApi && e.esConflictoVersion) return setConflictoVersion(true);
      setErrorServidor(e.message);
    },
  });

  function enviar(ev: React.FormEvent) {
    ev.preventDefault();
    setErrorServidor(null);
    const n = nombre.trim();
    const msg = n.length < 2 ? "El nombre necesita al menos 2 caracteres." : n.length > 120 ? "El nombre admite hasta 120 caracteres." : null;
    setErrorNombre(msg);
    if (!msg) guardar.mutate();
  }

  return (
    <section className="space-y-6">
      <div className="flex items-center justify-between gap-4">
        <h1 className="text-2xl font-bold">Empresas</h1>
        {editando === null ? (
          <button type="button" onClick={() => abrir("nueva")} className="min-h-11 rounded bg-verde px-5 font-semibold text-white hover:bg-verde-oscuro">
            Crear empresa
          </button>
        ) : null}
      </div>

      {editando !== null ? (
        <form noValidate onSubmit={enviar} className="space-y-4 rounded-lg border border-borde bg-white p-6">
          <h2 className="text-lg font-bold">{editando === "nueva" ? "Crear empresa" : `Editar ${editando.nombre}`}</h2>
          <div className="grid gap-4 md:grid-cols-2">
            <div>
              <label htmlFor="nombre-empresa" className="block font-semibold">Nombre</label>
              <input id="nombre-empresa" type="text" value={nombre} aria-invalid={!!errorNombre} className={campo}
                onChange={(e) => { setNombre(e.target.value); setErrorNombre(null); }} />
              {errorNombre ? <p className="mt-1 text-sm text-ladrillo">{errorNombre}</p> : null}
            </div>
            {editando !== "nueva" ? (
              <div>
                <label htmlFor="estado-empresa" className="block font-semibold">Estado</label>
                <select id="estado-empresa" value={estado} className={campo} onChange={(e) => setEstado(e.target.value as EmpresaAdmin["estado"])}>
                  <option value="activo">Activa</option>
                  <option value="baja">Dada de baja</option>
                </select>
              </div>
            ) : null}
          </div>
          {errorServidor ? <p role="alert" className="rounded bg-ladrillo-claro p-3 text-ladrillo">Error: {errorServidor}</p> : null}
          <div className="flex gap-3">
            <button type="submit" disabled={guardar.isPending}
              className="min-h-11 rounded bg-verde px-5 font-semibold text-white hover:bg-verde-oscuro disabled:opacity-60">
              {guardar.isPending ? "Guardando…" : editando === "nueva" ? "Crear empresa" : "Guardar cambios"}
            </button>
            <button type="button" onClick={() => setEditando(null)} className="min-h-11 rounded border border-tinta px-5 font-semibold">Cancelar</button>
          </div>
        </form>
      ) : null}

      {empresas.isError ? <BannerError mensaje={empresas.error.message} onReintentar={() => empresas.refetch()} /> : null}
      {empresas.isPending ? <Esqueleto filas={4} /> : null}
      {empresas.data && empresas.data.length === 0 ? (
        <Vacio titulo="Todavía no hay empresas" causa="No se ha creado ninguna empresa." accion={<span>Usa «Crear empresa».</span>} />
      ) : null}
      {empresas.data && empresas.data.length > 0 ? (
        <div className="overflow-x-auto rounded-lg border border-borde bg-white">
          <table className="w-full text-left">
            <caption className="sr-only">Empresas</caption>
            <thead className="bg-fondo text-sm">
              <tr><th scope="col" className="p-3">Nombre</th><th scope="col" className="p-3">Estado</th><th scope="col" className="p-3"><span className="sr-only">Acciones</span></th></tr>
            </thead>
            <tbody>
              {empresas.data.map((e) => (
                <tr key={e.id} className="border-t border-borde">
                  <td className="p-3 font-semibold">{e.nombre}</td>
                  <td className="p-3">{e.estado === "activo" ? "Activa" : "Dada de baja"}</td>
                  <td className="p-3 text-right">
                    <button type="button" onClick={() => abrir(e)} aria-label={`Editar ${e.nombre}`}
                      className="min-h-11 rounded border border-verde px-4 font-semibold text-verde hover:bg-fondo">Editar</button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      ) : null}

      <Modal abierto={conflictoVersion} titulo="Alguien más cambió esto" onCerrar={() => setConflictoVersion(false)}
        acciones={<button type="button" className="min-h-11 rounded bg-verde px-5 font-semibold text-white"
          onClick={() => { setConflictoVersion(false); setEditando(null); void empresas.refetch(); }}>Recargar</button>}>
        Alguien más cambió esto. Recarga para ver los cambios.
      </Modal>
    </section>
  );
}
