import { describe, expect, it } from "vitest";
import {
  distanciaM, erroresPorPunto, longitudCircuitoM, MAX_PUNTOS, muyPegado, puntosParaEnvio, validarPuntos, type PuntoCapturado,
} from "./puntos-ruta";

// Caso real del contrato §23: Fátima a Chipre.
const FATIMA_CHIPRE: PuntoCapturado[] = [
  { lat: 5.052476, lng: -75.497089, nombre: "Fátima" },
  { lat: 5.0617019, lng: -75.5079102 },
  { lat: 5.0701278, lng: -75.5179314 },
  { lat: 5.07655, lng: -75.525721, nombre: "Chipre" },
];

describe("puntos de ruta", () => {
  it("el caso Fátima a Chipre es válido y arma el cuerpo en orden, solo con los nombres escritos", () => {
    expect(validarPuntos(FATIMA_CHIPRE)).toEqual([]);
    expect(puntosParaEnvio(FATIMA_CHIPRE)).toEqual([
      { lat: 5.052476, lng: -75.497089, nombre: "Fátima" },
      { lat: 5.0617019, lng: -75.5079102 },
      { lat: 5.0701278, lng: -75.5179314 },
      { lat: 5.07655, lng: -75.525721, nombre: "Chipre" },
    ]);
  });

  it("la longitud del circuito incluye el cierre al primer punto", () => {
    const ida = FATIMA_CHIPRE.slice(1).reduce((t, p, i) => t + distanciaM(FATIMA_CHIPRE[i]!, p), 0);
    expect(longitudCircuitoM(FATIMA_CHIPRE)).toBeGreaterThan(ida);
    expect(longitudCircuitoM(FATIMA_CHIPRE)).toBeGreaterThan(5000);
  });

  it("detecta clics a menos de 10 m del punto anterior", () => {
    const base = FATIMA_CHIPRE[0]!;
    expect(muyPegado([base], { lat: base.lat + 0.00003, lng: base.lng })).toBe(true); // ~3 m
    expect(muyPegado([base], { lat: base.lat + 0.001, lng: base.lng })).toBe(false); // ~110 m
    expect(muyPegado([], base)).toBe(false);
  });

  it("marca el último punto si coincide con el primero (con más de 2 puntos)", () => {
    const cerrado = [...FATIMA_CHIPRE, { lat: FATIMA_CHIPRE[0]!.lat, lng: FATIMA_CHIPRE[0]!.lng }];
    expect(validarPuntos(cerrado).map((e) => [e.indice, e.motivo])).toEqual([[4, "ultimo_igual_al_primero"]]);
  });

  it("marca puntos consecutivos duplicados y nombres demasiado largos", () => {
    const p = FATIMA_CHIPRE;
    const lista = [p[0]!, { ...p[0]!, lng: p[0]!.lng + 0.00002 }, { ...p[2]!, nombre: "x".repeat(121) }];
    expect(validarPuntos(lista).map((e) => [e.indice, e.motivo])).toEqual([[1, "duplicado_consecutivo"], [2, "nombre_invalido"]]);
  });

  it("el tope es de 30 puntos (contrato §24) y un 400 sin detalles por punto no marca ninguno", () => {
    expect(MAX_PUNTOS).toBe(30);
    // «más de 30 puntos» llega sin `detalles` por índice: el formulario cae al mensaje general del servidor.
    expect(erroresPorPunto(null)).toEqual([]);
    expect(erroresPorPunto([])).toEqual([]);
  });

  it("traduce los detalles de un 400 por punto y ignora lo demás", () => {
    const e = erroresPorPunto([
      { campo: "puntos[1]", motivo: "fuera_de_zona" },
      { campo: "nombre", motivo: "muy_corto" },
      { campo: "puntos[3]", motivo: "algo_nuevo" },
    ]);
    expect(e.map((x) => x.indice)).toEqual([1, 3]);
    expect(e[0]!.texto).toBe("El punto 2 está fuera de la zona de la ciudad.");
    expect(e[1]!.texto).toBe("El punto 4 no es válido.");
    expect(erroresPorPunto(null)).toEqual([]);
  });
});
