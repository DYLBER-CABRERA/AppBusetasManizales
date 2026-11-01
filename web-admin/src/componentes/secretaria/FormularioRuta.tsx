"use client";
import { zodResolver } from "@hookform/resolvers/zod";
import { useMutation, useQueryClient } from "@tanstack/react-query";
import { useState } from "react";
import { useForm } from "react-hook-form";
import { z } from "zod";
import { Modal } from "@/componentes/Modal";
import { useToast } from "@/componentes/Toast";
import { ErrorApi } from "@/lib/errores";
import {
  CLAVE_RUTAS, crearRuta, editarRuta,
  type Empresa, type Paradero, type RutaDetalle, type RutaResumen, type ServicioCrearEntrada,
} from "@/lib/secretaria";
import { SelectorParaderos } from "./SelectorParaderos";

const esquema = z.object({
  nombre: z.string().trim().min(1, "Escribe el nombre de la ruta.").max(120, "El nombre admite hasta 120 caracteres."),
  descripcion: z.string().optional(),
  rutaPrincipalId: z.string().optional(),
});
type Datos = z.infer<typeof esquema>;

type Codigos = { codigoPublico: string; codigoInterno: string };

const campo = "mt-1 min-h-11 w-full rounded border border-tinta/40 bg-white px-3";
const error = "mt-1 text-sm text-ladrillo";

type Props = {
  /** Con `ruta` se edita (con `version`); sin ella se registra una nueva. */
  ruta?: RutaDetalle;
  paraderos: Paradero[];
  empresas: Empresa[];
  rutas: RutaResumen[];
  onListo: () => void;
  onCancelar: () => void;
  onConflictoVersion: () => void;
};

