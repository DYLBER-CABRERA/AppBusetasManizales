"use client";
import { zodResolver } from "@hookform/resolvers/zod";
import { useQueryClient } from "@tanstack/react-query";
import { useRouter } from "next/navigation";
import { useState } from "react";
import { useForm } from "react-hook-form";
import { z } from "zod";
import { BannerEjemplo } from "@/componentes/BannerEjemplo";
import { api, consultar } from "@/lib/api";
import { cerrarSesion, correoSesionEjemplo, hayCredencialesSupabase, iniciarSesion, rutaInicial } from "@/lib/auth";
import { PERFILES_EJEMPLO } from "@/lib/mocks";

const esquema = z.object({
  correo: z.string().min(1, "Escribe tu correo.").email("Escribe un correo válido."),
  contrasena: z.string().min(1, "Escribe tu contraseña."),
});
type Datos = z.infer<typeof esquema>;

export default function Login() {
  const router = useRouter();
  const cliente = useQueryClient();
  const [error, setError] = useState<string | null>(null);
  const modoEjemplo = !hayCredencialesSupabase();
  const { register, handleSubmit, formState: { errors, isSubmitting } } = useForm<Datos>({
    resolver: zodResolver(esquema),
  });

  async function enviar(d: Datos) {
    setError(null);
    try {
      await iniciarSesion(d.correo, d.contrasena);
      const perfil = await consultar(
        () => api.GET("/api/v1/yo"),
        () => {
          const p = PERFILES_EJEMPLO[correoSesionEjemplo() ?? ""];
          if (!p) throw new Error("Esa cuenta no existe en el modo de ejemplo.");
          return p;
        },
      );
      if (perfil.rol === "pasajero") {
        await cerrarSesion();
        setError("Esta aplicación es para el personal de gestión. Los pasajeros usan la app móvil o Telegram.");
        return;
      }
      cliente.setQueryData(["yo"], perfil);
      router.replace(rutaInicial(perfil.rol));
    } catch (e) {
      await cerrarSesion();
      setError(e instanceof Error ? e.message : "No se pudo iniciar sesión.");
    }
  }

  return (
    <>
      <BannerEjemplo />
      <main className="mx-auto mt-16 w-full max-w-md rounded-lg bg-white p-8 shadow">
        <h1 className="text-2xl font-bold">BusetasApp · Gestión</h1>
        <p className="mt-1 text-sm">Inicia sesión con tu cuenta de gestión.</p>
        {modoEjemplo ? (
          <p className="mt-3 rounded bg-aviso p-3 text-sm" role="note">
            Modo de ejemplo (sin Supabase configurado): no se verifica la contraseña. Prueba con
            {" "}<code>jefe@sideral.example</code>, <code>movilidad@alcaldia.example</code> o <code>admin@busetasapp.example</code>.
          </p>
        ) : null}
        <form onSubmit={handleSubmit(enviar)} noValidate className="mt-5 space-y-4">
          <div>
            <label htmlFor="correo" className="block font-semibold">Correo</label>
            <input id="correo" type="email" autoComplete="username" aria-invalid={!!errors.correo}
              className="mt-1 min-h-11 w-full rounded border border-tinta/40 px-3" {...register("correo")} />
            {errors.correo ? <p className="mt-1 text-sm text-ladrillo">{errors.correo.message}</p> : null}
          </div>
          <div>
            <label htmlFor="contrasena" className="block font-semibold">Contraseña</label>
            <input id="contrasena" type="password" autoComplete="current-password" aria-invalid={!!errors.contrasena}
              className="mt-1 min-h-11 w-full rounded border border-tinta/40 px-3" {...register("contrasena")} />
            {errors.contrasena ? <p className="mt-1 text-sm text-ladrillo">{errors.contrasena.message}</p> : null}
          </div>
          {error ? <p role="alert" className="rounded bg-ladrillo-claro p-3 text-sm text-ladrillo">Error: {error}</p> : null}
          <button type="submit" disabled={isSubmitting}
            className="min-h-11 w-full rounded bg-verde font-semibold text-white hover:bg-verde-oscuro disabled:opacity-60">
            {isSubmitting ? "Entrando…" : "Iniciar sesión"}
          </button>
        </form>
      </main>
    </>
  );
}
