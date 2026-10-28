-- =====================================================================
-- BusetasApp — esquema de base de datos (Supabase / Postgres + PostGIS)
-- Estado: PROPUESTO (Actividad 6). Lo "Confirmado" es solo que la base es Supabase.
-- Convenciones: nombres en español, snake_case; identificadores uuid;
--               control de concurrencia con "version" (RNF-02);
--               baja lógica (D-04); coordenadas WGS84 (SRID 4326), geography.
-- Orden de aplicación sugerido (migraciones):
--   0001 tipos y tablas · 0002 índices · 0003 funciones · 0004 RLS · 0005 semillas
-- =====================================================================

-- ---------- 0001: extensiones ----------
create extension if not exists postgis;
create extension if not exists pg_trgm;
create extension if not exists unaccent;
create extension if not exists btree_gist;

-- ---------- 0001: tipos ----------
create type rol_usuario        as enum ('pasajero','jefe_operaciones','secretaria_movilidad','administrador');
create type tipo_recorrido     as enum ('lineal','circular');
create type sentido_ruta       as enum ('ida','vuelta','circular');
create type tipo_dia           as enum ('lun_vie','sabado','dom_festivo');
create type estado_registro    as enum ('activo','baja');
create type estado_servicio    as enum ('activo','suspendido','baja');
create type estado_buseta      as enum ('activa','fuera_servicio','baja');
create type estado_rodamiento  as enum ('borrador','publicado','anulado');
create type estado_turno       as enum ('programado','cancelado');   -- en_curso y finalizado se derivan
create type origen_aviso       as enum ('empresa','movilidad','aplicativo');
create type estado_aviso       as enum ('activo','retirado');        -- programado y vencido se derivan de las fechas
create type tipo_hito          as enum ('hito','barrio','sector','universidad','hospital','terminal','otro');
create type tipo_favorito      as enum ('ruta','paradero');
create type estado_alerta      as enum ('activa','notificada','desactivada');
create type canal_notificacion as enum ('push','bandeja');
create type estado_notificacion as enum ('pendiente','enviada','fallida','leida');
create type tipo_importacion   as enum ('conductores','busetas','asignaciones','horarios_frecuencias','rodamiento','rutas_paraderos');
create type estado_importacion as enum ('completada','parcial','rechazada','fallida');
create type tipo_evento_uso    as enum ('mapa','detalle_ruta','horarios','frecuencias','busetas_vivo','eta','busqueda','planificacion');

-- ---------- 0001: utilidades ----------
create or replace function marcar_actualizacion() returns trigger
language plpgsql as $$
begin
  new.actualizado_en := now();
  return new;
end;
$$;

-- ---------- 0001: empresas y usuarios ----------
create table empresa (
  id             uuid primary key default gen_random_uuid(),
  nombre         text not null check (length(btrim(nombre)) between 2 and 120),
  estado         estado_registro not null default 'activo',
  version        integer not null default 1,
  creado_en      timestamptz not null default now(),
  actualizado_en timestamptz not null default now()
);
create unique index ux_empresa_nombre on empresa (lower(nombre)) where estado = 'activo';

-- Una fila por cuenta de Supabase Auth. El conductor NO tiene perfil (BR-06).
create table perfil_usuario (
  id             uuid primary key,                     -- = auth.users.id
  correo         text not null,
  nombre         text,
  rol            rol_usuario not null default 'pasajero',
  empresa_id     uuid references empresa(id),
  activo         boolean not null default true,
  version        integer not null default 1,
  creado_en      timestamptz not null default now(),
  actualizado_en timestamptz not null default now(),
  -- RD-14: el jefe pertenece a exactamente una empresa; los demás roles a ninguna
  constraint ck_perfil_empresa check (
    (rol = 'jefe_operaciones' and empresa_id is not null) or
    (rol <> 'jefe_operaciones' and empresa_id is null)
  )
);
create unique index ux_perfil_correo on perfil_usuario (lower(correo));

