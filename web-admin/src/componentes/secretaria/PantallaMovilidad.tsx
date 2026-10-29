"use client";
import { useMutation, useQueryClient } from "@tanstack/react-query";
import { useState } from "react";
import { BannerError } from "@/componentes/BannerError";
import { Esqueleto } from "@/componentes/Esqueleto";
import { Modal } from "@/componentes/Modal";
import { useToast } from "@/componentes/Toast";
import { Vacio } from "@/componentes/Vacio";
import {
  CLAVE_AVISOS_MOVILIDAD, publicarAviso, retirarAviso, useAvisosMovilidad, useParaderos, useRutas, type Aviso,
} from "@/lib/secretaria";

type Tipo = "cierre" | "desvio" | "obra" | "condicion";
const TIPOS: { valor: Tipo; etiqueta: string }[] = [
  { valor: "cierre", etiqueta: "Cierre" },
  { valor: "desvio", etiqueta: "Desvío" },
  { valor: "obra", etiqueta: "Obra" },
  { valor: "condicion", etiqueta: "Condición" },
];
const etiquetaTipo = (t: string | null | undefined) => TIPOS.find((x) => x.valor === t)?.etiqueta ?? "Aviso";

// PENDIENTE(decisión): la Secretaría no puede leer `longitud_max_aviso` (solo el administrador lee
// parámetros); se usa el valor por defecto (500). El backend valida de todos modos.
const LONGITUD_MAX_AVISO = 500;

const campo = "mt-1 min-h-11 w-full rounded border border-tinta/40 bg-white px-3";
const mensajeError = "mt-1 text-sm text-ladrillo";

/** `datetime-local` (hora de Bogotá, sin horario de verano) → ISO 8601 con zona. */
const aIso = (v: string) => (v ? `${v}:00-05:00` : null);

