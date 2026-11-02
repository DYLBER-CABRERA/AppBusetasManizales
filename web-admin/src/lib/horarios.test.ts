import { describe, expect, it } from "vitest";
import {
  filasDeHorarios, horariosParaEnviar, validarFranjas, validarHorario, type FilaFranja, type FilaHorario,
} from "./horarios";

const fila = (p: Partial<FilaHorario> = {}): FilaHorario => ({
  tipoDia: "lun_vie", activo: true, primeraSalida: "04:45", ultimaSalida: "21:30", cierre: "", nota: "", ...p,
});
const franja = (clave: string, p: Partial<FilaFranja> = {}): FilaFranja => ({
  clave, tipoDia: "lun_vie", franjaInicio: "06:00", franjaFin: "10:00", minutosMin: "8", minutosMax: "10", nota: "", ...p,
});

describe("validarHorario", () => {
  it("acepta un horario correcto y no valida filas sin marcar", () => {
    expect(validarHorario(fila())).toEqual({});
    expect(validarHorario(fila({ activo: false, primeraSalida: "", ultimaSalida: "" }))).toEqual({});
  });
  it("pide primera y última salida", () => {
    const e = validarHorario(fila({ primeraSalida: "", ultimaSalida: "" }));
    expect(e.primeraSalida).toBeTruthy();
    expect(e.ultimaSalida).toBeTruthy();
  });
  it("la última salida no puede ser antes de la primera", () => {
    expect(validarHorario(fila({ primeraSalida: "22:00", ultimaSalida: "21:00" })).ultimaSalida).toBeTruthy();
  });
  it("el cierre debe ser igual o posterior a la última salida", () => {
    expect(validarHorario(fila({ cierre: "21:00" })).cierre).toBeTruthy();
    expect(validarHorario(fila({ cierre: "21:30" }))).toEqual({});
    expect(validarHorario(fila({ cierre: "23:00" }))).toEqual({});
  });
});

describe("horarios de la API", () => {
  it("un tipo de día sin dato queda sin marcar y no se envía", () => {
    const filas = filasDeHorarios([{ tipoDia: "lun_vie", primeraSalida: "04:45", ultimaSalida: "21:30" }]);
    expect(filas.map((f) => f.activo)).toEqual([true, false, false]);
    expect(horariosParaEnviar(filas)).toEqual([
      { tipoDia: "lun_vie", primeraSalida: "04:45", ultimaSalida: "21:30", cierre: null, nota: null },
    ]);
  });
});

describe("validarFranjas", () => {
  it("acepta franjas consecutivas y una que termina a medianoche", () => {
    const e = validarFranjas([
      franja("a"), franja("b", { franjaInicio: "10:00", franjaFin: "16:30" }),
      franja("c", { franjaInicio: "16:30", franjaFin: "24:00" }),
    ]);
    expect(e).toEqual({});
  });
  it("el fin debe ser posterior al inicio", () => {
    expect(validarFranjas([franja("a", { franjaFin: "06:00" })]).a?.franjaFin).toBeTruthy();
  });
  it("el mínimo no puede superar al máximo", () => {
    expect(validarFranjas([franja("a", { minutosMin: "12", minutosMax: "10" })]).a?.minutosMax).toBeTruthy();
  });
  it("exige minutos enteros de al menos 1", () => {
    const e = validarFranjas([franja("a", { minutosMin: "0", minutosMax: "x" })]);
    expect(e.a?.minutosMin).toBeTruthy();
    expect(e.a?.minutosMax).toBeTruthy();
  });
  it("detecta franjas que se cruzan en el mismo día, pero no en días distintos", () => {
    const cruzadas = validarFranjas([franja("a"), franja("b", { franjaInicio: "09:00", franjaFin: "12:00" })]);
    expect(cruzadas.b?.franjaInicio).toBeTruthy();
    const otroDia = validarFranjas([franja("a"), franja("b", { tipoDia: "sabado", franjaInicio: "09:00", franjaFin: "12:00" })]);
    expect(otroDia).toEqual({});
  });
});