create table permiso_rol (
  rol     rol_usuario not null,
  permiso text not null,
  primary key (rol, permiso)
);

-- ---------- 0001: red de transporte (la gestiona la Secretaría, BR-04) ----------
create table ruta (
  id                uuid primary key default gen_random_uuid(),
  nombre            text not null check (length(btrim(nombre)) between 2 and 120),
  tipo_recorrido    tipo_recorrido not null default 'lineal',
  ruta_principal_id uuid references ruta(id),          -- variante de otra ruta (contexto §8.2.5)
  descripcion       text,
  estado            estado_registro not null default 'activo',
  version           integer not null default 1,
  creado_en         timestamptz not null default now(),
  actualizado_en    timestamptz not null default now(),
  constraint ck_ruta_no_autovariante check (ruta_principal_id is null or ruta_principal_id <> id)
);

-- RD-02: una variante solo puede apuntar a una ruta que no sea variante
create or replace function validar_variante() returns trigger
language plpgsql as $$
begin
  if new.ruta_principal_id is not null then
    if exists (select 1 from ruta where id = new.ruta_principal_id and ruta_principal_id is not null) then
      raise exception 'La ruta principal no puede ser a su vez una variante' using errcode = '23514';
    end if;
    if exists (select 1 from ruta where ruta_principal_id = new.id) then
      raise exception 'Una ruta con variantes no puede ser variante de otra' using errcode = '23514';
    end if;
  end if;
  return new;
end;
$$;
create trigger tg_ruta_validar_variante before insert or update of ruta_principal_id on ruta
  for each row execute function validar_variante();

-- Trazado por sentido. Lineal: ida y vuelta. Circular: un único sentido 'circular'.
create table ruta_trazado (
  ruta_id   uuid not null references ruta(id),
  sentido   sentido_ruta not null,
  trazado   geography(LineString, 4326) not null,
  longitud_m double precision generated always as (st_length(trazado)) stored,
  primary key (ruta_id, sentido)
);

create table paradero (
  id             uuid primary key default gen_random_uuid(),
  nombre         text not null check (length(btrim(nombre)) between 2 and 120),
  direccion      text,
  ubicacion      geography(Point, 4326) not null,
  estado         estado_registro not null default 'activo',
  version        integer not null default 1,
  creado_en      timestamptz not null default now(),
  actualizado_en timestamptz not null default now()
);

-- Secuencia ordenada de paraderos por ruta y sentido (RD-04)
create table ruta_paradero (
  ruta_id     uuid not null references ruta(id),
  sentido     sentido_ruta not null,
  orden       integer not null check (orden >= 1),
  paradero_id uuid not null references paradero(id),
  primary key (ruta_id, sentido, orden),
  foreign key (ruta_id, sentido) references ruta_trazado (ruta_id, sentido)
);

create table hito (
  id         uuid primary key default gen_random_uuid(),
  nombre     text not null,
  tipo       tipo_hito not null default 'hito',
  alias      text[] not null default '{}',
  ubicacion  geography(Point, 4326) not null,
  estado     estado_registro not null default 'activo',
  version    integer not null default 1
);

-- Rutas compartidas: una fila por empresa que opera la ruta (RD-01)
create table servicio_ruta (
  id                    uuid primary key default gen_random_uuid(),
  ruta_id               uuid not null references ruta(id),
  empresa_id            uuid not null references empresa(id),
  codigo_publico        text check (codigo_publico ~ '^[0-9]+$'),         -- Serviturismo no tiene (puede ser null)
  codigo_interno        text,
  duracion_estandar_min integer check (duracion_estandar_min between 5 and 300),
  estado                estado_servicio not null default 'activo',
  version               integer not null default 1,
  creado_en             timestamptz not null default now(),
  actualizado_en        timestamptz not null default now()
);
create unique index ux_servicio_ruta_empresa on servicio_ruta (ruta_id, empresa_id) where estado <> 'baja';
create unique index ux_servicio_codigo_publico on servicio_ruta (empresa_id, codigo_publico)
  where codigo_publico is not null and estado <> 'baja';

