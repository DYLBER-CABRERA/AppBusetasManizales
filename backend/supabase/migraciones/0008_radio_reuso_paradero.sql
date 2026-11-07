-- 0008: parámetro `radio_reuso_paradero_m` (rutas creadas tocando puntos en el mapa). NO aplicada automáticamente:
-- ver backend/scripts/aplicar_migracion.py. El backend usa 20 m por defecto si la fila no existe, así que aplicarla solo
-- hace el valor editable desde el panel de parámetros. Idempotente.
insert into parametro_global (clave, valor, descripcion, minimo, maximo) values
  ('radio_reuso_paradero_m', '20', 'Rutas desde puntos: un punto a esta distancia o menos de un paradero activo lo reutiliza; 0 = siempre crea uno nuevo', 0, 100)
on conflict (clave) do nothing;
