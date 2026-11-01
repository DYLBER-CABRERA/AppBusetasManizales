-- 0007: el radio de caminata del planificador sube de 500 m a 1000 m (HU-P07). NO aplicada automáticamente:
-- ver backend/scripts/aplicar_migracion.py. Solo cambia el valor si sigue en el valor de fábrica (500): si el
-- administrador ya lo editó desde el panel, no se toca. Idempotente.
update parametro_global
   set valor = '1000'::jsonb, version = version + 1
 where clave = 'radio_caminata_m' and valor = '500'::jsonb;