create table dia_festivo (
  fecha       date primary key,
  descripcion text not null
);

-- ---------- 0001: horarios y frecuencias (los edita el jefe de su empresa) ----------
create table horario (
  id               uuid primary key default gen_random_uuid(),
  servicio_ruta_id uuid not null references servicio_ruta(id),
  tipo_dia         tipo_dia not null,
  primera_salida   time not null,
  ultima_salida    time not null,
  cierre           time,                       -- cierre total (Socobuses: 23:00)
  nota             text,
  version          integer not null default 1,
  constraint ck_horario_orden check (primera_salida <= ultima_salida),
  constraint ck_horario_cierre check (cierre is null or cierre >= ultima_salida),
  unique (servicio_ruta_id, tipo_dia)
);

-- Franja en minutos desde 00:00 (permite impedir solapamientos con una restricción de exclusión)
create table frecuencia (
  id               uuid primary key default gen_random_uuid(),
  servicio_ruta_id uuid not null references servicio_ruta(id),
  tipo_dia         tipo_dia not null,
  inicio_minuto    smallint not null check (inicio_minuto between 0 and 1439),
  fin_minuto       smallint not null check (fin_minuto between 1 and 1440),
  minutos_min      smallint not null check (minutos_min >= 1),
  minutos_max      smallint not null,
  nota             text,
  version          integer not null default 1,
  constraint ck_frecuencia_franja check (inicio_minuto < fin_minuto),
  constraint ck_frecuencia_rango check (minutos_max >= minutos_min),
  constraint ex_frecuencia_sin_solape exclude using gist (
    servicio_ruta_id with =, tipo_dia with =, int4range(inicio_minuto, fin_minuto) with &&
  )
);

-- ---------- 0001: operación de las empresas (BR-03) ----------
create table buseta (
  id             uuid primary key default gen_random_uuid(),
  empresa_id     uuid not null references empresa(id),
  numero_lateral text not null check (length(btrim(numero_lateral)) between 1 and 20),
  placa          text,
  estado         estado_buseta not null default 'activa',
  version        integer not null default 1,
  creado_en      timestamptz not null default now(),
  actualizado_en timestamptz not null default now(),
  unique (empresa_id, numero_lateral)          -- RD-07
);

-- El conductor es un dato (BR-06). Se guarda solo lo necesario.
create table conductor (
  id             uuid primary key default gen_random_uuid(),
  empresa_id     uuid not null references empresa(id),
  nombre         text not null check (length(btrim(nombre)) between 2 and 120),
  codigo         text,
  estado         estado_registro not null default 'activo',
  version        integer not null default 1,
  creado_en      timestamptz not null default now(),
  actualizado_en timestamptz not null default now()
);
create unique index ux_conductor_codigo on conductor (empresa_id, codigo) where codigo is not null and estado = 'activo';

-- Asignación vigente servicio–buseta–conductor. Una buseta puede tener varias (contexto §8.2.6).
create table asignacion (
  id               uuid primary key default gen_random_uuid(),
  servicio_ruta_id uuid not null references servicio_ruta(id),
  buseta_id        uuid not null references buseta(id),
  conductor_id     uuid references conductor(id),
  vigente_desde    date not null default current_date,
  vigente_hasta    date,
  version          integer not null default 1,
  constraint ck_asignacion_fechas check (vigente_hasta is null or vigente_hasta >= vigente_desde)
);
create unique index ux_asignacion_vigente on asignacion (servicio_ruta_id, buseta_id) where vigente_hasta is null;

