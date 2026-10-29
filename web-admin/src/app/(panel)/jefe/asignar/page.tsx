import { Suspense } from "react";
import { Esqueleto } from "@/componentes/Esqueleto";
import { PantallaAsignar } from "@/componentes/jefe/PantallaAsignar";

export default function Page() {
  return (
    <Suspense fallback={<Esqueleto filas={5} />}>
      <PantallaAsignar />
    </Suspense>
  );
}
