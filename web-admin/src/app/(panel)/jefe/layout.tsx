"use client";
import { BannerError } from "@/componentes/BannerError";
import { Vacio } from "@/componentes/Vacio";
import { fijarEmpresaElegida, useEmpresaElegida } from "@/lib/contexto-empresa";
import { useEmpresasPublicas } from "@/lib/jefe";
import { usePerfil } from "@/lib/perfil";

/**
 * Paneles del jefe. El administrador (BR-07) ve un selector de empresa y todas las peticiones del
 * jefe llevan ese `empresaId`. El jefe real no ve el selector y nunca envía `empresaId`.
 */
export default function JefeLayout({ children }: { children: React.ReactNode }) {
  const { data: perfil } = usePerfil();
  const elegida = useEmpresaElegida();
  const empresas = useEmpresasPublicas();
  const esAdmin = perfil?.rol === "administrador";

  if (!esAdmin) return <>{children}</>;

  return (
    <div>
      <div className="mb-6 flex flex-wrap items-center gap-3 rounded-lg border border-borde bg-white p-4">
        <label htmlFor="empresa-activa" className="font-semibold">Empresa</label>
        <select
          id="empresa-activa"
          className="min-h-11 min-w-56 rounded border border-tinta/40 bg-white px-3"
          value={elegida?.id ?? ""}
          onChange={(e) => {
            const emp = empresas.data?.find((x) => x.id === e.target.value);
            fijarEmpresaElegida(emp ? { id: emp.id, nombre: emp.nombre } : null);
          }}
        >
          <option value="">Elige una empresa…</option>
          {empresas.data?.map((e) => (
            <option key={e.id} value={e.id}>{e.nombre}</option>
          ))}
        </select>
        <span className="text-sm">Como administrador ves el panel del jefe de la empresa que elijas.</span>
      </div>
      {empresas.isError ? (
        <div className="mb-4">
          <BannerError mensaje={empresas.error.message} onReintentar={() => empresas.refetch()} />
        </div>
      ) : null}
      {elegida ? (
        children
      ) : (
        <Vacio titulo="Elige una empresa" causa="Estas pantallas muestran los datos de una sola empresa." accion={<span>Usa el selector de arriba.</span>} />
      )}
    </div>
  );
}
