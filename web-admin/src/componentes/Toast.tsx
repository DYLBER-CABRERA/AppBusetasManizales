"use client";
import { createContext, useCallback, useContext, useState, type ReactNode } from "react";

type Toast = { id: number; texto: string };
const Contexto = createContext<(texto: string) => void>(() => {});

/** Toast con el mismo verbo del botón (Publicar → "Publicado"). */
export const useToast = () => useContext(Contexto);

export function ProveedorToast({ children }: { children: ReactNode }) {
  const [toasts, setToasts] = useState<Toast[]>([]);
  const mostrar = useCallback((texto: string) => {
    const id = Date.now() + Math.random();
    setToasts((t) => [...t, { id, texto }]);
    setTimeout(() => setToasts((t) => t.filter((x) => x.id !== id)), 4000);
  }, []);
  return (
    <Contexto.Provider value={mostrar}>
      {children}
      <div aria-live="polite" className="fixed bottom-4 right-4 z-50 space-y-2">
        {toasts.map((t) => (
          <div key={t.id} className="rounded-lg bg-tinta px-4 py-3 font-semibold text-white shadow-lg">
            {t.texto}
          </div>
        ))}
      </div>
    </Contexto.Provider>
  );
}
