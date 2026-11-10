import { Suspense } from "react";
import { Esqueleto } from "@/componentes/Esqueleto";
import { PantallaRutas } from "@/componentes/secretaria/PantallaRutas";

export default function Page() {
  // PantallaRutas lee `?ver=<id>` (enlace desde la importación), que exige Suspense en Next.
  return (
    <Suspense fallback={<Esqueleto filas={5} />}>
      <PantallaRutas />
    </Suspense>
  );
}
