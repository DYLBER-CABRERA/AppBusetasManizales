-- 0003: índices y funciones (se invocan desde el backend con SQL escrito a mano).
-- Eliminados: ix_asignacion_buseta, ix_notificacion_user, tipo_de_dia, limpiar_eventos_uso.
-- Renombrada: eliminar_ruta_con_asignaciones -> dar_de_baja_ruta (sin la tabla asignacion).

-- unaccent no es inmutable; este envoltorio permite indexar. El backend debe buscar con la MISMA función.
create or replace function normalizar_texto(t text) returns text
language sql immutable parallel safe as $$ select lower(public.unaccent('public.unaccent', t)) $$;

create index ix_trazado_geo        on ruta_trazado using gist (trazado);
create index ix_paradero_geo       on paradero using gist (ubicacion) where estado = 'activo';
create index ix_hito_geo           on hito using gist (ubicacion) where estado = 'activo';
create index ix_posicion_geo       on posicion_buseta using gist (ubicacion);
create index ix_posicion_servicio  on posicion_buseta (servicio_ruta_id, reportada_en desc);
create index ix_ruta_nombre_trgm   on ruta using gin (normalizar_texto(nombre) gin_trgm_ops);
create index ix_hito_nombre_trgm   on hito using gin (normalizar_texto(nombre) gin_trgm_ops);
create index ix_ruta_principal     on ruta (ruta_principal_id) where ruta_principal_id is not null;
create index ix_ruta_paradero_par  on ruta_paradero (paradero_id);
create index ix_servicio_empresa   on servicio_ruta (empresa_id) where estado <> 'baja';
create index ix_horario_servicio   on horario (servicio_ruta_id);
create index ix_buseta_empresa     on buseta (empresa_id) where estado <> 'baja';
create index ix_conductor_empresa  on conductor (empresa_id) where estado = 'activo';
create index ix_turno_rodamiento   on turno (rodamiento_id);
create index ix_turno_buseta_hora  on turno (buseta_id, hora_salida);
create index ix_turno_servicio     on turno (servicio_ruta_id);
create index ix_rodamiento_fecha   on rodamiento (empresa_id, fecha) where estado = 'publicado';
create index ix_aviso_vigentes     on aviso (estado, desde, hasta);
create index ix_aviso_empresa      on aviso (empresa_id) where empresa_id is not null;
create index ix_alerta_ruta_par    on alerta_llegada (ruta_id, paradero_id) where estado <> 'desactivada';
create index ix_evento_fecha_ruta  on evento_uso (ocurrido_en, ruta_id);

-- Rutas activas con algún trazado a menos de p_radio_m del punto
create or replace function rutas_cercanas(p_lat double precision, p_lng double precision, p_radio_m integer)
returns table (ruta_id uuid, nombre text, tipo_recorrido tipo_recorrido, distancia_m double precision)
language sql stable as $$
  with punto as (select st_setsrid(st_makepoint(p_lng, p_lat), 4326)::geography as g)
  select r.id, r.nombre, r.tipo_recorrido, min(st_distance(t.trazado, punto.g)) as distancia_m
  from ruta r
  join ruta_trazado t on t.ruta_id = r.id
  cross join punto
  where r.estado = 'activo' and st_dwithin(t.trazado, punto.g, p_radio_m)
  group by r.id, r.nombre, r.tipo_recorrido
  order by distancia_m;
$$;

create or replace function paraderos_cercanos(
  p_lat double precision, p_lng double precision, p_radio_m integer,
  p_ruta_id uuid default null, p_limite integer default 20)
returns table (paradero_id uuid, nombre text, lat double precision, lng double precision, distancia_m double precision)
language sql stable as $$
  with punto as (select st_setsrid(st_makepoint(p_lng, p_lat), 4326)::geography as g)
  select p.id, p.nombre, st_y(p.ubicacion::geometry), st_x(p.ubicacion::geometry),
         st_distance(p.ubicacion, punto.g) as distancia_m
  from paradero p cross join punto
  where p.estado = 'activo'
    and st_dwithin(p.ubicacion, punto.g, p_radio_m)
    and (p_ruta_id is null or exists (select 1 from ruta_paradero rp where rp.paradero_id = p.id and rp.ruta_id = p_ruta_id))
  order by distancia_m
  limit least(greatest(p_limite, 1), 100);
$$;

