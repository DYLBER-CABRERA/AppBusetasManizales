"use client";
import { MutationCache, QueryCache, QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { useRouter } from "next/navigation";
import { useState, type ReactNode } from "react";
import { ErrorApi } from "@/lib/errores";
import { ProveedorToast } from "./Toast";

export function Proveedores({ children }: { children: ReactNode }) {
  const router = useRouter();
  // 401 (sesión vencida) -> volver a /login
  const sesionVencida = (e: unknown) => {
    if (e instanceof ErrorApi && e.estado === 401 && !window.location.pathname.startsWith("/login")) {
      router.replace("/login");
    }
  };
  const [cliente] = useState(
    () =>
      new QueryClient({
        queryCache: new QueryCache({ onError: sesionVencida }),
        mutationCache: new MutationCache({ onError: sesionVencida }),
        defaultOptions: { queries: { retry: false, refetchOnWindowFocus: false } },
      }),
  );
  return (
    <QueryClientProvider client={cliente}>
      <ProveedorToast>{children}</ProveedorToast>
    </QueryClientProvider>
  );
}
