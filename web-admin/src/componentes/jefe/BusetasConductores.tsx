"use client";
import { useMutation, useQueryClient } from "@tanstack/react-query";
import { useState } from "react";
import { BannerError } from "@/componentes/BannerError";
import { Esqueleto } from "@/componentes/Esqueleto";
import { useToast } from "@/componentes/Toast";
import { ErrorApi } from "@/lib/errores";
import { crearBuseta, crearConductor, editarBuseta, editarConductor, useBusetas, useClaveEmpresa, useConductores } from "@/lib/jefe";

const campo = "mt-1 min-h-11 w-full rounded border border-tinta/40 bg-white px-3";
const mensajeError = "mt-1 text-sm text-ladrillo";

type BusetaFila = NonNullable<ReturnType<typeof useBusetas>["data"]>[number];
type ConductorFila = NonNullable<ReturnType<typeof useConductores>["data"]>[number];
const MSG_VERSION = "Alguien más cambió esto. Recarga para ver los cambios.";

/** Alta y edición de busetas y conductores de la empresa (en los PUT, un campo omitido o null no se modifica). */
export function BusetasConductores() {
  const cliente = useQueryClient();
  const toast = useToast();
  const emp = useClaveEmpresa();
  const busetas = useBusetas();
  const conductores = useConductores();

  const [lateral, setLateral] = useState("");
  const [placa, setPlaca] = useState("");
  const [errLateral, setErrLateral] = useState<string | null>(null);
  const [errBuseta, setErrBuseta] = useState<string | null>(null);

  const [nombre, setNombre] = useState("");
  const [codigo, setCodigo] = useState("");
  const [errNombre, setErrNombre] = useState<string | null>(null);
  const [errConductor, setErrConductor] = useState<string | null>(null);

  const [editB, setEditB] = useState<BusetaFila | null>(null);
  const [estadoB, setEstadoB] = useState<"activa" | "fuera_servicio" | "baja">("activa");
  const [editC, setEditC] = useState<ConductorFila | null>(null);
  const [estadoC, setEstadoC] = useState<"activo" | "baja">("activo");

  const limpiarBuseta = () => { setEditB(null); setLateral(""); setPlaca(""); setErrBuseta(null); setErrLateral(null); };
  const limpiarConductor = () => { setEditC(null); setNombre(""); setCodigo(""); setErrConductor(null); setErrNombre(null); };
  const errorDe = (e: Error) => (e instanceof ErrorApi && e.esConflictoVersion ? MSG_VERSION : e.message);

  const nuevaBuseta = useMutation({
    mutationFn: () =>
      editB
        ? editarBuseta(editB.id, { numeroLateral: lateral.trim(), placa: placa.trim() || null, estado: estadoB, version: editB.version })
        : crearBuseta({ numeroLateral: lateral.trim(), placa: placa.trim() || null }),
    onSuccess: async () => {
      limpiarBuseta();
      await cliente.invalidateQueries({ queryKey: ["jefe", emp, "busetas"] });
      toast("Guardada");
    },
    onError: (e) => {
      setErrBuseta(errorDe(e));
      if (e instanceof ErrorApi && e.esConflictoVersion) void cliente.invalidateQueries({ queryKey: ["jefe", emp, "busetas"] });
    },
  });
  const nuevoConductor = useMutation({
    mutationFn: () =>
      editC
        ? editarConductor(editC.id, { nombre: nombre.trim(), codigo: codigo.trim() || null, estado: estadoC, version: editC.version })
        : crearConductor({ nombre: nombre.trim(), codigo: codigo.trim() || null }),
    onSuccess: async () => {
      limpiarConductor();
      await cliente.invalidateQueries({ queryKey: ["jefe", emp, "conductores"] });
      toast("Guardado");
    },
    onError: (e) => {
      setErrConductor(errorDe(e));
      if (e instanceof ErrorApi && e.esConflictoVersion) void cliente.invalidateQueries({ queryKey: ["jefe", emp, "conductores"] });
    },
  });

  return (
    <div className="grid gap-6 lg:grid-cols-2">
      <section className="space-y-3 rounded-lg border border-borde bg-white p-5" aria-labelledby="h-busetas">
        <h2 id="h-busetas" className="text-lg font-bold">Busetas</h2>
        {busetas.isError ? <BannerError mensaje={busetas.error.message} onReintentar={() => busetas.refetch()} /> : null}
        {busetas.isPending ? <Esqueleto filas={3} /> : null}
        <ul className="flex flex-wrap gap-2">
          {busetas.data?.map((b) => (
            <li key={b.id} className="flex items-center gap-2 rounded bg-fondo px-3 py-1">
              <span>{b.numeroLateral}{b.placa ? ` · ${b.placa}` : ""}{b.estado === "fuera_servicio" ? " · fuera de servicio" : ""}</span>
              <button type="button" aria-label={`Editar la buseta ${b.numeroLateral}`} className="min-h-11 rounded px-2 font-semibold text-verde underline"
                onClick={() => { setEditB(b); setLateral(b.numeroLateral); setPlaca(b.placa ?? ""); setEstadoB(b.estado); setErrBuseta(null); setErrLateral(null); }}>Editar</button>
            </li>
          ))}
          {busetas.data?.length === 0 ? <li className="text-sm">Todavía no hay busetas. Agrega la primera.</li> : null}
        </ul>
        <form noValidate className="space-y-3" onSubmit={(ev) => {
          ev.preventDefault();
          setErrBuseta(null);
          const v = lateral.trim();
          const msg = !v ? "Escribe el número lateral." : v.length > 20 ? "El número lateral admite hasta 20 caracteres." : placa.trim().length > 10 ? "La placa admite hasta 10 caracteres." : null;
          setErrLateral(msg);
          if (!msg) nuevaBuseta.mutate();
        }}>
          <div>
            <label htmlFor="lateral" className="block font-semibold">Número lateral</label>
            <input id="lateral" type="text" value={lateral} aria-invalid={!!errLateral} className={campo} onChange={(e) => { setLateral(e.target.value); setErrLateral(null); }} />
            {errLateral ? <p className={mensajeError}>{errLateral}</p> : null}
          </div>
          <div>
            <label htmlFor="placa" className="block font-semibold">Placa (opcional)</label>
            <input id="placa" type="text" value={placa} className={campo} onChange={(e) => setPlaca(e.target.value)} />
          </div>
          {editB ? (
            <div>
              <label htmlFor="estado-buseta" className="block font-semibold">Estado</label>
              <select id="estado-buseta" value={estadoB} className={campo} onChange={(e) => setEstadoB(e.target.value as typeof estadoB)}>
                <option value="activa">Activa</option>
                <option value="fuera_servicio">Fuera de servicio</option>
                <option value="baja">Dar de baja (deja de listarse)</option>
              </select>
            </div>
          ) : null}
          {errBuseta ? <p role="alert" className="rounded bg-ladrillo-claro p-3 text-ladrillo">Error: {errBuseta}</p> : null}
          <button type="submit" disabled={nuevaBuseta.isPending} className="min-h-11 rounded bg-verde px-5 font-semibold text-white hover:bg-verde-oscuro disabled:opacity-60">
            {nuevaBuseta.isPending ? "Guardando…" : editB ? "Guardar cambios de la buseta" : "Guardar buseta"}
          </button>
          {editB ? <button type="button" onClick={limpiarBuseta} className="ml-3 min-h-11 rounded border border-tinta px-5 font-semibold">Cancelar</button> : null}
        </form>
      </section>

      <section className="space-y-3 rounded-lg border border-borde bg-white p-5" aria-labelledby="h-conductores">
        <h2 id="h-conductores" className="text-lg font-bold">Conductores</h2>
        {conductores.isError ? <BannerError mensaje={conductores.error.message} onReintentar={() => conductores.refetch()} /> : null}
        {conductores.isPending ? <Esqueleto filas={3} /> : null}
        <ul className="flex flex-wrap gap-2">
          {conductores.data?.map((c) => (
            <li key={c.id} className="flex items-center gap-2 rounded bg-fondo px-3 py-1">
              <span>{c.nombre}{c.codigo ? ` · ${c.codigo}` : ""}</span>
              <button type="button" aria-label={`Editar al conductor ${c.nombre}`} className="min-h-11 rounded px-2 font-semibold text-verde underline"
                onClick={() => { setEditC(c); setNombre(c.nombre); setCodigo(c.codigo ?? ""); setEstadoC(c.estado); setErrConductor(null); setErrNombre(null); }}>Editar</button>
            </li>
          ))}
          {conductores.data?.length === 0 ? <li className="text-sm">Todavía no hay conductores. Agrega el primero.</li> : null}
        </ul>
        <form noValidate className="space-y-3" onSubmit={(ev) => {
          ev.preventDefault();
          setErrConductor(null);
          const v = nombre.trim();
          const msg = !v ? "Escribe el nombre." : v.length < 2 ? "El nombre necesita al menos 2 caracteres." : v.length > 120 ? "El nombre admite hasta 120 caracteres." : codigo.trim().length > 20 ? "El código admite hasta 20 caracteres." : null;
          setErrNombre(msg);
          if (!msg) nuevoConductor.mutate();
        }}>
          <div>
            <label htmlFor="nombre-conductor" className="block font-semibold">Nombre</label>
            <input id="nombre-conductor" type="text" value={nombre} aria-invalid={!!errNombre} className={campo} onChange={(e) => { setNombre(e.target.value); setErrNombre(null); }} />
            {errNombre ? <p className={mensajeError}>{errNombre}</p> : null}
          </div>
          <div>
            <label htmlFor="codigo-conductor" className="block font-semibold">Código (opcional)</label>
            <input id="codigo-conductor" type="text" value={codigo} className={campo} onChange={(e) => setCodigo(e.target.value)} />
          </div>
          {editC ? (
            <div>
              <label htmlFor="estado-conductor" className="block font-semibold">Estado</label>
              <select id="estado-conductor" value={estadoC} className={campo} onChange={(e) => setEstadoC(e.target.value as typeof estadoC)}>
                <option value="activo">Activo</option>
                <option value="baja">Dar de baja (deja de listarse)</option>
              </select>
            </div>
          ) : null}
          {errConductor ? <p role="alert" className="rounded bg-ladrillo-claro p-3 text-ladrillo">Error: {errConductor}</p> : null}
          <button type="submit" disabled={nuevoConductor.isPending} className="min-h-11 rounded bg-verde px-5 font-semibold text-white hover:bg-verde-oscuro disabled:opacity-60">
            {nuevoConductor.isPending ? "Guardando…" : editC ? "Guardar cambios del conductor" : "Guardar conductor"}
          </button>
          {editC ? <button type="button" onClick={limpiarConductor} className="ml-3 min-h-11 rounded border border-tinta px-5 font-semibold">Cancelar</button> : null}
        </form>
      </section>
    </div>
  );
}
