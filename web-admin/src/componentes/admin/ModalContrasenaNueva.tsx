"use client";
import { ModalSecretoUnico } from "./ModalSecretoUnico";

type Props = {
  /** Contraseña devuelta una sola vez por `POST /admin/usuarios`. `null` = cerrado. */
  contrasena: string | null;
  correo: string;
  onCerrar: () => void;
};

/** Contraseña de una cuenta recién creada (escrita por el administrador o generada por el backend). */
export function ModalContrasenaNueva({ contrasena, correo, onCerrar }: Props) {
  return (
    <ModalSecretoUnico
      secreto={contrasena}
      titulo="Contraseña de la cuenta nueva"
      advertencia="Esta contraseña se muestra una sola vez. Cópiala y compártela en privado con el usuario."
      detalle={`Cuenta ${correo}:`}
      confirmacion="Ya guardé la contraseña en un lugar seguro"
      onCerrar={onCerrar}
    />
  );
}
