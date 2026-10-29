"use client";
import { useMutation, useQueryClient, type QueryKey } from "@tanstack/react-query";
import { useState } from "react";
import { Modal } from "@/componentes/Modal";
import { useToast } from "@/componentes/Toast";
import { ErrorApi } from "@/lib/errores";
import { guardarTurnos, publicarRodamiento } from "@/lib/jefe";
import {
  aTurnoEntrada, etiquetaServicioTabla, filaDesdeTurno, frasesDeReemplazo, textoSolapamientos, turnoAEntrada,
  turnosVigentes, type Buseta, type Conductor, type Fila, type Rodamiento, type ServicioRuta,
} from "@/lib/rodamiento";
import { minutos } from "@/lib/fechas";

type Props = {
  rodamiento: Rodamiento;
  claveConsulta: QueryKey;
  servicios: ServicioRuta[];
  busetas: Buseta[];
  conductores: Conductor[];
  onRecargar: () => void;
};

const campo = "min-h-11 rounded border border-tinta/40 bg-white px-2";

export function TablaRodamiento({ rodamiento, claveConsulta, servicios, busetas, conductores, onRecargar }: Props) {
  const cliente = useQueryClient();
  const toast = useToast();
  const [filas, setFilas] = useState<Fila[]>(() => turnosVigentes(rodamiento).map(filaDesdeTurno));
  const [errores, setErrores] = useState<Record<string, string>>({});
  const [modalVersion, setModalVersion] = useState(false);
  const [reemplazos, setReemplazos] = useState<string[] | null>(null);
  const [errorGeneral, setErrorGeneral] = useState<string | null>(null);

  const editable = rodamiento.estado === "borrador";
  const guardados = turnosVigentes(rodamiento);
  const cambiado =
    JSON.stringify(filas.map(aTurnoEntrada)) !== JSON.stringify(guardados.map(turnoAEntrada));
  const advertencias = rodamiento.advertencias;
  const enConflicto = new Set(advertencias.flatMap((a) => a.turnoIds));
  const lateral = (id: string) => busetas.find((b) => b.id === id)?.numeroLateral ?? id;

  function cambiar(clave: string, parche: Partial<Fila>) {
    setFilas((fs) => fs.map((f) => (f.clave === clave ? { ...f, ...parche } : f)));
    setErrores((e) => {
      const { [clave]: _quitado, ...resto } = e;
      void _quitado;
      return resto;
    });
  }

  function validar(): boolean {
    const nuevos: Record<string, string> = {};
    for (const f of filas) {
      if (!f.servicioId || !f.busetaId || !f.horaSalida) nuevos[f.clave] = "Completa ruta, buseta y hora de salida.";
      else if (f.horaFin && minutos(f.horaFin) <= minutos(f.horaSalida)) nuevos[f.clave] = "El fin debe ser posterior a la salida.";
    }
    setErrores(nuevos);
    return Object.keys(nuevos).length === 0;
  }

  function alFallar(e: unknown) {
    if (e instanceof ErrorApi && e.esConflictoVersion) return setModalVersion(true);
    if (e instanceof ErrorApi && e.esConflictoNegocio) {
      const frases = frasesDeReemplazo(guardados, filas.map(aTurnoEntrada), { busetas, conductores });
      if (frases.length > 0) return setReemplazos(frases);
    }
    setErrorGeneral(e instanceof Error ? e.message : "No se pudo completar la acción.");
  }

  const guardar = useMutation({
    mutationFn: (confirmarReemplazo: boolean) =>
      guardarTurnos(rodamiento.rodamientoId, {
        turnos: filas.map(aTurnoEntrada), version: rodamiento.version, confirmarReemplazo,
      }),
    onSuccess: (nuevo) => {
      setReemplazos(null);
      setErrorGeneral(null);
      cliente.setQueryData(claveConsulta, nuevo);
      toast("Guardado");
    },
    onError: alFallar,
  });

  const publicar = useMutation({
    mutationFn: () => publicarRodamiento(rodamiento.rodamientoId, rodamiento.version),
    onSuccess: async () => {
      setErrorGeneral(null);
      await cliente.invalidateQueries({ queryKey: claveConsulta });
      toast("Publicado");
    },
    onError: (e) => {
      alFallar(e);
      void cliente.invalidateQueries({ queryKey: claveConsulta });
    },
  });

  function corregir(turnoIds: string[]) {
    const fila = filas.find((f) => f.id && turnoIds.includes(f.id));
    if (fila) document.getElementById(`salida-${fila.clave}`)?.focus();
  }

  const bloqueoPublicar = !editable
    ? null
    : cambiado
      ? "Guarda los cambios para poder publicar."
      : advertencias.length > 0
        ? "Corrige el solapamiento para poder publicar."
        : null;

  return (
    <div>
      {editable && advertencias.length > 0 ? (
        <div role="alert" className="mb-4 rounded-lg border border-amarillo bg-aviso p-4">
          <p className="font-bold">{textoSolapamientos(advertencias.length)}</p>
          {advertencias.map((a, i) => (
            <div key={i} className="mt-2 flex items-start justify-between gap-4">
              <p>{a.mensaje}</p>
              <button type="button" onClick={() => corregir(a.turnoIds)}
                className="min-h-11 shrink-0 rounded border border-tinta bg-white px-4 font-semibold hover:bg-fondo">
                Corregir
              </button>
            </div>
          ))}
        </div>
      ) : null}

      {errorGeneral ? (
        <p role="alert" className="mb-4 rounded bg-ladrillo-claro p-3 text-ladrillo">Error: {errorGeneral}</p>
      ) : null}

      <div className="overflow-x-auto rounded-lg border border-borde bg-white">
        <table className="w-full text-left">
          <caption className="sr-only">Turnos del rodamiento</caption>
          <thead className="bg-fondo text-sm">
            <tr>
              <th scope="col" className="p-3">Buseta</th>
              <th scope="col" className="p-3">Ruta</th>
              <th scope="col" className="p-3">Conductor</th>
              <th scope="col" className="p-3">Salida</th>
              <th scope="col" className="p-3">Fin estimado</th>
              <th scope="col" className="p-3"><span className="sr-only">Estado</span></th>
            </tr>
          </thead>
          <tbody>
            {filas.map((f) => {
              const conflicto = f.id !== null && enConflicto.has(f.id);
              const err = errores[f.clave];
              return (
                <tr key={f.clave} id={`fila-${f.clave}`}
                  className={`border-t border-borde align-top ${conflicto ? "bg-ladrillo-claro" : ""}`}>
                  <td className="p-3">
                    {editable ? (
                      <select aria-label="Buseta" className={campo} value={f.busetaId}
                        onChange={(e) => cambiar(f.clave, { busetaId: e.target.value })}>
                        <option value="">—</option>
                        {busetas.map((b) => <option key={b.id} value={b.id}>{b.numeroLateral}</option>)}
                      </select>
                    ) : <strong>{lateral(f.busetaId)}</strong>}
                  </td>
                  <td className="p-3">
                    {editable ? (
                      <select aria-label="Ruta" className={campo} value={f.servicioId}
                        onChange={(e) => cambiar(f.clave, { servicioId: e.target.value })}>
                        <option value="">—</option>
                        {servicios.map((s) => <option key={s.id} value={s.id}>{etiquetaServicioTabla(s)}</option>)}
                      </select>
                    ) : etiquetaServicioTabla(servicios.find((s) => s.id === f.servicioId) ?? ({ rutaNombre: "Ruta" } as ServicioRuta))}
                  </td>
                  <td className="p-3">
                    {editable ? (
                      <select aria-label="Conductor" className={campo} value={f.conductorId}
                        onChange={(e) => cambiar(f.clave, { conductorId: e.target.value })}>
                        <option value="">Sin conductor</option>
                        {conductores.map((c) => <option key={c.id} value={c.id}>{c.nombre}</option>)}
                      </select>
                    ) : conductores.find((c) => c.id === f.conductorId)?.nombre ?? "Sin conductor"}
                  </td>
                  <td className="p-3">
                    {editable ? (
                      <input id={`salida-${f.clave}`} aria-label="Hora de salida" type="time" className={campo}
                        value={f.horaSalida} onChange={(e) => cambiar(f.clave, { horaSalida: e.target.value })} />
                    ) : f.horaSalida}
                  </td>
                  <td className="p-3">
                    {editable ? (
                      <input aria-label="Hora de fin estimada" type="time" className={campo}
                        value={f.horaFin} onChange={(e) => cambiar(f.clave, { horaFin: e.target.value })} />
                    ) : f.horaFin}
                  </td>
                  <td className="p-3 text-sm">
                    {conflicto ? <strong className="text-ladrillo">Solapamiento</strong> : null}
                    {err ? <p role="alert" className="text-ladrillo">{err}</p> : null}
                    {editable ? (
                      <button type="button" onClick={() => setFilas((fs) => fs.filter((x) => x.clave !== f.clave))}
                        className="mt-1 block min-h-11 font-semibold text-verde underline">
                        Quitar
                      </button>
                    ) : null}
                  </td>
                </tr>
              );
            })}
          </tbody>
        </table>
      </div>

      {rodamiento.estado === "publicado" ? (
        <p className="mt-4 font-semibold">Este rodamiento ya está publicado.</p>
      ) : (
        <div className="mt-6 flex flex-wrap items-center gap-4">
          <button type="button" disabled={!cambiado || guardar.isPending}
            onClick={() => { if (validar()) guardar.mutate(false); }}
            className="min-h-11 rounded border border-verde px-5 font-semibold text-verde hover:bg-fondo disabled:opacity-50">
            {guardar.isPending ? "Guardando…" : "Guardar borrador"}
          </button>
          <button type="button" disabled={bloqueoPublicar !== null || publicar.isPending}
            aria-describedby="ayuda-publicar" onClick={() => publicar.mutate()}
            className="min-h-11 rounded bg-verde px-5 font-semibold text-white hover:bg-verde-oscuro disabled:cursor-not-allowed disabled:opacity-50">
            {publicar.isPending ? "Publicando…" : "Publicar rodamiento"}
          </button>
          <span id="ayuda-publicar" className="text-sm">{bloqueoPublicar}</span>
        </div>
      )}

      <Modal abierto={modalVersion} titulo="Alguien más cambió esto"
        onCerrar={() => setModalVersion(false)}
        acciones={<button type="button" onClick={() => { setModalVersion(false); onRecargar(); }}
          className="min-h-11 rounded bg-verde px-5 font-semibold text-white">Recargar</button>}>
        Alguien más cambió esto. Recarga para ver los cambios.
      </Modal>

      <Modal abierto={reemplazos !== null} titulo="Reemplazar asignación" onCerrar={() => setReemplazos(null)}
        acciones={
          <>
            <button type="button" onClick={() => setReemplazos(null)}
              className="min-h-11 rounded border border-tinta px-5 font-semibold">Cancelar</button>
            <button type="button" onClick={() => guardar.mutate(true)}
              className="min-h-11 rounded bg-verde px-5 font-semibold text-white">Reemplazar</button>
          </>
        }>
        {reemplazos?.map((f, i) => <p key={i} className="mb-2">{f}</p>)}
      </Modal>
    </div>
  );
}