create table rodamiento (
  id              uuid primary key default gen_random_uuid(),
  empresa_id      uuid not null references empresa(id),
  fecha           date not null,
  estado          estado_rodamiento not null default 'borrador',
  publicado_por   uuid references perfil_usuario(id),
  publicado_en    timestamptz,
  version         integer not null default 1,
  creado_en       timestamptz not null default now(),
  actualizado_en  timestamptz not null default now()
);
create unique index ux_rodamiento_empresa_fecha on rodamiento (empresa_id, fecha) where estado <> 'anulado';

create table turno (
  id                  uuid primary key default gen_random_uuid(),
  rodamiento_id       uuid not null references rodamiento(id) on delete cascade,
  servicio_ruta_id    uuid not null references servicio_ruta(id),
  buseta_id           uuid not null references buseta(id),
  conductor_id        uuid references conductor(id),
  hora_salida         time not null,
  hora_fin_estimada   time,
  estado              estado_turno not null default 'programado',
  nota                text,
  constraint ck_turno_horas check (hora_fin_estimada is null or hora_fin_estimada > hora_salida)
);

-- RD-09: el servicio, la buseta y el conductor deben ser de la misma empresa del rodamiento
create or replace function validar_turno_empresa() returns trigger
language plpgsql as $$
declare v_empresa uuid;
begin
  select empresa_id into v_empresa from rodamiento where id = new.rodamiento_id;
  if not exists (select 1 from servicio_ruta where id = new.servicio_ruta_id and empresa_id = v_empresa) then
    raise exception 'El servicio de ruta no pertenece a la empresa del rodamiento' using errcode = '23514';
  end if;
  if not exists (select 1 from buseta where id = new.buseta_id and empresa_id = v_empresa) then
    raise exception 'La buseta no pertenece a la empresa del rodamiento' using errcode = '23514';
  end if;
  if new.conductor_id is not null and
     not exists (select 1 from conductor where id = new.conductor_id and empresa_id = v_empresa) then
    raise exception 'El conductor no pertenece a la empresa del rodamiento' using errcode = '23514';
  end if;
  return new;
end;
$$;
create trigger tg_turno_validar_empresa before insert or update on turno
  for each row execute function validar_turno_empresa();

-- ---------- 0001: seguimiento ----------
-- Credencial de la fuente de posiciones: una clave por empresa; solo se guarda el hash.
create table credencial_fuente_gps (
  id           uuid primary key default gen_random_uuid(),
  empresa_id   uuid not null references empresa(id),
  nombre       text not null,
  hash_clave   text not null unique,
  activa       boolean not null default true,
  creada_en    timestamptz not null default now(),
  ultimo_uso   timestamptz
);

-- Solo la última posición de cada buseta (RD-11)
create table posicion_buseta (
  buseta_id        uuid primary key references buseta(id),
  servicio_ruta_id uuid references servicio_ruta(id),   -- deducido del rodamiento; null si no tiene turno
  ubicacion        geography(Point, 4326) not null,
  velocidad_kmh    real check (velocidad_kmh is null or velocidad_kmh between 0 and 150),
  rumbo            real check (rumbo is null or rumbo >= 0 and rumbo < 360),
  reportada_en     timestamptz not null,
  recibida_en      timestamptz not null default now()
);

-- ---------- 0001: comunicación ----------
create table aviso (
  id          uuid primary key default gen_random_uuid(),
  origen      origen_aviso not null,
  empresa_id  uuid references empresa(id),
  titulo      text not null check (length(btrim(titulo)) between 1 and 120),
  cuerpo      text not null check (length(btrim(cuerpo)) between 1 and 2000),   -- el máximo operativo lo da longitud_max_aviso
  desde       timestamptz not null default now(),
  hasta       timestamptz,
  estado      estado_aviso not null default 'activo',
  autor_id    uuid not null references perfil_usuario(id),
  version     integer not null default 1,
  creado_en   timestamptz not null default now(),
  constraint ck_aviso_vigencia check (hasta is null or hasta > desde),
  constraint ck_aviso_empresa check (
    (origen = 'empresa' and empresa_id is not null) or (origen <> 'empresa' and empresa_id is null)
  )
);

