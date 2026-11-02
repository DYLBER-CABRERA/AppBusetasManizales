import { fireEvent, render, screen } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";
import { Modal } from "./Modal";

function abierto(obligatorio: boolean) {
  const onCerrar = vi.fn();
  render(
    <Modal abierto obligatorio={obligatorio} titulo="Prueba" onCerrar={onCerrar}
      acciones={<><button type="button">Otro</button><button type="button" data-foco-inicial>Inicial</button></>}>
      Contenido
    </Modal>,
  );
  const dialogo = document.querySelector("dialog") as HTMLDialogElement;
  return { dialogo, onCerrar };
}

describe("Modal obligatorio", () => {
  it("abre el diálogo y deja el foco dentro, en el elemento inicial", () => {
    const { dialogo } = abierto(true);
    expect(dialogo.open).toBe(true);
    expect(dialogo.contains(document.activeElement)).toBe(true);
    expect(document.activeElement).toBe(screen.getByText("Inicial", { selector: "button" }));
  });

  it("bloquea Esc (keydown con acción por defecto cancelada) las veces que se pulse", () => {
    const { dialogo, onCerrar } = abierto(true);
    for (let i = 0; i < 3; i++) {
      const sigueSinCancelar = fireEvent.keyDown(dialogo, { key: "Escape" });
      expect(sigueSinCancelar).toBe(false); // preventDefault llamado: el navegador no cierra
    }
    expect(onCerrar).not.toHaveBeenCalled();
    expect(dialogo.open).toBe(true);
  });

  it("si el navegador lo cierra igualmente (segundo Esc en Chromium), se vuelve a abrir sin avisar", () => {
    const { dialogo, onCerrar } = abierto(true);
    dialogo.close();
    expect(dialogo.open).toBe(true);
    expect(dialogo.contains(document.activeElement)).toBe(true);
    expect(onCerrar).not.toHaveBeenCalled();
  });

  it("un clic fuera (sobre el fondo del diálogo) no lo cierra", () => {
    const { dialogo, onCerrar } = abierto(true);
    fireEvent.click(dialogo);
    expect(dialogo.open).toBe(true);
    expect(onCerrar).not.toHaveBeenCalled();
  });

  it("el evento cancel (primer Esc) se cancela", () => {
    const { dialogo } = abierto(true);
    const evento = new Event("cancel", { cancelable: true });
    dialogo.dispatchEvent(evento);
    expect(evento.defaultPrevented).toBe(true);
  });
});

describe("Modal normal", () => {
  it("avisa con onCerrar cuando se cierra", () => {
    const { dialogo, onCerrar } = abierto(false);
    dialogo.close();
    expect(onCerrar).toHaveBeenCalledTimes(1);
  });

  it("Esc no se bloquea", () => {
    const { dialogo } = abierto(false);
    expect(fireEvent.keyDown(dialogo, { key: "Escape" })).toBe(true);
  });
});
