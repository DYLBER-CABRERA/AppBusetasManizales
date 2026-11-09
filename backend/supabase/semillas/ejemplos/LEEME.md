# Ejemplos para importar rutas (datos de ejemplo, no oficiales)

- `importacion_rutas_ejemplo.csv`: la plantilla con una ruta válida (Fátima → Chipre, coordenadas de `barrios.json`), separador coma y decimal con punto.
- `importacion_rutas_con_errores_ejemplo.csv`: separador `;` y decimal con coma; trae una ruta válida y dos con errores (punto fuera de zona y empresa que no existe) para ver la vista previa.

Columnas: `ruta, orden, latitud, longitud, nombre_punto, empresa, codigo_publico`. Ver `docs/03-contrato-api.md` §25.
Subir a `POST /api/v1/rutas/importacion/vista-previa` (cuerpo = el archivo, `Content-Type: text/csv`).
