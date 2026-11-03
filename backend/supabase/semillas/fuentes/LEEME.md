# Fuentes de datos de los barrios

## barrios_alcaldia.geojson (capa oficial, barrios urbanos)

- **Origen:** Alcaldía de Manizales, ítem de ArcGIS `53ddc71c63e9474486a44af3ef334684`, «Límite de barrios Municipio de Manizales»
  (conforme a los Acuerdos Municipales 589 de 2004 y 1038 de 2019).
- **Servicio:** https://sig.manizales.gov.co/wadmzl/rest/services/20_WEB/2021_consulta_catas_urbano_web/FeatureServer/1
- **Descargado:** 2026-11-02, una sola vez, de la API pública (sin cuenta). 116 polígonos, 114 nombres únicos, EPSG:4326.
- **Atributos usados:** `BARRIOS` (nombre en mayúsculas sin tildes) e `Id_Comuna`. `X`/`Y` están en coordenadas proyectadas y no se usan.
- **Tratamiento:** dato no confiable; solo se lee como JSON (`scripts/generar_barrios_alcaldia.py`), nunca se ejecuta.
  El nombre `BELLA MONTAÑA` trae la letra Ñ (U+00D1) correcta en la fuente; no hay caracteres corruptos.

## barrios_osm.json (OpenStreetMap, sobre todo veredas)

- Generado por `scripts/descargar_barrios.py` con Overpass API. © OpenStreetMap contributors (ODbL), https://www.openstreetmap.org/copyright

Regenerar `../barrios.json`: `python scripts/generar_barrios_alcaldia.py` (desde `backend/`, sin internet).