-- Paradero más cercano a una ruta (para HU-P01 alternativo y HU-P09 sin cobertura)
create or replace function paradero_mas_cercano_a_ruta(p_lat double precision, p_lng double precision, p_ruta_id uuid)
returns table (paradero_id uuid, nombre text, distancia_m double precision)
language sql stable as $$
  with punto as (select st_setsrid(st_makepoint(p_lng, p_lat), 4326)::geography as g)
  select p.id, p.nombre, st_distance(p.ubicacion, punto.g)
  from ruta_paradero rp join paradero p on p.id = rp.paradero_id and p.estado = 'activo'
  cross join punto
  where rp.ruta_id = p_ruta_id
  order by st_distance(p.ubicacion, punto.g)
  limit 1;
$$;

create or replace function rutas_por_hito(p_hito_id uuid, p_radio_m integer)
returns table (ruta_id uuid, distancia_m double precision)
language sql stable as $$
  select r.id, min(st_distance(t.trazado, h.ubicacion)) as distancia_m
  from hito h
  join ruta_trazado t on st_dwithin(t.trazado, h.ubicacion, p_radio_m)
  join ruta r on r.id = t.ruta_id and r.estado = 'activo'
  where h.id = p_hito_id and h.estado = 'activo'
  group by r.id
  order by distancia_m;
$$;

-- Avance de un punto a lo largo del trazado (metros desde el inicio) y desvío respecto de la ruta
create or replace function progreso_en_ruta(
  p_ruta_id uuid, p_sentido sentido_ruta, p_lat double precision, p_lng double precision)
returns table (progreso_m double precision, desvio_m double precision, longitud_m double precision)
language sql stable as $$
  with punto as (select st_setsrid(st_makepoint(p_lng, p_lat), 4326) as g)
  select st_linelocatepoint(t.trazado::geometry, punto.g) * t.longitud_m,
         st_distance(t.trazado, punto.g::geography),
         t.longitud_m
  from ruta_trazado t cross join punto
  where t.ruta_id = p_ruta_id and t.sentido = p_sentido;
$$;

-- Progreso de cada paradero de una ruta, calculado EN SECUENCIA por `orden` (decisión del equipo, opción B).
-- Un trazado circular puede repetir calles (ida y vuelta por la misma vía): la proyección al punto más cercano es
-- ambigua en esos tramos. Aquí cada paradero se busca solo desde el progreso del anterior hasta el final del
-- circuito, así el progreso nunca retrocede y respeta el orden de recorrido.
create or replace function progresos_paraderos_ruta(p_ruta_id uuid, p_sentido sentido_ruta)
returns table (orden integer, paradero_id uuid, progreso_m double precision, longitud_m double precision)
language sql stable as $$
  with recursive t as (
    select rt.trazado::geometry as g, rt.longitud_m as l
    from ruta_trazado rt where rt.ruta_id = p_ruta_id and rt.sentido = p_sentido
  ), paradas as (
    select rp.orden as ord, rp.paradero_id as pid, p.ubicacion::geometry as pt,
           row_number() over (order by rp.orden) as n
    from ruta_paradero rp join paradero p on p.id = rp.paradero_id
    where rp.ruta_id = p_ruta_id and rp.sentido = p_sentido
  ), seq as (
    select pa.n, pa.ord, pa.pid, st_linelocatepoint(t.g, pa.pt) as frac
    from paradas pa cross join t
    where pa.n = 1
    union all
    select pa.n, pa.ord, pa.pid,
           s.frac + (1 - s.frac) * st_linelocatepoint(st_linesubstring(t.g, least(s.frac, 0.9999999), 1), pa.pt)
    from seq s
    join paradas pa on pa.n = s.n + 1
    cross join t
  )
  select seq.ord, seq.pid, seq.frac * t.l, t.l from seq cross join t order by seq.ord;
$$;

-- Progreso de un paradero en la ruta: el calculado en secuencia; si el paradero no está en la ruta, el más cercano.
create or replace function progreso_paradero(p_ruta_id uuid, p_sentido sentido_ruta, p_paradero_id uuid)
returns table (progreso_m double precision, longitud_m double precision)
language sql stable as $$
  select x.prog, x.lon from (
    select s.progreso_m as prog, s.longitud_m as lon, 0 as pref, s.orden as ord
    from progresos_paraderos_ruta(p_ruta_id, p_sentido) s where s.paradero_id = p_paradero_id
    union all
    select st_linelocatepoint(t.trazado::geometry, p.ubicacion::geometry) * t.longitud_m, t.longitud_m, 1, 0
    from ruta_trazado t join paradero p on p.id = p_paradero_id
    where t.ruta_id = p_ruta_id and t.sentido = p_sentido
  ) x
  order by x.pref, x.ord
  limit 1;
$$;