export function PantallaMovilidad() {
  const cliente = useQueryClient();
  const toast = useToast();
  const rutas = useRutas();
  const paraderos = useParaderos();
  const avisos = useAvisosMovilidad();

  const [tipo, setTipo] = useState<Tipo>("cierre");
  const [titulo, setTitulo] = useState("");
  const [cuerpo, setCuerpo] = useState("");
  const [rutaIds, setRutaIds] = useState<string[]>([]);
  const [paraderoIds, setParaderoIds] = useState<string[]>([]);
  const [filtro, setFiltro] = useState("");
  const [desde, setDesde] = useState("");
  const [hasta, setHasta] = useState("");
  const [errores, setErrores] = useState<Record<string, string>>({});
  const [errorServidor, setErrorServidor] = useState<string | null>(null);
  const [aRetirar, setARetirar] = useState<Aviso | null>(null);

  const publicar = useMutation({
    mutationFn: () =>
      publicarAviso({
        tipoCambio: tipo, titulo: titulo.trim(), cuerpo: cuerpo.trim(), rutaIds, paraderoIds,
        desde: aIso(desde), hasta: aIso(hasta),
      }),
    onSuccess: async () => {
      setTitulo(""); setCuerpo(""); setRutaIds([]); setParaderoIds([]); setDesde(""); setHasta("");
      setErrores({}); setErrorServidor(null);
      await cliente.invalidateQueries({ queryKey: CLAVE_AVISOS_MOVILIDAD });
      toast("Publicado");
    },
    onError: (e) => setErrorServidor(e.message),
  });

  const retirar = useMutation({
    mutationFn: (id: string) => retirarAviso(id),
    onSuccess: async () => {
      setARetirar(null);
      await cliente.invalidateQueries({ queryKey: CLAVE_AVISOS_MOVILIDAD });
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
    else if (cuerpo.trim().length > LONGITUD_MAX_AVISO) e.cuerpo = `El mensaje supera el máximo de ${LONGITUD_MAX_AVISO} caracteres.`;
    if (rutaIds.length === 0 && paraderoIds.length === 0) e.afectados = "Elige al menos una ruta o un paradero afectado.";
    if (desde && hasta && hasta <= desde) e.hasta = "La vigencia debe terminar después de que empieza.";
    setErrores(e);
    if (Object.keys(e).length === 0) publicar.mutate();
  }

  const alternar = (lista: string[], id: string) => (lista.includes(id) ? lista.filter((x) => x !== id) : [...lista, id]);
  const nombreRuta = (id: string) => rutas.data?.find((r) => r.id === id)?.nombre ?? "Ruta";
  const nombreParadero = (id: string) => paraderos.data?.find((p) => p.id === id)?.nombre ?? "Paradero";
  const paraderosVisibles = paraderos.data?.filter((p) => p.nombre.toLowerCase().includes(filtro.trim().toLowerCase())) ?? [];

  const cargando = rutas.isPending || paraderos.isPending;
  const fallo = [rutas, paraderos].find((q) => q.isError)?.error;

  return (
    <section className="space-y-6">
      <h1 className="text-2xl font-bold">Cambios de movilidad</h1>

      {fallo ? <BannerError mensaje={fallo.message} onReintentar={() => { void rutas.refetch(); void paraderos.refetch(); }} /> : null}
      {cargando && !fallo ? <Esqueleto filas={5} /> : null}

      {rutas.data && paraderos.data ? (
        <form noValidate onSubmit={enviar} className="space-y-5 rounded-lg border border-borde bg-white p-6">
          <div className="grid gap-4 md:grid-cols-2">
            <div>
              <label htmlFor="tipo-cambio" className="block font-semibold">Qué pasa</label>
              <select id="tipo-cambio" value={tipo} onChange={(e) => setTipo(e.target.value as Tipo)} className={campo}>
                {TIPOS.map((t) => <option key={t.valor} value={t.valor}>{t.etiqueta}</option>)}
              </select>
            </div>
            <div>
              <label htmlFor="titulo-cambio" className="block font-semibold">Título</label>
              <input id="titulo-cambio" type="text" value={titulo} aria-invalid={!!errores.titulo} className={campo}
                onChange={(e) => setTitulo(e.target.value)} />
              {errores.titulo ? <p className={mensajeError}>{errores.titulo}</p> : null}
            </div>
          </div>

          <div>
            <label htmlFor="mensaje-cambio" className="block font-semibold">Mensaje</label>
            <textarea id="mensaje-cambio" rows={3} value={cuerpo} aria-invalid={!!errores.cuerpo} aria-describedby="contador-cambio"
              className={`${campo} py-2`} onChange={(e) => setCuerpo(e.target.value)} />
            <p id="contador-cambio" className={`mt-1 text-sm ${cuerpo.length > LONGITUD_MAX_AVISO ? "text-ladrillo" : ""}`}>
              {cuerpo.length} de {LONGITUD_MAX_AVISO} caracteres
            </p>
            {errores.cuerpo ? <p className={mensajeError}>{errores.cuerpo}</p> : null}
          </div>

          <div className="grid gap-5 lg:grid-cols-2">
            <fieldset>
              <legend className="font-semibold">Rutas afectadas</legend>
              <div className="mt-1 space-y-1">
                {rutas.data.map((r) => (
                  <label key={r.id} className="flex min-h-11 items-center gap-2 rounded bg-fondo px-3">
                    <input type="checkbox" className="size-5" checked={rutaIds.includes(r.id)}
                      onChange={() => setRutaIds((l) => alternar(l, r.id))} />
                    {r.nombre}
                  </label>
                ))}
              </div>
            </fieldset>
            <fieldset>
              <legend className="font-semibold">Paraderos afectados</legend>
              <label htmlFor="filtro-afectados" className="sr-only">Buscar paradero</label>
              <input id="filtro-afectados" type="search" placeholder="Buscar paradero" value={filtro}
                onChange={(e) => setFiltro(e.target.value)} className={campo} />
              <div className="mt-1 max-h-52 space-y-1 overflow-y-auto">
                {paraderosVisibles.map((p) => (
                  <label key={p.id} className="flex min-h-11 items-center gap-2 rounded bg-fondo px-3">
                    <input type="checkbox" className="size-5" checked={paraderoIds.includes(p.id)}
                      onChange={() => setParaderoIds((l) => alternar(l, p.id))} />
                    {p.nombre}
                  </label>
                ))}
                {paraderosVisibles.length === 0 ? <p className="text-sm">Sin paraderos para mostrar.</p> : null}
              </div>
              {paraderoIds.length > 0 ? <p className="mt-1 text-sm">{paraderoIds.length} elegido(s).</p> : null}
            </fieldset>
          </div>
          {errores.afectados ? <p className={mensajeError}>{errores.afectados}</p> : null}

          <div className="grid gap-4 md:grid-cols-2">
            <div>
              <label htmlFor="desde-cambio" className="block font-semibold">Vigente desde (opcional)</label>
              <input id="desde-cambio" type="datetime-local" value={desde} className={campo} onChange={(e) => setDesde(e.target.value)} />
              <p className="mt-1 text-sm">Si lo dejas vacío, vale desde ahora.</p>
            </div>
            <div>
              <label htmlFor="hasta-cambio" className="block font-semibold">Vigente hasta (opcional)</label>
              <input id="hasta-cambio" type="datetime-local" value={hasta} className={campo} onChange={(e) => setHasta(e.target.value)} />
              {errores.hasta ? <p className={mensajeError}>{errores.hasta}</p> : <p className="mt-1 text-sm">Si lo dejas vacío, no vence.</p>}
            </div>
          </div>

          {errorServidor ? <p role="alert" className="rounded bg-ladrillo-claro p-3 text-ladrillo">Error: {errorServidor}</p> : null}

          <button type="submit" disabled={publicar.isPending}
            className="min-h-11 rounded bg-verde px-5 font-semibold text-white hover:bg-verde-oscuro disabled:opacity-60">
            {publicar.isPending ? "Publicando…" : "Publicar cambio"}
          </button>
        </form>
      ) : null}

      <div>
        <h2 className="mb-2 text-lg font-bold">Cambios publicados</h2>
        {avisos.isError ? <BannerError mensaje={avisos.error.message} onReintentar={() => avisos.refetch()} /> : null}
        {avisos.isPending ? <Esqueleto filas={2} /> : null}
        {avisos.data && avisos.data.length === 0 ? (
          <Vacio titulo="No hay cambios vigentes" causa="No hay avisos de movilidad publicados que estén vigentes." />
        ) : null}
        <ul className="space-y-3">
          {avisos.data?.map((a) => (
            <li key={a.id} className="flex items-start justify-between gap-4 rounded-lg border border-borde bg-white p-4">
              <div>
                <p className="font-bold">{etiquetaTipo(a.tipoCambio)} · {a.titulo}</p>
                <p className="text-sm">{a.cuerpo}</p>
                <p className="mt-1 text-xs">
                  {[...a.rutaIds.map(nombreRuta), ...a.paraderoIds.map(nombreParadero)].join(", ")}
                </p>
              </div>
              <button type="button" onClick={() => setARetirar(a)} aria-label={`Retirar ${a.titulo}`}
                className="min-h-11 shrink-0 rounded border border-ladrillo px-4 font-semibold text-ladrillo hover:bg-ladrillo-claro">
                Retirar
              </button>
            </li>
          ))}
        </ul>
      </div>

      <Modal abierto={aRetirar !== null} titulo="Retirar cambio" onCerrar={() => setARetirar(null)}
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
