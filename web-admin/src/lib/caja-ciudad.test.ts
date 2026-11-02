import { describe, expect, it } from "vitest";
import { cajaDesdeValor, validarCaja } from "./caja-ciudad";

const base = { minLat: "4.95", maxLat: "5.20", minLng: "-75.65", maxLng: "-75.40" };

describe("validarCaja", () => {
  it("acepta una caja válida", () => {
    expect(validarCaja(base).caja).toEqual({ minLat: 4.95, maxLat: 5.2, minLng: -75.65, maxLng: -75.4 });
  });
  it("rechaza vacíos y no numéricos", () => {
    expect(validarCaja({ ...base, minLat: "" }).errores.minLat).toBeDefined();
    expect(validarCaja({ ...base, maxLng: "abc" }).errores.maxLng).toBeDefined();
  });
  it("rechaza latitudes fuera de rango y bordes invertidos", () => {
    expect(validarCaja({ ...base, maxLat: "95" }).errores.maxLat).toBeDefined();
    expect(validarCaja({ ...base, minLat: "6" }).errores.maxLat).toBeDefined();
    expect(validarCaja({ ...base, minLng: "-75.3" }).errores.maxLng).toBeDefined();
  });
  it("acepta coma decimal", () => {
    expect(validarCaja({ ...base, minLat: "4,95" }).caja?.minLat).toBe(4.95);
  });
  it("lee el valor del backend", () => {
    expect(cajaDesdeValor({ minLat: 1, maxLat: 2, minLng: 3, maxLng: 4 }).maxLng).toBe("4");
    expect(cajaDesdeValor(null).minLat).toBe("");
  });
});
