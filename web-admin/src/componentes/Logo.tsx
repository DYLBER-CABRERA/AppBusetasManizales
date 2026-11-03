import logo from "@/images/logoAppBusetas.png";

/**
 * Logo de BusetasApp: solo el recuadro verde, con esquinas transparentes (sirve sobre fondo claro u oscuro).
 * Se usa <img> y no next/image porque la imagen ya es liviana.
 */
export function Logo({ alto = 40, prioridad = false }: { alto?: number; prioridad?: boolean }) {
  return (
    // eslint-disable-next-line @next/next/no-img-element
    <img
      src={logo.src}
      alt="BusetasApp"
      height={alto}
      fetchPriority={prioridad ? "high" : "auto"}
      className="shrink-0"
      style={{ height: alto, width: "auto", borderRadius: "22%" }}
    />
  );
}
