import logo from "@/images/logoAppBusetas.avif";

/**
 * Logo de BusetasApp. Siempre sobre un fondo claro para que se lea también en la barra oscura.
 * Se usa <img> y no next/image porque Turbopack no lee las dimensiones de un AVIF y la imagen ya es liviana (11 KB).
 */
export function Logo({ alto = 40, prioridad = false }: { alto?: number; prioridad?: boolean }) {
  return (
    // eslint-disable-next-line @next/next/no-img-element
    <img src={logo.src} alt="BusetasApp" height={alto} fetchPriority={prioridad ? "high" : "auto"} style={{ height: alto, width: "auto" }} />
  );
}
