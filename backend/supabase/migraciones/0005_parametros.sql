-- 0005: parámetros globales (valores PROPUESTOS; editables por el administrador, HU-A04).
-- Eliminados: max_filas_excel, tamano_max_excel_mb, radio_transbordo_m, retencion_eventos_dias.
insert into parametro_global (clave, valor, descripcion, minimo, maximo) values
  ('radio_busqueda_m',            '800',   'Radio para rutas y paraderos cercanos (HU-P01)', 100, 5000),
  ('radio_caminata_m',            '500',   'Distancia máxima a pie en la planificación (HU-P07)', 100, 2000),
  ('radio_hito_m',                '300',   'Radio para considerar que una ruta pasa por un hito (HU-P09)', 50, 2000),
  ('velocidad_default_kmh',       '20',    'Velocidad usada en el ETA si la buseta no reporta una válida', 5, 60),
  ('umbral_posicion_obsoleta_s',  '60',    'Segundos tras los cuales una posición se considera sin señal', 10, 600),
  ('intervalo_refresco_cliente_s','5',     'Cada cuánto consulta el cliente las busetas en vivo', 2, 60),
  ('distancia_aviso_llegada_m',   '300',   'Distancia por defecto para avisar la llegada (HU-P11)', 50, 2000),
  ('enfriamiento_alerta_min',     '10',    'Minutos antes de volver a avisar la misma alerta', 1, 120),
  ('umbral_desvio_m',             '100',   'Distancia a la ruta a partir de la cual se considera desvío', 30, 500),
  ('longitud_max_aviso',          '500',   'Caracteres máximos del cuerpo de un aviso (HU-J05)', 50, 2000),
  ('max_opciones_viaje',          '3',     'Opciones devueltas por la planificación', 1, 10),
  ('dias_max_rodamiento_adelante','15',    'Días hacia adelante en que se puede definir un rodamiento', 1, 60),
  ('rango_max_estadisticas_dias', '365',   'Rango máximo de consulta de estadísticas', 7, 730);

-- Valor PROVISIONAL: el equipo debe ajustarlo con el mapa real (zona de Manizales y alrededores).
insert into parametro_global (clave, valor, descripcion) values
  ('caja_ciudad', '{"minLat":4.95,"maxLat":5.20,"minLng":-75.65,"maxLng":-75.40}',
   'Caja geográfica fuera de la cual se rechazan posiciones GPS');