create table aviso_afecta (
  aviso_id    uuid not null references aviso(id) on delete cascade,
  ruta_id     uuid references ruta(id),
  paradero_id uuid references paradero(id),
  constraint ck_aviso_afecta check (ruta_id is not null or paradero_id is not null)
);

-- ---------- 0001: pasajero registrado ----------
create table favorito (
  id          uuid primary key default gen_random_uuid(),
  usuario_id  uuid not null references perfil_usuario(id) on delete cascade,
  tipo        tipo_favorito not null,
  ruta_id     uuid references ruta(id),
  paradero_id uuid references paradero(id),
  creado_en   timestamptz not null default now(),
  constraint ck_favorito_objetivo check (
    (tipo = 'ruta' and ruta_id is not null and paradero_id is null) or
    (tipo = 'paradero' and paradero_id is not null and ruta_id is null)
  )
);
create unique index ux_favorito_ruta     on favorito (usuario_id, ruta_id)     where ruta_id is not null;
create unique index ux_favorito_paradero on favorito (usuario_id, paradero_id) where paradero_id is not null;

create table alerta_llegada (
  id                    uuid primary key default gen_random_uuid(),
  usuario_id            uuid not null references perfil_usuario(id) on delete cascade,
  ruta_id               uuid not null references ruta(id),
  paradero_id           uuid not null references paradero(id),
  sentido               sentido_ruta not null,
  distancia_aviso_m     integer not null check (distancia_aviso_m between 50 and 2000),
  estado                estado_alerta not null default 'activa',
  ultima_notificacion_en timestamptz,
  version               integer not null default 1,
  creada_en             timestamptz not null default now()
);
create unique index ux_alerta_unica on alerta_llegada (usuario_id, ruta_id, paradero_id, sentido) where estado <> 'desactivada';

create table suscripcion_push (
  id          uuid primary key default gen_random_uuid(),
  usuario_id  uuid not null references perfil_usuario(id) on delete cascade,
  endpoint    text not null unique,
  p256dh      text not null,
  auth        text not null,
  creada_en   timestamptz not null default now()
);

create table notificacion (
  id          uuid primary key default gen_random_uuid(),
  usuario_id  uuid not null references perfil_usuario(id) on delete cascade,
  alerta_id   uuid references alerta_llegada(id) on delete set null,
  canal       canal_notificacion not null,
  titulo      text not null,
  cuerpo      text not null,
  estado      estado_notificacion not null default 'pendiente',
  creada_en   timestamptz not null default now(),
  leida_en    timestamptz
);

-- ---------- 0001: plataforma ----------
-- Sin identificador de usuario ni coordenadas (RD-17, RNF-01)
create table evento_uso (
  id           bigint generated always as identity primary key,
  tipo         tipo_evento_uso not null,
  ruta_id      uuid references ruta(id),
  empresa_id   uuid references empresa(id),
  ocurrido_en  timestamptz not null default now()
);

create table parametro_global (
  clave        text primary key,
  valor        jsonb not null,
  descripcion  text not null,
  minimo       numeric,
  maximo       numeric,
  version      integer not null default 1,
  actualizado_en timestamptz not null default now()
);

create table importacion (
  id            uuid primary key default gen_random_uuid(),
  usuario_id    uuid not null references perfil_usuario(id),
  empresa_id    uuid references empresa(id),
  tipo          tipo_importacion not null,
  estado        estado_importacion not null,
  filas_total   integer not null default 0,
  filas_ok      integer not null default 0,
  filas_error   integer not null default 0,
  errores       jsonb not null default '[]',      -- [{fila, columna, motivo}]
  creada_en     timestamptz not null default now()
);