export function FormularioRuta({ ruta, paraderos, empresas, rutas, onListo, onCancelar, onConflictoVersion }: Props) {
  const cliente = useQueryClient();
  const toast = useToast();
  const edita = ruta !== undefined;

  const { register, handleSubmit, formState: { errors } } = useForm<Datos>({
    resolver: zodResolver(esquema),
    defaultValues: { nombre: ruta?.nombre ?? "", descripcion: ruta?.descripcion ?? "", rutaPrincipalId: "" },
  });
  const inicial = ruta ? [...ruta.paraderos].sort((a, b) => a.orden - b.orden).map((p) => p.paraderoId) : [];
  const [paraderoIds, setParaderoIds] = useState<string[]>(inicial);
  const [elegidas, setElegidas] = useState<Record<string, Codigos>>({});
  const [errorParaderos, setErrorParaderos] = useState<string | null>(null);
  const [errorEmpresas, setErrorEmpresas] = useState<string | null>(null);
  const [errorServidor, setErrorServidor] = useState<string | null>(null);
  const [compartida, setCompartida] = useState(false);

  const servicios = (): ServicioCrearEntrada[] =>
    Object.entries(elegidas).map(([empresaId, c]) => ({
      empresaId,
      codigoPublico: c.codigoPublico.trim() || null,
      codigoInterno: c.codigoInterno.trim() || null,
    }));

  const guardar = useMutation({
    mutationFn: async ({ d, confirmar }: { d: Datos; confirmar: boolean }) => {
      if (ruta) {
        const cambioParaderos = JSON.stringify(paraderoIds) !== JSON.stringify(inicial);
        return editarRuta(ruta.id, {
          nombre: d.nombre.trim(),
          descripcion: d.descripcion?.trim() || null,
          paraderoIds: cambioParaderos ? paraderoIds : null,
          version: ruta.version,
        });
      }
      return crearRuta({
        nombre: d.nombre.trim(),
        tipoRecorrido: "circular",
        rutaPrincipalId: d.rutaPrincipalId || null,
        paraderoIds,
        servicios: servicios(),
        confirmarCompartida: confirmar,
      });
    },
    onSuccess: async () => {
      setCompartida(false);
      await cliente.invalidateQueries({ queryKey: CLAVE_RUTAS });
      if (ruta) await cliente.invalidateQueries({ queryKey: ["sec", "ruta", ruta.id] });
      toast(edita ? "Guardado" : "Registrada");
      onListo();
    },
    onError: (e, { confirmar }) => {
      if (e instanceof ErrorApi && e.esConflictoVersion) return onConflictoVersion();
      if (e instanceof ErrorApi && e.esConflictoNegocio && !edita && !confirmar && Object.keys(elegidas).length > 1) {
        return setCompartida(true);
      }
      setCompartida(false);
      setErrorServidor(e.message);
    },
  });

  function enviar(d: Datos) {
    setErrorServidor(null);
    const sinParaderos = paraderoIds.length < 2;
    const sinEmpresas = !edita && Object.keys(elegidas).length === 0;
    setErrorParaderos(sinParaderos ? "Elige al menos 2 paraderos para armar el recorrido." : null);
    setErrorEmpresas(sinEmpresas ? "Elige al menos una empresa que opere la ruta." : null);
    if (sinParaderos || sinEmpresas) return;
    guardar.mutate({ d, confirmar: false });
  }

  const alternarEmpresa = (id: string, marcada: boolean) =>
    setElegidas((e) => {
      const { [id]: _quitada, ...resto } = e;
      void _quitada;
      return marcada ? { ...e, [id]: { codigoPublico: "", codigoInterno: "" } } : resto;
    });

  return (
    <form noValidate onSubmit={handleSubmit(enviar)} className="space-y-5 rounded-lg border border-borde bg-white p-6">
      <h2 className="text-xl font-bold">{edita ? `Editar ruta ${ruta.nombre}` : "Registrar ruta"}</h2>

      <div className="grid gap-4 md:grid-cols-2">
        <div>
          <label htmlFor="nombre-ruta" className="block font-semibold">Nombre</label>
          <input id="nombre-ruta" type="text" aria-invalid={!!errors.nombre} className={campo} {...register("nombre")} />
          {errors.nombre ? <p className={error}>{errors.nombre.message}</p> : null}
        </div>
        <div>
          <label htmlFor="tipo-recorrido" className="block font-semibold">Tipo de recorrido</label>
          <select id="tipo-recorrido" disabled className={campo} defaultValue="circular">
            <option value="circular">Circular</option>
          </select>
          <p className="mt-1 text-sm">En el prototipo todas las rutas son circulares.</p>
        </div>
        {edita ? (
          <div className="md:col-span-2">
            <label htmlFor="descripcion-ruta" className="block font-semibold">Descripción (opcional)</label>
            <input id="descripcion-ruta" type="text" className={campo} {...register("descripcion")} />
          </div>
        ) : (
          <div>
            <label htmlFor="variante-ruta" className="block font-semibold">Variante de (opcional)</label>
            <select id="variante-ruta" className={campo} {...register("rutaPrincipalId")}>
              <option value="">Ninguna: es una ruta principal</option>
              {rutas.filter((r) => !r.esVariante).map((r) => <option key={r.id} value={r.id}>{r.nombre}</option>)}
            </select>
          </div>
        )}
      </div>

      {!edita ? (
        <fieldset>
          <legend className="font-semibold">Empresas que la operan</legend>
          <p className="text-sm">Cada empresa tiene su propio horario y frecuencia. Los códigos son opcionales.</p>
          <div className="mt-2 space-y-2">
            {empresas.map((e) => {
              const marcada = e.id in elegidas;
              return (
                <div key={e.id} className="flex flex-wrap items-center gap-3 rounded bg-fondo px-3 py-2">
                  <label className="flex min-h-11 min-w-44 items-center gap-2 font-semibold">
                    <input type="checkbox" className="size-5" checked={marcada} onChange={(ev) => alternarEmpresa(e.id, ev.target.checked)} />
                    {e.nombre}
                  </label>
                  {marcada ? (
                    <>
                      <label className="text-sm">
                        Código público
                        <input type="text" maxLength={20} className="ml-2 min-h-11 w-28 rounded border border-tinta/40 bg-white px-2"
                          value={elegidas[e.id]?.codigoPublico ?? ""}
                          onChange={(ev) => setElegidas((s) => ({ ...s, [e.id]: { codigoPublico: ev.target.value, codigoInterno: s[e.id]?.codigoInterno ?? "" } }))} />
                      </label>
                      <label className="text-sm">
                        Código interno
                        <input type="text" maxLength={20} className="ml-2 min-h-11 w-28 rounded border border-tinta/40 bg-white px-2"
                          value={elegidas[e.id]?.codigoInterno ?? ""}
                          onChange={(ev) => setElegidas((s) => ({ ...s, [e.id]: { codigoInterno: ev.target.value, codigoPublico: s[e.id]?.codigoPublico ?? "" } }))} />
                      </label>
                    </>
                  ) : null}
                </div>
              );
            })}
          </div>
          {errorEmpresas ? <p className={error}>{errorEmpresas}</p> : null}
        </fieldset>
      ) : null}

      <fieldset>
        <legend className="font-semibold">Paraderos del recorrido</legend>
        <p className="mb-2 text-sm">El trazado une los paraderos en el orden que elijas y vuelve al primero.</p>
        <SelectorParaderos paraderos={paraderos} valor={paraderoIds} onCambio={(ids) => { setParaderoIds(ids); setErrorParaderos(null); }} />
        {errorParaderos ? <p className={error}>{errorParaderos}</p> : null}
      </fieldset>

      {errorServidor ? <p role="alert" className="rounded bg-ladrillo-claro p-3 text-ladrillo">Error: {errorServidor}</p> : null}

      <div className="flex gap-3">
        <button type="submit" disabled={guardar.isPending}
          className="min-h-11 rounded bg-verde px-5 font-semibold text-white hover:bg-verde-oscuro disabled:opacity-60">
          {guardar.isPending ? "Guardando…" : edita ? "Guardar cambios" : "Registrar ruta"}
        </button>
        <button type="button" onClick={onCancelar} className="min-h-11 rounded border border-tinta px-5 font-semibold">Cancelar</button>
      </div>

      <Modal abierto={compartida} titulo="Ruta compartida" onCerrar={() => setCompartida(false)}
        acciones={
          <>
            <button type="button" onClick={() => setCompartida(false)} className="min-h-11 rounded border border-tinta px-5 font-semibold">Cancelar</button>
            <button type="button" disabled={guardar.isPending}
              onClick={() => handleSubmit((d) => guardar.mutate({ d, confirmar: true }))()}
              className="min-h-11 rounded bg-verde px-5 font-semibold text-white">Confirmar compartida</button>
          </>
        }>
        Esta ruta ya la opera otra empresa. Si también la opera esta empresa, cada una tendrá su propio horario y frecuencia.
      </Modal>
    </form>
  );
}
