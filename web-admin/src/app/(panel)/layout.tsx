"use client";
import Link from "next/link";
import { useEffect } from "react";
import { usePathname, useRouter } from "next/navigation";
import { BannerEjemplo } from "@/componentes/BannerEjemplo";
import { BannerError } from "@/componentes/BannerError";
import { Esqueleto } from "@/componentes/Esqueleto";
import { Vacio } from "@/componentes/Vacio";
import { cerrarSesion, puedeEntrar, rutaInicial } from "@/lib/auth";
import { ErrorApi, MENSAJE_SIN_PERMISO } from "@/lib/errores";
import { ETIQUETA_ROL, gruposDeRol } from "@/lib/navegacion";
import { useEstadoDemo } from "@/lib/demo";
import { usePerfil } from "@/lib/perfil";

export default function PanelLayout({ children }: { children: React.ReactNode }) {
  const ruta = usePathname();
  const router = useRouter();
  const { data: perfil, error, isPending, refetch } = usePerfil();
  // El Panel de demo solo existe si GET /demo/estado responde 200 (MODO_DEMO=true).
  const demo = useEstadoDemo({ habilitado: perfil?.rol === "administrador" });

  const sinSesion = !isPending && !perfil && (!(error instanceof ErrorApi) || error.estado === 401);
  useEffect(() => {
    if (sinSesion) router.replace("/login");
  }, [sinSesion, router]);

  async function salir() {
    await cerrarSesion();
    router.replace("/login");
  }

  if (isPending) {
    return (
      <div className="p-8">
        <Esqueleto filas={6} />
      </div>
    );
  }
  if (!perfil) {
    if (sinSesion) return null;
    return (
      <div className="p-8">
        <BannerError mensaje={error instanceof Error ? error.message : "Error"} onReintentar={() => refetch()} />
      </div>
    );
  }

  const grupos = gruposDeRol(perfil.rol).map((g) => ({
    ...g,
    secciones: g.secciones.filter((s) => s.href !== "/admin/demo" || demo.isSuccess),
  }));
  const permitido = puedeEntrar(perfil.rol, ruta);

  return (
    <div className="flex min-h-screen flex-col">
      <BannerEjemplo />
      <header className="flex items-center justify-between bg-tinta px-6 py-3 text-white">
        <span className="font-titulo text-lg font-bold">BusetasApp · Gestión</span>
        <div className="flex items-center gap-4 text-sm">
          <div className="text-right leading-tight">
            <p className="font-semibold">
              {perfil.nombre?.trim() || perfil.correo} · {ETIQUETA_ROL[perfil.rol] ?? perfil.rol}
              {perfil.empresaNombre ? ` · ${perfil.empresaNombre}` : ""}
            </p>
            {perfil.nombre?.trim() ? <p className="text-xs text-white/85">{perfil.correo}</p> : null}
          </div>
          <button type="button" onClick={salir}
            className="min-h-11 rounded border border-white px-4 font-semibold hover:bg-white/15">
            Cerrar sesión
          </button>
        </div>
      </header>
      <div className="flex flex-1">
        <nav aria-label="Secciones" className="w-64 shrink-0 border-r border-borde bg-white p-4">
          {grupos.map((g) => (
            <div key={g.clave} className="mb-5">
              <p className="mb-1 text-xs font-bold uppercase tracking-wide">{g.titulo}</p>
              <ul>
                {g.secciones.map((s) => {
                  const activa = ruta === s.href;
                  return (
                    <li key={s.href}>
                      <Link href={s.href} aria-current={activa ? "page" : undefined}
                        className={`flex min-h-11 items-center rounded px-3 ${
                          activa ? "bg-verde font-semibold text-white" : "hover:bg-fondo"
                        }`}>
                        {s.etiqueta}
                      </Link>
                    </li>
                  );
                })}
              </ul>
            </div>
          ))}
        </nav>
        <main className="flex-1 p-8">
          {permitido ? (
            children
          ) : (
            <Vacio
              titulo={MENSAJE_SIN_PERMISO}
              causa="Tu rol no incluye esta sección."
              accion={
                <Link href={rutaInicial(perfil.rol)} className="font-semibold text-verde underline">
                  Ir a mi panel
                </Link>
              }
            />
          )}
        </main>
      </div>
    </div>
  );
}
