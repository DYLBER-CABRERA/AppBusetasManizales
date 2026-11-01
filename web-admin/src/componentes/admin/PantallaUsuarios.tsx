"use client";
import { useMutation, useQueryClient } from "@tanstack/react-query";
import { useState } from "react";
import { BannerError } from "@/componentes/BannerError";
import { Esqueleto } from "@/componentes/Esqueleto";
import { Modal } from "@/componentes/Modal";
import { useToast } from "@/componentes/Toast";
import { Vacio } from "@/componentes/Vacio";
import { CLAVE_USUARIOS, crearUsuario, editarUsuario, useEmpresasAdmin, useUsuarios, type Usuario } from "@/lib/admin";
import { ErrorApi } from "@/lib/errores";
import { ETIQUETA_ROL } from "@/lib/navegacion";
import { ModalContrasenaNueva } from "./ModalContrasenaNueva";

type Rol = Usuario["rol"];
const ROLES: Rol[] = ["jefe_operaciones", "secretaria_movilidad", "administrador", "pasajero"];

const campo = "mt-1 min-h-11 w-full rounded border border-tinta/40 bg-white px-3";
const mensajeError = "mt-1 text-sm text-ladrillo";
const MENSAJE_CORREO_REPETIDO = "Ese correo ya está registrado.";
const MENSAJE_EMPRESA_INEXISTENTE = "La empresa elegida ya no existe. Recarga la página y elige otra.";
const MENSAJE_SERVICIO = "No se pudo crear la cuenta por un fallo del servicio de autenticación. Inténtalo de nuevo.";
const MENSAJE_ULTIMO_ADMIN = "No se puede quitar el rol ni desactivar al último administrador activo.";