-- Disparadores de marca de tiempo
create trigger tg_empresa_act        before update on empresa        for each row execute function marcar_actualizacion();
create trigger tg_perfil_act         before update on perfil_usuario for each row execute function marcar_actualizacion();
create trigger tg_ruta_act           before update on ruta           for each row execute function marcar_actualizacion();
create trigger tg_paradero_act       before update on paradero       for each row execute function marcar_actualizacion();
create trigger tg_servicio_act       before update on servicio_ruta  for each row execute function marcar_actualizacion();
create trigger tg_buseta_act         before update on buseta         for each row execute function marcar_actualizacion();
create trigger tg_conductor_act      before update on conductor      for each row execute function marcar_actualizacion();
create trigger tg_rodamiento_act     before update on rodamiento     for each row execute function marcar_actualizacion();
create trigger tg_parametro_act      before update on parametro_global for each row execute function marcar_actualizacion();

-- ---------- 0002: índices ----------
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
create index ix_asignacion_buseta  on asignacion (buseta_id) where vigente_hasta is null;
create index ix_turno_rodamiento   on turno (rodamiento_id);
create index ix_turno_buseta_hora  on turno (buseta_id, hora_salida);
create index ix_turno_servicio     on turno (servicio_ruta_id);
create index ix_rodamiento_fecha   on rodamiento (empresa_id, fecha) where estado = 'publicado';
create index ix_aviso_vigentes     on aviso (estado, desde, hasta);
create index ix_aviso_empresa      on aviso (empresa_id) where empresa_id is not null;
create index ix_alerta_ruta_par    on alerta_llegada (ruta_id, paradero_id) where estado <> 'desactivada';
create index ix_notificacion_user  on notificacion (usuario_id, creada_en desc);
create index ix_evento_fecha_ruta  on evento_uso (ocurrido_en, ruta_id);

-- ---------- 0003: funciones (se invocan con rpc desde el backend) ----------
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

create or replace function progreso_paradero(p_ruta_id uuid, p_sentido sentido_ruta, p_paradero_id uuid)
returns table (progreso_m double precision, longitud_m double precision)
language sql stable as $$
  select st_linelocatepoint(t.trazado::geometry, p.ubicacion::geometry) * t.longitud_m, t.longitud_m
  from ruta_trazado t join paradero p on p.id = p_paradero_id
  where t.ruta_id = p_ruta_id and t.sentido = p_sentido;
$$;

-- Tipo de día de una fecha (festivo tiene prioridad), fecha en hora local de Bogotá
create or replace function tipo_de_dia(p_fecha date) returns tipo_dia
language sql stable as $$
  select case
    when exists (select 1 from dia_festivo where fecha = p_fecha) then 'dom_festivo'::tipo_dia
    when extract(isodow from p_fecha) between 1 and 5 then 'lun_vie'::tipo_dia
    when extract(isodow from p_fecha) = 6 then 'sabado'::tipo_dia
    else 'dom_festivo'::tipo_dia
  end;
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

-- Baja de una ruta con cierre de asignaciones y cancelación de turnos futuros (HU-SM03)
create or replace function eliminar_ruta_con_asignaciones(p_ruta_id uuid, p_version integer)
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
  update asignacion set vigente_hasta = current_date
  where vigente_hasta is null
    and servicio_ruta_id in (select id from servicio_ruta where ruta_id = p_ruta_id);
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

-- Limpieza de eventos antiguos (se invoca desde una tarea programada)
create or replace function limpiar_eventos_uso(p_dias integer) returns integer
language plpgsql as $$
declare v_filas integer;
begin
  delete from evento_uso where ocurrido_en < now() - make_interval(days => p_dias);
  get diagnostics v_filas = row_count;
  return v_filas;
end;
$$;

