"use client";
import Link from "next/link";
import { useSearchParams } from "next/navigation";
import { useState } from "react";
import { BannerError } from "@/componentes/BannerError";
import { Esqueleto } from "@/componentes/Esqueleto";
import { Vacio } from "@/componentes/Vacio";
import { useEmpresaElegida } from "@/lib/contexto-empresa";
import { DIAS_MAX_RODAMIENTO_ADELANTE, diaSemana, fechaLarga, hoyBogota, sumarDias } from "@/lib/fechas";
import { useBusetas, useClaveEmpresa, useConductores, useRodamiento, useServicios } from "@/lib/jefe";
import { usePerfil } from "@/lib/perfil";
import { AnularRodamiento } from "./AnularRodamiento";
import { TablaRodamiento } from "./TablaRodamiento";

export function PantallaRodamiento() {
  const params = useSearchParams();
  const hoy = hoyBogota();
  const maxima = sumarDias(hoy, DIAS_MAX_RODAMIENTO_ADELANTE);
  const pedida = params.get("fecha");
  const [fecha, setFecha] = useState(pedida && pedida >= hoy && pedida <= maxima ? pedida : sumarDias(hoy, 1));
  const [recarga, setRecarga] = useState(0);

  const { data: perfil } = usePerfil();
  const elegida = useEmpresaElegida();
  const empresa = elegida?.nombre ?? perfil?.empresaNombre ?? "";
  const clave = useClaveEmpresa();

  const rodamiento = useRodamiento(fecha);
  const servicios = useServicios();
  const busetas = useBusetas();
  const conductores = useConductores();
  const consultas = [rodamiento, servicios, busetas, conductores];
  const error = consultas.find((c) => c.isError)?.error;
  const cargando = consultas.some((c) => c.isPending);

  const r = rodamiento.data;
  const titulo =
    fecha === sumarDias(hoy, 1) ? "Rodamiento de mañana" : fecha === hoy ? "Rodamiento de hoy" : `Rodamiento del ${fechaLarga(fecha)}`;
  const subtitulo = [empresa, diaSemana(fecha), r?.estado].filter(Boolean).join(" · ");

  function reintentar() {
    consultas.forEach((c) => void c.refetch());
  }

  return (
    <section>
      <div className="mb-4 flex flex-wrap items-end justify-between gap-4">
        <div>
          <h1 className="text-2xl font-bold">{titulo}</h1>
          <p className="text-sm">{subtitulo}</p>
        </div>
        <div>
          <label htmlFor="fecha" className="block text-sm font-semibold">Fecha</label>
          <input id="fecha" type="date" min={hoy} max={maxima} value={fecha}
            onChange={(e) => { if (e.target.value >= hoy && e.target.value <= maxima) setFecha(e.target.value); }}
            className="min-h-11 rounded border border-tinta/40 bg-white px-3" />
          <p className="mt-1 text-xs">Desde hoy hasta {DIAS_MAX_RODAMIENTO_ADELANTE} días adelante.</p>
        </div>
      </div>

      {error ? (
        <div className="mb-4">
          <BannerError mensaje={error.message} onReintentar={reintentar} />
        </div>
      ) : null}

      {cargando && !error ? <Esqueleto filas={5} /> : null}

      {!cargando && r === null ? (
        <Vacio
          titulo="Todavía no hay rodamiento para esta fecha"
          causa="El borrador se crea al asignar el primer turno."
          accion={
            <Link href={`/jefe/asignar?fecha=${fecha}`} className="font-semibold text-verde underline">
              Asignar el primer turno
            </Link>
          }
        />
      ) : null}

      {r && servicios.data && busetas.data && conductores.data ? (
        <>
          <TablaRodamiento
            key={`${clave}-${r.rodamientoId}-${r.version}-${recarga}`}
            rodamiento={r}
            claveConsulta={["jefe", clave, "rodamiento", fecha]}
            servicios={servicios.data}
            busetas={busetas.data}
            conductores={conductores.data}
            onRecargar={() => {
              setRecarga((n) => n + 1);
              void rodamiento.refetch();
            }}
          />
          {r.estado === "borrador" ? (
            <p className="mt-6 text-sm">
              ¿Falta un turno?{" "}
              <Link href={`/jefe/asignar?fecha=${fecha}`} className="font-semibold text-verde underline">
                Asignar buseta y conductor
              </Link>
            </p>
          ) : null}
          {r.estado === "borrador" || r.estado === "publicado" ? (
            <AnularRodamiento rodamientoId={r.rodamientoId} version={r.version} claveConsulta={["jefe", clave, "rodamiento", fecha]}
              fechaTexto={fechaLarga(fecha)} onConflicto={() => { setRecarga((n) => n + 1); void rodamiento.refetch(); }} />
          ) : null}
        </>
      ) : null}
    </section>
  );
}
