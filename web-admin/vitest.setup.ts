import { cleanup } from "@testing-library/react";
import { afterEach } from "vitest";

afterEach(cleanup);

// jsdom no implementa showModal/close del <dialog>: se simulan lo justo para probar el comportamiento
// del componente (abrir, mover el foco, avisar con el evento `close`).
HTMLDialogElement.prototype.showModal = function showModal(this: HTMLDialogElement) {
  this.setAttribute("open", "");
  this.querySelector<HTMLElement>("button, input, select, textarea, [tabindex]")?.focus();
};
HTMLDialogElement.prototype.close = function close(this: HTMLDialogElement) {
  if (!this.hasAttribute("open")) return;
  this.removeAttribute("open");
  this.dispatchEvent(new Event("close"));
};
