"use client";
import type { components } from "@/lib/tipos-api";
import { ModalSecretoUnico } from "./ModalSecretoUnico";

type CredencialCreada = components["schemas"]["CredencialGpsCreada"];

type Props = {
  credencial: CredencialCreada | null;
  empresa: string;
  /** Solo se llama desde el botón «Cerrar», una vez copiada o confirmada la clave. */
  onCerrar: () => void;
};

/** Clave de una fuente GPS: se muestra una sola vez (ver `ModalSecretoUnico`). */
export function ModalClaveNueva({ credencial, empresa, onCerrar }: Props) {
  return (
    <ModalSecretoUnico
      secreto={credencial?.clave ?? null}
      titulo="Clave nueva"
      advertencia="Copia la clave ahora. No podrás verla otra vez."
      detalle={`Fuente «${credencial?.nombre}» de ${empresa}:`}
      confirmacion="Ya guardé la clave en un lugar seguro"
      onCerrar={onCerrar}
    />
  );
}
