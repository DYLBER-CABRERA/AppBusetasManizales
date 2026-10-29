import { fireEvent, render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";
import type { components } from "@/lib/tipos-api";
import { ModalClaveNueva } from "./ModalClaveNueva";

const credencial: components["schemas"]["CredencialGpsCreada"] = {
  id: "c1", nombre: "GPS de la flota", activa: true, creadaEn: "2026-10-28T08:00:00-05:00", ultimoUso: null,
  clave: "clave-secreta-de-prueba",
};

function montar() {
  const onCerrar = vi.fn();
  render(<ModalClaveNueva credencial={credencial} empresa="Serviturismo" onCerrar={onCerrar} />);
  const dialogo = document.querySelector("dialog") as HTMLDialogElement;
  return { onCerrar, dialogo, cerrar: () => screen.getByRole("button", { name: "Cerrar", hidden: true }) };
}

describe("Clave de fuente GPS (se muestra una sola vez)", () => {
  it("muestra el aviso y la clave, con el foco dentro del modal", () => {
    const { dialogo } = montar();
    expect(screen.getByText("Copia la clave ahora. No podrás verla otra vez.")).toBeTruthy();
    expect(screen.getByText("clave-secreta-de-prueba")).toBeTruthy();
    expect(dialogo.open).toBe(true);
    expect(dialogo.contains(document.activeElement)).toBe(true);
  });

  it("no se cierra con Esc, con clic fuera ni con otras teclas", async () => {
    const { dialogo, onCerrar } = montar();
    for (const tecla of ["Escape", "Enter", " ", "Tab"]) {
      fireEvent.keyDown(dialogo, { key: tecla });
    }
    expect(fireEvent.keyDown(dialogo, { key: "Escape" })).toBe(false);
    fireEvent.click(dialogo);
    dialogo.close(); // lo que hace Chromium con el segundo Esc
    expect(dialogo.open).toBe(true);
    expect(onCerrar).not.toHaveBeenCalled();
  });

  it("Cerrar está deshabilitado hasta copiar la clave", async () => {
    const usuario = userEvent.setup();
    const { onCerrar, cerrar } = montar();
    expect((cerrar() as HTMLButtonElement).disabled).toBe(true);
    await usuario.click(cerrar());
    expect(onCerrar).not.toHaveBeenCalled();

    await usuario.click(screen.getByRole("button", { name: "Copiar", hidden: true }));
    expect(await navigator.clipboard.readText()).toBe("clave-secreta-de-prueba");
    expect((cerrar() as HTMLButtonElement).disabled).toBe(false);
    await usuario.click(cerrar());
    expect(onCerrar).toHaveBeenCalledTimes(1);
  });

  it("si no se puede copiar, Cerrar sigue deshabilitado hasta marcar que se guardó a mano", async () => {
    const usuario = userEvent.setup();
    const { onCerrar, cerrar } = montar();
    vi.spyOn(navigator.clipboard, "writeText").mockRejectedValueOnce(new Error("sin permiso"));
    await usuario.click(screen.getByRole("button", { name: "Copiar", hidden: true }));
    expect((cerrar() as HTMLButtonElement).disabled).toBe(true);

    await usuario.click(screen.getByRole("checkbox", { name: /guardé la clave/i, hidden: true }));
    expect((cerrar() as HTMLButtonElement).disabled).toBe(false);
    await usuario.click(cerrar());
    expect(onCerrar).toHaveBeenCalledTimes(1);
  });
});
