import { fireEvent, render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";
import { ModalContrasenaNueva } from "./ModalContrasenaNueva";

function montar(contrasena: string | null = "Clave-segura-1") {
  const onCerrar = vi.fn();
  render(<ModalContrasenaNueva contrasena={contrasena} correo="ana@empresa.example" onCerrar={onCerrar} />);
  const dialogo = document.querySelector("dialog") as HTMLDialogElement;
  return { onCerrar, dialogo, cerrar: () => screen.getByRole("button", { name: "Cerrar", hidden: true }) };
}

describe("Contraseña de la cuenta nueva (se muestra una sola vez)", () => {
  it("muestra la advertencia, el correo y la contraseña", () => {
    const { dialogo } = montar();
    expect(screen.getByText("Esta contraseña se muestra una sola vez. Cópiala y compártela en privado con el usuario.")).toBeTruthy();
    expect(screen.getByText("Cuenta ana@empresa.example:")).toBeTruthy();
    expect(screen.getByText("Clave-segura-1")).toBeTruthy();
    expect(dialogo.open).toBe(true);
  });

  it("no se cierra con Esc ni con clic fuera, y Cerrar espera a que se confirme", async () => {
    const { dialogo, onCerrar, cerrar } = montar();
    expect(fireEvent.keyDown(dialogo, { key: "Escape" })).toBe(false);
    fireEvent.click(dialogo);
    dialogo.close();
    expect(dialogo.open).toBe(true);
    expect(cerrar().hasAttribute("disabled")).toBe(true);
    await userEvent.click(screen.getByRole("checkbox", { hidden: true }));
    await userEvent.click(cerrar());
    expect(onCerrar).toHaveBeenCalledTimes(1);
  });

  it("sin contraseña el modal queda cerrado", () => {
    const { dialogo } = montar(null);
    expect(dialogo.open).toBe(false);
  });
});
