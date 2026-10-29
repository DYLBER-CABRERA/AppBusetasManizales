"use client";
import { useMutation, useQueryClient } from "@tanstack/react-query";
import { useEffect, useState } from "react";
import { BannerError } from "@/componentes/BannerError";
import { Esqueleto } from "@/componentes/Esqueleto";
import { useToast } from "@/componentes/Toast";
import { Vacio } from "@/componentes/Vacio";
import {
  CLAVE_ESTADO_DEMO, enviarEscenario, useBusetasEnVivo, useEmpresasReales, useEstadoDemo, useRutasReales,
  type EscenarioDemo,
} from "@/lib/demo";
import { ErrorApi } from "@/lib/errores";
import { haceTexto, horaBogota } from "@/lib/fechas";
import { MapaDemo } from "./MapaDemo";

const boton = "min-h-11 rounded border border-verde px-4 font-semibold text-verde hover:bg-fondo disabled:opacity-50";
const botonPrimario = "min-h-11 rounded bg-verde px-4 font-semibold text-white hover:bg-verde-oscuro disabled:opacity-50";
const campo = "min-h-11 rounded border border-tinta/40 bg-white px-3";

/** Texto del toast: el mismo verbo del botón. */
function textoToast(e: EscenarioDemo): string {
  switch (e.tipo) {
    case "perder_senal": return "Señal perdida";
    case "restaurar_senal": return "Señal restaurada";
    case "activar_gps_empresa": return e.activo === false ? "GPS apagado" : "GPS activado";
    case "desvio": return "Desvío iniciado";
    case "fijar_hora": return e.hora ? "Hora fijada" : "Hora real restaurada";
    case "acelerar": return "Velocidad aplicada";
    case "reiniciar_simulacion": return "Simulación reiniciada";
  }
}

function useAhora(ms: number) {
  const [ahora, setAhora] = useState(() => Date.now());
  useEffect(() => {
    const t = setInterval(() => setAhora(Date.now()), ms);
    return () => clearInterval(t);
  }, [ms]);
  return ahora;
}

