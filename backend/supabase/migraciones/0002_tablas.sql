-- 0002: tablas y disparadores.
-- Eliminadas: permiso_rol, dia_festivo, asignacion, suscripcion_push, notificacion, importacion.
-- Modificadas: alerta_llegada (usuario_id admite null + telegram_chat_id, D-P08) y aviso (+ tipo_cambio, decisión del equipo).

-- ---------- empresas y usuarios ----------
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

-- ---------- red de transporte (la gestiona la Secretaría, BR-04) ----------
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

-- ---------- horarios y frecuencias (los edita el jefe de su empresa) ----------
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

-- ---------- operación de las empresas (BR-03) ----------
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

-- ---------- seguimiento ----------
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

-- ---------- comunicación ----------
create table aviso (
  id          uuid primary key default gen_random_uuid(),
  origen      origen_aviso not null,
  empresa_id  uuid references empresa(id),
  tipo_cambio text check (tipo_cambio is null or tipo_cambio in ('cierre','desvio','obra','condicion')),  -- avisos de movilidad (SM05)
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

-- ---------- pasajero ----------
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

-- D-P08: en Telegram el chat_id hace de identidad; en la app, usuario_id. Exactamente uno de los dos.
create table alerta_llegada (
  id                    uuid primary key default gen_random_uuid(),
  usuario_id            uuid references perfil_usuario(id) on delete cascade,
  telegram_chat_id      bigint,
  ruta_id               uuid not null references ruta(id),
  paradero_id           uuid not null references paradero(id),
  sentido               sentido_ruta not null,
  distancia_aviso_m     integer not null check (distancia_aviso_m between 50 and 2000),
  estado                estado_alerta not null default 'activa',
  ultima_notificacion_en timestamptz,
  version               integer not null default 1,
  creada_en             timestamptz not null default now(),
  check ((usuario_id is not null) <> (telegram_chat_id is not null))
);
create unique index ux_alerta_unica_usuario on alerta_llegada (usuario_id, ruta_id, paradero_id, sentido)
  where estado <> 'desactivada' and usuario_id is not null;
create unique index ux_alerta_unica_telegram on alerta_llegada (telegram_chat_id, ruta_id, paradero_id, sentido)
  where estado <> 'desactivada' and telegram_chat_id is not null;

-- ---------- plataforma ----------
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

-- Disparadores de marca de tiempo (sin cambios)
create trigger tg_empresa_act        before update on empresa        for each row execute function marcar_actualizacion();
create trigger tg_perfil_act         before update on perfil_usuario for each row execute function marcar_actualizacion();
create trigger tg_ruta_act           before update on ruta           for each row execute function marcar_actualizacion();
create trigger tg_paradero_act       before update on paradero       for each row execute function marcar_actualizacion();
create trigger tg_servicio_act       before update on servicio_ruta  for each row execute function marcar_actualizacion();
create trigger tg_buseta_act         before update on buseta         for each row execute function marcar_actualizacion();
create trigger tg_conductor_act      before update on conductor      for each row execute function marcar_actualizacion();
create trigger tg_rodamiento_act     before update on rodamiento     for each row execute function marcar_actualizacion();
create trigger tg_parametro_act      before update on parametro_global for each row execute function marcar_actualizacion();