-- Servicio de ruta que cumple una buseta en un instante, según el rodamiento publicado
create or replace function turno_vigente(p_empresa_id uuid, p_numero_lateral text, p_instante timestamptz)
returns uuid
language sql stable as $$
  select t.servicio_ruta_id
  from turno t
  join rodamiento r on r.id = t.rodamiento_id
  join buseta b on b.id = t.buseta_id
  join servicio_ruta s on s.id = t.servicio_ruta_id
  where r.empresa_id = p_empresa_id
    and r.estado = 'publicado'
    and r.fecha = (p_instante at time zone 'America/Bogota')::date
    and b.empresa_id = p_empresa_id
    and b.numero_lateral = p_numero_lateral
    and t.estado = 'programado'
    and (p_instante at time zone 'America/Bogota') between
        (r.fecha + t.hora_salida)
        and (r.fecha + coalesce(t.hora_fin_estimada, t.hora_salida)
             + case when t.hora_fin_estimada is null
                    then make_interval(mins => coalesce(s.duracion_estandar_min, 120)) else interval '0' end)
  order by t.hora_salida desc
  limit 1;
$$;

-- Guarda la posición solo si es más reciente que la almacenada. Devuelve true si la aceptó.
create or replace function guardar_posicion(
  p_buseta_id uuid, p_servicio_ruta_id uuid, p_lat double precision, p_lng double precision,
  p_velocidad_kmh real, p_rumbo real, p_reportada_en timestamptz)
returns boolean
language plpgsql as $$
declare v_filas integer;
begin
  insert into posicion_buseta as pb (buseta_id, servicio_ruta_id, ubicacion, velocidad_kmh, rumbo, reportada_en)
  values (p_buseta_id, p_servicio_ruta_id, st_setsrid(st_makepoint(p_lng, p_lat), 4326)::geography,
          p_velocidad_kmh, p_rumbo, p_reportada_en)
  on conflict (buseta_id) do update
    set servicio_ruta_id = excluded.servicio_ruta_id,
        ubicacion        = excluded.ubicacion,
        velocidad_kmh    = excluded.velocidad_kmh,
        rumbo            = excluded.rumbo,
        reportada_en     = excluded.reportada_en,
        recibida_en      = now()
    where pb.reportada_en < excluded.reportada_en;
  get diagnostics v_filas = row_count;
  return v_filas > 0;
end;
$$;

-- Reemplaza la secuencia de paraderos de una ruta y sentido en una sola transacción
create or replace function reemplazar_paraderos_de_ruta(p_ruta_id uuid, p_sentido sentido_ruta, p_paraderos uuid[])
returns void
language plpgsql as $$
begin
  delete from ruta_paradero where ruta_id = p_ruta_id and sentido = p_sentido;
  insert into ruta_paradero (ruta_id, sentido, orden, paradero_id)
  select p_ruta_id, p_sentido, ord, pid from unnest(p_paraderos) with ordinality as u(pid, ord);
end;
$$;

-- Baja de una ruta con cancelación de turnos futuros y baja de sus servicios (HU-SM03).
-- Si hay turnos futuros y no viene `confirmar`, la decisión es del caso de uso (consulta antes con un select).
create or replace function dar_de_baja_ruta(p_ruta_id uuid, p_version integer)
returns boolean
language plpgsql as $$
declare v_filas integer;
begin
  update ruta set estado = 'baja', version = version + 1
  where id = p_ruta_id and version = p_version and estado = 'activo';
  get diagnostics v_filas = row_count;
  if v_filas = 0 then
    return false;
  end if;
  update turno set estado = 'cancelado'
  where estado = 'programado'
    and servicio_ruta_id in (select id from servicio_ruta where ruta_id = p_ruta_id)
    and rodamiento_id in (select id from rodamiento where fecha >= current_date and estado <> 'anulado');
  update servicio_ruta set estado = 'baja', version = version + 1 where ruta_id = p_ruta_id and estado <> 'baja';
  return true;
end;
$$;

-- Estadísticas de uso por ruta y día para las rutas de una empresa (HU-J06)
create or replace function estadisticas_uso(p_empresa_id uuid, p_desde date, p_hasta date)
returns table (ruta_id uuid, dia date, tipo tipo_evento_uso, total bigint)
language sql stable as $$
  select e.ruta_id, (e.ocurrido_en at time zone 'America/Bogota')::date, e.tipo, count(*)
  from evento_uso e
  where e.ruta_id in (select s.ruta_id from servicio_ruta s where s.empresa_id = p_empresa_id and s.estado <> 'baja')
    and e.ocurrido_en >= p_desde::timestamp at time zone 'America/Bogota'
    and e.ocurrido_en <  (p_hasta + 1)::timestamp at time zone 'America/Bogota'
  group by 1, 2, 3
  order by 2, 1;
$$;