export function PantallaDemo() {
  const cliente = useQueryClient();
  const toast = useToast();
  const ahora = useAhora(1000);

  const estado = useEstadoDemo({ habilitado: true, intervaloMs: 3000 });
  const empresas = useEmpresasReales(true);
  const rutas = useRutasReales(true);
  const rutaIds = rutas.data?.map((r) => r.id) ?? [];
  const vivo = useBusetasEnVivo(rutaIds);

  const [errorAccion, setErrorAccion] = useState<string | null>(null);
  const [empresaId, setEmpresaId] = useState("");
  const [busetaDesvio, setBusetaDesvio] = useState("");
  const [duracion, setDuracion] = useState("60");
  const [hora, setHora] = useState("");
  const [factor, setFactor] = useState("1");

  const escenario = useMutation({
    mutationFn: enviarEscenario,
    onSuccess: (nuevo, enviado) => {
      setErrorAccion(null);
      cliente.setQueryData(CLAVE_ESTADO_DEMO, nuevo);
      toast(textoToast(enviado));
    },
    onError: (e) => setErrorAccion(e.message),
  });
  const lanzar = (e: EscenarioDemo) => escenario.mutate(e);

  if (estado.isPending) {
    return <Esqueleto filas={6} />;
  }
  if (estado.error instanceof ErrorApi && estado.error.estado === 404) {
    return (
      <Vacio
        titulo="El modo de demostración no está activo"
        causa="El servidor respondió 404 en /demo/estado porque MODO_DEMO no es true."
        accion={<span>Activa <code>MODO_DEMO=true</code> en el backend y reinícialo.</span>}
      />
    );
  }
  const datos = estado.data;

  const busetas = [...(datos?.busetas ?? [])].sort((a, b) => a.numeroLateral.localeCompare(b.numeroLateral));
  const vivas = new Map(vivo.busetas.map((b) => [b.numeroLateral, b]));
  const nombreRuta = (id: string) => rutas.data?.find((r) => r.id === id)?.nombre ?? "—";
  const idDeEmpresa = (nombre: string) => empresas.data?.find((e) => e.nombre === nombre)?.id;
  const servi = empresas.data?.find((e) => e.nombre === "Serviturismo");
  const enMapa = vivo.busetas;
  const ocupado = escenario.isPending;

  return (
    <section className="space-y-6">
      <div className="flex flex-wrap items-end justify-between gap-4">
        <h1 className="text-2xl font-bold">Panel de demo</h1>
        {datos ? (
          <p className="text-sm" aria-live="polite">
            Hora simulada:{" "}
            <strong>{datos.relojSimulado ? horaBogota(datos.relojSimulado) : "hora real"}</strong>
            {" · "}Velocidad: <strong>{datos.factor}×</strong>
          </p>
        ) : null}
      </div>

      {estado.isError ? <BannerError mensaje={estado.error.message} onReintentar={() => estado.refetch()} /> : null}
      {errorAccion ? <p role="alert" className="rounded bg-ladrillo-claro p-3 text-ladrillo">Error: {errorAccion}</p> : null}

      <div>
        <div className="mb-2 flex items-center justify-between text-sm">
          <h2 className="font-bold">Busetas en vivo</h2>
          <span>
            {vivo.total === 0
              ? "Sin rutas cargadas"
              : vivo.conectadas === vivo.total
                ? "Tiempo real conectado"
                : "Tiempo real no disponible: actualizando cada 5 s"}
          </span>
        </div>
        {rutas.isError ? (
          <BannerError mensaje={rutas.error.message} onReintentar={() => rutas.refetch()} />
        ) : (
          <MapaDemo busetas={enMapa} />
        )}
        {enMapa.length === 0 && !rutas.isError ? (
          <p className="mt-2 text-sm">No hay busetas en servicio en este momento. Revisa la hora simulada o reinicia la simulación.</p>
        ) : null}
      </div>

      <div className="grid gap-4 lg:grid-cols-2">
        <fieldset className="rounded-lg border border-borde bg-white p-4">
          <legend className="px-1 font-bold">Por empresa</legend>
          <label htmlFor="empresa-demo" className="block text-sm font-semibold">Empresa</label>
          <select id="empresa-demo" className={`${campo} w-full`} value={empresaId} onChange={(e) => setEmpresaId(e.target.value)}>
            <option value="">Elige una empresa…</option>
            {empresas.data?.map((e) => <option key={e.id} value={e.id}>{e.nombre}</option>)}
          </select>
          <div className="mt-3 flex flex-wrap gap-2">
            <button type="button" className={boton} disabled={!empresaId || ocupado}
              onClick={() => lanzar({ tipo: "perder_senal", empresaId })}>Perder señal</button>
            <button type="button" className={boton} disabled={!empresaId || ocupado}
              onClick={() => lanzar({ tipo: "restaurar_senal", empresaId })}>Restaurar</button>
            <button type="button" className={boton} disabled={!empresaId || ocupado}
              onClick={() => lanzar({ tipo: "activar_gps_empresa", empresaId, activo: false })}>Apagar GPS</button>
          </div>
          <button type="button" className={`${botonPrimario} mt-3`} disabled={!servi || ocupado}
            onClick={() => servi && lanzar({ tipo: "activar_gps_empresa", empresaId: servi.id, activo: true })}>
            Activar GPS de Serviturismo
          </button>
        </fieldset>

        <fieldset className="rounded-lg border border-borde bg-white p-4">
          <legend className="px-1 font-bold">Desvío</legend>
          <div className="flex flex-wrap items-end gap-3">
            <div>
              <label htmlFor="buseta-desvio" className="block text-sm font-semibold">Buseta</label>
              <select id="buseta-desvio" className={campo} value={busetaDesvio} onChange={(e) => setBusetaDesvio(e.target.value)}>
                <option value="">Elige…</option>
                {busetas.map((b) => <option key={b.numeroLateral} value={b.numeroLateral}>{b.numeroLateral} · {b.empresa}</option>)}
              </select>
            </div>
            <div>
              <label htmlFor="duracion" className="block text-sm font-semibold">Duración (s)</label>
              <input id="duracion" type="number" min={1} className={`${campo} w-28`} value={duracion} onChange={(e) => setDuracion(e.target.value)} />
            </div>
            <button type="button" className={botonPrimario} disabled={!busetaDesvio || Number(duracion) < 1 || ocupado}
              onClick={() => lanzar({ tipo: "desvio", numeroLateral: busetaDesvio, duracionS: Math.round(Number(duracion)) })}>
              Desvío
            </button>
          </div>
        </fieldset>

        <fieldset className="rounded-lg border border-borde bg-white p-4">
          <legend className="px-1 font-bold">Hora simulada</legend>
          <div className="flex flex-wrap items-end gap-3">
            <div>
              <label htmlFor="hora" className="block text-sm font-semibold">Hora (HH:MM)</label>
              <input id="hora" type="time" className={campo} value={hora} onChange={(e) => setHora(e.target.value)} />
            </div>
            <button type="button" className={botonPrimario} disabled={!hora || ocupado}
              onClick={() => lanzar({ tipo: "fijar_hora", hora })}>Fijar hora</button>
            <button type="button" className={boton} disabled={ocupado}
              onClick={() => lanzar({ tipo: "fijar_hora", hora: null })}>Volver a la hora real</button>
          </div>
        </fieldset>

        <fieldset className="rounded-lg border border-borde bg-white p-4">
          <legend className="px-1 font-bold">Velocidad y reinicio</legend>
          <div className="flex flex-wrap items-end gap-3">
            <div>
              <label htmlFor="factor" className="block text-sm font-semibold">Acelerar (0,5 a 5×)</label>
              <input id="factor" type="number" min={0.5} max={5} step={0.5} className={`${campo} w-28`} value={factor}
                onChange={(e) => setFactor(e.target.value)} />
            </div>
            <button type="button" className={botonPrimario}
              disabled={!(Number(factor) >= 0.5 && Number(factor) <= 5) || ocupado}
              onClick={() => lanzar({ tipo: "acelerar", factor: Number(factor) })}>Acelerar</button>
            <button type="button" className={boton} disabled={ocupado}
              onClick={() => lanzar({ tipo: "reiniciar_simulacion" })}>Reiniciar simulación</button>
          </div>
          {!(Number(factor) >= 0.5 && Number(factor) <= 5) ? (
            <p className="mt-2 text-sm text-ladrillo">Escribe un valor entre 0,5 y 5.</p>
          ) : null}
        </fieldset>
      </div>

      <div className="overflow-x-auto rounded-lg border border-borde bg-white">
        <table className="w-full text-left">
          <caption className="p-3 text-left font-bold">Busetas simuladas</caption>
          <thead className="bg-fondo text-sm">
            <tr>
              <th scope="col" className="p-3">Lateral</th>
              <th scope="col" className="p-3">Empresa</th>
              <th scope="col" className="p-3">Ruta</th>
              <th scope="col" className="p-3">Emitiendo</th>
              <th scope="col" className="p-3">Última posición</th>
              <th scope="col" className="p-3">Señal</th>
              <th scope="col" className="p-3">Acciones</th>
            </tr>
          </thead>
          <tbody>
            {busetas.map((b) => {
              const v = vivas.get(b.numeroLateral);
              return (
                <tr key={b.numeroLateral} className="border-t border-borde">
                  <td className="p-3 font-bold">{b.numeroLateral}</td>
                  <td className="p-3">{b.empresa}</td>
                  <td className="p-3">{v ? nombreRuta(v.rutaId) : "—"}</td>
                  <td className="p-3">{b.emitiendo ? "Sí" : "No"}</td>
                  <td className="p-3">{b.ultimaPosicion ? haceTexto(b.ultimaPosicion, ahora) : "Sin posición"}</td>
                  <td className="p-3">{v ? (v.estado === "sin_senal" ? "Sin señal" : "Con señal") : "—"}</td>
                  <td className="p-3">
                    <div className="flex flex-wrap gap-2">
                      <button type="button" className={boton} disabled={ocupado}
                        onClick={() => lanzar({ tipo: "perder_senal", numeroLateral: b.numeroLateral })}>Perder señal</button>
                      <button type="button" className={boton} disabled={ocupado}
                        onClick={() => lanzar({ tipo: "restaurar_senal", numeroLateral: b.numeroLateral })}>Restaurar</button>
                    </div>
                  </td>
                </tr>
              );
            })}
            {busetas.length === 0 ? (
              <tr>
                <td colSpan={7} className="p-6 text-center">
                  No hay busetas simuladas. Reinicia la simulación o revisa las semillas del backend.
                </td>
              </tr>
            ) : null}
          </tbody>
        </table>
      </div>
      <p className="text-xs">
        Las busetas de Serviturismo no emiten hasta activar su GPS. {empresas.data && !idDeEmpresa("Serviturismo") ? "No se encontró la empresa Serviturismo." : ""}
      </p>
    </section>
  );
}
