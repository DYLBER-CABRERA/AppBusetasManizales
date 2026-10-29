import { Suspense } from "react";
import { Esqueleto } from "@/componentes/Esqueleto";
import { PantallaRodamiento } from "@/componentes/jefe/PantallaRodamiento";

export default function Page() {
  return (
    <Suspense fallback={<Esqueleto filas={5} />}>
      <PantallaRodamiento />
    </Suspense>
  );
}
