import L from "leaflet";

/** Marcador numerado. Rojo ladrillo con «!» si tiene error (el color no es el único canal). Solo se importa desde mapas cargados sin SSR. */
export const iconoNumerado = (n: number, error = false) =>
  L.divIcon({
    className: "",
    iconSize: [30, 30],
    iconAnchor: [15, 15],
    html: `<div style="width:30px;height:30px;border-radius:50%;display:flex;align-items:center;justify-content:center;font:700 14px sans-serif;color:#fff;border:3px solid #fff;box-shadow:0 1px 4px rgba(0,0,0,.5);background:${error ? "#a63d2f" : "#0e7c66"}">${n}${error ? "!" : ""}</div>`,
  });