-- ---------- 0004: seguridad a nivel de base de datos ----------
-- RLS activada y SIN políticas: nadie con la clave anónima o de usuario lee tablas directamente.
-- El backend usa la clave service_role (que omite RLS) y aplica la autorización por rol y empresa.
alter table empresa               enable row level security;
alter table perfil_usuario        enable row level security;
alter table permiso_rol           enable row level security;
alter table ruta                  enable row level security;
alter table ruta_trazado          enable row level security;
alter table paradero              enable row level security;
alter table ruta_paradero         enable row level security;
alter table hito                  enable row level security;
alter table servicio_ruta         enable row level security;
alter table dia_festivo           enable row level security;
alter table horario               enable row level security;
alter table frecuencia            enable row level security;
alter table buseta                enable row level security;
alter table conductor             enable row level security;
alter table asignacion            enable row level security;
alter table rodamiento            enable row level security;
alter table turno                 enable row level security;
alter table credencial_fuente_gps enable row level security;
alter table posicion_buseta       enable row level security;
alter table aviso                 enable row level security;
alter table aviso_afecta          enable row level security;
alter table favorito              enable row level security;
alter table alerta_llegada        enable row level security;
alter table suscripcion_push      enable row level security;
alter table notificacion          enable row level security;
alter table evento_uso            enable row level security;
alter table parametro_global      enable row level security;
alter table importacion           enable row level security;

revoke execute on all functions in schema public from anon, authenticated;

-- ---------- 0005: semillas (valores PROPUESTOS; editables por el administrador, HU-A04) ----------
insert into parametro_global (clave, valor, descripcion, minimo, maximo) values
  ('radio_busqueda_m',            '800',   'Radio para rutas y paraderos cercanos (HU-P01)', 100, 5000),
  ('radio_caminata_m',            '500',   'Distancia máxima a pie en la planificación (HU-P07)', 100, 2000),
  ('radio_transbordo_m',          '200',   'Distancia máxima entre paraderos de un transbordo', 50, 1000),
  ('radio_hito_m',                '300',   'Radio para considerar que una ruta pasa por un hito (HU-P09)', 50, 2000),
  ('velocidad_default_kmh',       '20',    'Velocidad usada en el ETA si la buseta no reporta una válida', 5, 60),
  ('umbral_posicion_obsoleta_s',  '60',    'Segundos tras los cuales una posición se considera sin señal', 10, 600),
  ('intervalo_refresco_cliente_s','5',     'Cada cuánto consulta el cliente las busetas en vivo', 2, 60),
  ('distancia_aviso_llegada_m',   '300',   'Distancia por defecto para avisar la llegada (HU-P11)', 50, 2000),
  ('enfriamiento_alerta_min',     '10',    'Minutos antes de volver a avisar la misma alerta', 1, 120),
  ('umbral_desvio_m',             '100',   'Distancia a la ruta a partir de la cual se considera desvío', 30, 500),
  ('longitud_max_aviso',          '500',   'Caracteres máximos del cuerpo de un aviso (HU-J05)', 50, 2000),
  ('max_opciones_viaje',          '3',     'Opciones devueltas por la planificación', 1, 10),
  ('max_filas_excel',             '5000',  'Filas máximas por archivo importado', 10, 20000),
  ('tamano_max_excel_mb',         '5',     'Tamaño máximo del archivo importado', 1, 20),
  ('dias_max_rodamiento_adelante','15',    'Días hacia adelante en que se puede definir un rodamiento', 1, 60),
  ('rango_max_estadisticas_dias', '365',   'Rango máximo de consulta de estadísticas', 7, 730),
  ('retencion_eventos_dias',      '180',   'Días que se conservan los eventos de uso', 30, 730);
-- Valor PROVISIONAL: el equipo debe ajustarlo con el mapa real (zona de Manizales y alrededores).
insert into parametro_global (clave, valor, descripcion) values
  ('caja_ciudad', '{"minLat":4.95,"maxLat":5.20,"minLng":-75.65,"maxLng":-75.40}',
   'Caja geográfica fuera de la cual se rechazan posiciones GPS');