export function PantallaUsuarios() {
  const cliente = useQueryClient();
  const toast = useToast();
  const [texto, setTexto] = useState("");
  const [busqueda, setBusqueda] = useState("");
  const usuarios = useUsuarios(busqueda);
  const empresas = useEmpresasAdmin();

  const [editando, setEditando] = useState<Usuario | "nuevo" | null>(null);
  const [correo, setCorreo] = useState("");
  const [nombre, setNombre] = useState("");
  const [rol, setRol] = useState<Rol>("jefe_operaciones");
  const [empresaId, setEmpresaId] = useState("");
  const [activo, setActivo] = useState(true);
  const [contrasena, setContrasena] = useState("");
  const [creada, setCreada] = useState<{ id: string; correo: string; contrasena: string } | null>(null);
  const [reintentable, setReintentable] = useState(false);
  const [errores, setErrores] = useState<Record<string, string>>({});
  const [errorServidor, setErrorServidor] = useState<string | null>(null);
  const [conflictoVersion, setConflictoVersion] = useState(false);

  const nombreEmpresa = (id: string | null) => (id ? (empresas.data?.find((e) => e.id === id)?.nombre ?? "—") : "—");

  function abrir(u: Usuario | "nuevo") {
    setEditando(u);
    setErrores({});
    setErrorServidor(null);
    setReintentable(false);
    if (u === "nuevo") {
      setCorreo(""); setNombre(""); setRol("jefe_operaciones"); setEmpresaId(""); setActivo(true); setContrasena("");
    } else {
      setCorreo(u.correo); setNombre(u.nombre ?? ""); setRol(u.rol); setEmpresaId(u.empresaId ?? ""); setActivo(u.activo);
    }
  }

  const guardar = useMutation({
    mutationFn: () => {
      const esJefe = rol === "jefe_operaciones";
      if (editando === "nuevo") {
        return crearUsuario({
          correo: correo.trim(), nombre: nombre.trim() || null, rol, empresaId: esJefe ? empresaId : null,
          contrasena: contrasena === "" ? null : contrasena,
        });
      }
      const u = editando as Usuario;
      return editarUsuario(u.id, {
        nombre: nombre.trim() || null, rol, empresaId: esJefe ? empresaId : null, activo, version: u.version,
      });
    },
    onSuccess: async (resultado) => {
      const nuevo = editando === "nuevo";
      setEditando(null);
      setContrasena("");
      // La contraseña vive solo en este estado: no se guarda en la caché de consultas ni en el almacenamiento.
      const clave = (resultado as { contrasena?: unknown }).contrasena;
      if (nuevo && typeof clave === "string") setCreada({ id: resultado.id, correo: resultado.correo, contrasena: clave });
      guardar.reset();
      await cliente.invalidateQueries({ queryKey: CLAVE_USUARIOS });
      toast(nuevo ? "Creada" : "Guardado");
    },
    onError: (e) => {
      setReintentable(false);
      if (e instanceof ErrorApi && e.esConflictoVersion) return setConflictoVersion(true);
      if (editando === "nuevo" && e instanceof ErrorApi) {
        // Contrato §20: 400 (incluye contraseña débil para Supabase), 403, 404, 409 y 503.
        if (e.estado === 400 && /contrase/i.test(e.message)) return setErrores({ contrasena: e.message });
        if (e.estado === 409) return setErrores({ correo: MENSAJE_CORREO_REPETIDO });
        if (e.estado === 404) return setErrorServidor(MENSAJE_EMPRESA_INEXISTENTE);
        if (e.estado === 503) { setReintentable(true); return setErrorServidor(MENSAJE_SERVICIO); }
      }
      if (e instanceof ErrorApi && e.esConflictoNegocio && editando !== "nuevo") return setErrorServidor(MENSAJE_ULTIMO_ADMIN);
      setErrorServidor(e.message);
    },
  });

  function enviar(ev: React.FormEvent) {
    ev.preventDefault();
    setErrorServidor(null);
    const e: Record<string, string> = {};
    if (editando === "nuevo") {
      if (!correo.trim()) e.correo = "Escribe el correo.";
      else if (!/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(correo.trim())) e.correo = "Escribe un correo válido.";
    }
    if (nombre.trim().length > 120) e.nombre = "El nombre admite hasta 120 caracteres.";
    if (editando === "nuevo" && contrasena !== "" && (contrasena.length < 8 || contrasena.length > 72)) e.contrasena = "La contraseña debe tener entre 8 y 72 caracteres.";
    if (rol === "jefe_operaciones" && !empresaId) e.empresa = "Elige la empresa del jefe de operaciones.";
    setErrores(e);
    if (Object.keys(e).length === 0) guardar.mutate();
  }

  return (
    <section className="space-y-6">
      <div className="flex flex-wrap items-end justify-between gap-4">
        <h1 className="text-2xl font-bold">Usuarios</h1>
        {editando === null ? (
          <button type="button" onClick={() => abrir("nuevo")}
            className="min-h-11 rounded bg-verde px-5 font-semibold text-white hover:bg-verde-oscuro">Crear cuenta</button>
        ) : null}
      </div>

      <form role="search" className="flex flex-wrap items-end gap-3" onSubmit={(ev) => { ev.preventDefault(); setBusqueda(texto); }}>
        <div>
          <label htmlFor="buscar-correo" className="block text-sm font-semibold">Buscar por correo</label>
          <input id="buscar-correo" type="search" value={texto} onChange={(e) => setTexto(e.target.value)}
            className="min-h-11 w-72 rounded border border-tinta/40 bg-white px-3" />
        </div>
        <button type="submit" className="min-h-11 rounded border border-verde px-5 font-semibold text-verde hover:bg-fondo">Buscar</button>
      </form>

      {editando !== null ? (
        <form noValidate onSubmit={enviar} className="space-y-4 rounded-lg border border-borde bg-white p-6">
          <h2 className="text-lg font-bold">{editando === "nuevo" ? "Crear cuenta" : `Editar ${editando.correo}`}</h2>
          <div className="grid gap-4 md:grid-cols-2">
            <div>
              <label htmlFor="correo-usuario" className="block font-semibold">Correo</label>
              <input id="correo-usuario" type="email" value={correo} disabled={editando !== "nuevo"} aria-invalid={!!errores.correo}
                className={campo} onChange={(e) => setCorreo(e.target.value)} />
              {errores.correo ? <p className={mensajeError}>{errores.correo}</p> : null}
            </div>
            <div>
              <label htmlFor="nombre-usuario" className="block font-semibold">Nombre (opcional)</label>
              <input id="nombre-usuario" type="text" value={nombre} className={campo} onChange={(e) => setNombre(e.target.value)} />
              {errores.nombre ? <p className={mensajeError}>{errores.nombre}</p> : null}
            </div>
            <div>
              <label htmlFor="rol-usuario" className="block font-semibold">Rol</label>
              <select id="rol-usuario" value={rol} className={campo} onChange={(e) => setRol(e.target.value as Rol)}>
                {ROLES.map((r) => <option key={r} value={r}>{ETIQUETA_ROL[r]}</option>)}
              </select>
            </div>
            {rol === "jefe_operaciones" ? (
              <div>
                <label htmlFor="empresa-usuario" className="block font-semibold">Empresa</label>
                <select id="empresa-usuario" value={empresaId} aria-invalid={!!errores.empresa} className={campo} onChange={(e) => setEmpresaId(e.target.value)}>
                  <option value="">Elige una empresa…</option>
                  {empresas.data?.filter((e) => e.estado === "activo").map((e) => <option key={e.id} value={e.id}>{e.nombre}</option>)}
                </select>
                {errores.empresa ? <p className={mensajeError}>{errores.empresa}</p> : null}
              </div>
            ) : null}
            {editando !== "nuevo" ? (
              <label className="flex min-h-11 items-center gap-2 font-semibold">
                <input type="checkbox" className="size-5" checked={activo} onChange={(e) => setActivo(e.target.checked)} />
                Cuenta activa
              </label>
            ) : null}
          </div>
          {editando === "nuevo" ? (
            <div>
              <label htmlFor="contrasena-usuario" className="block font-semibold">Contraseña (opcional)</label>
              <input id="contrasena-usuario" type="password" autoComplete="new-password" value={contrasena} aria-invalid={!!errores.contrasena}
                aria-describedby="ayuda-contrasena" className={campo}
                onChange={(e) => { setContrasena(e.target.value); setErrores((x) => ({ ...x, contrasena: "" })); }} />
              <p id="ayuda-contrasena" className={errores.contrasena ? mensajeError : "mt-1 text-sm"}>
                {errores.contrasena || "De 8 a 72 caracteres. Si la dejas vacía, el sistema genera una segura. Se mostrará una sola vez al crear la cuenta."}
              </p>
            </div>
          ) : null}
          {errorServidor ? (
            <div role="alert" className="flex flex-wrap items-center justify-between gap-3 rounded bg-ladrillo-claro p-3 text-ladrillo">
              <span>Error: {errorServidor}</span>
              {reintentable ? (
                <button type="button" disabled={guardar.isPending} onClick={() => guardar.mutate()}
                  className="min-h-11 rounded border border-ladrillo px-4 font-semibold">Reintentar</button>
              ) : null}
            </div>
          ) : null}
          <div className="flex gap-3">
            <button type="submit" disabled={guardar.isPending}
              className="min-h-11 rounded bg-verde px-5 font-semibold text-white hover:bg-verde-oscuro disabled:opacity-60">
              {guardar.isPending ? "Guardando…" : editando === "nuevo" ? "Crear cuenta" : "Guardar cambios"}
            </button>
            <button type="button" onClick={() => setEditando(null)} className="min-h-11 rounded border border-tinta px-5 font-semibold">Cancelar</button>
          </div>
        </form>
      ) : null}

      {usuarios.isError ? <BannerError mensaje={usuarios.error.message} onReintentar={() => usuarios.refetch()} /> : null}
      {usuarios.isPending ? <Esqueleto filas={5} /> : null}
      {usuarios.data && usuarios.data.length === 0 ? (
        <Vacio titulo="Sin resultados" causa={busqueda ? `Ningún usuario coincide con «${busqueda}».` : "Todavía no hay usuarios."}
          accion={busqueda ? <span>Prueba con otra parte del correo.</span> : undefined} />
      ) : null}
      {usuarios.data && usuarios.data.length > 0 ? (
        <div className="overflow-x-auto rounded-lg border border-borde bg-white">
          <table className="w-full text-left">
            <caption className="sr-only">Usuarios</caption>
            <thead className="bg-fondo text-sm">
              <tr>
                <th scope="col" className="p-3">Correo</th><th scope="col" className="p-3">Rol</th>
                <th scope="col" className="p-3">Empresa</th><th scope="col" className="p-3">Activo</th>
                <th scope="col" className="p-3"><span className="sr-only">Acciones</span></th>
              </tr>
            </thead>
            <tbody>
              {usuarios.data.map((u) => (
                <tr key={u.id} className="border-t border-borde">
                  <td className="p-3">{u.correo}</td>
                  <td className="p-3">{ETIQUETA_ROL[u.rol] ?? u.rol}</td>
                  <td className="p-3">{nombreEmpresa(u.empresaId ?? null)}</td>
                  <td className="p-3">{u.activo ? "Sí" : "No"}</td>
                  <td className="p-3 text-right">
                    <button type="button" onClick={() => abrir(u)} aria-label={`Editar ${u.correo}`}
                      className="min-h-11 rounded border border-verde px-4 font-semibold text-verde hover:bg-fondo">Editar</button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      ) : null}

      <ModalContrasenaNueva key={creada?.id} contrasena={creada?.contrasena ?? null} correo={creada?.correo ?? ""} onCerrar={() => setCreada(null)} />

      <Modal abierto={conflictoVersion} titulo="Alguien más cambió esto" onCerrar={() => setConflictoVersion(false)}
        acciones={<button type="button" className="min-h-11 rounded bg-verde px-5 font-semibold text-white"
          onClick={() => { setConflictoVersion(false); setEditando(null); void usuarios.refetch(); }}>Recargar</button>}>
        Alguien más cambió esto. Recarga para ver los cambios.
      </Modal>
    </section>
  );
}
