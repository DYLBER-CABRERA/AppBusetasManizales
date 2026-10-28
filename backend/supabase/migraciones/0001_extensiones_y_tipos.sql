-- 0001: extensiones, tipos y utilidades.
-- Recorte del esquema validado (docs/referencia/esquema.sql) según backend/CLAUDE.md §6.
-- Eliminados: tipos canal_notificacion, estado_notificacion, tipo_importacion, estado_importacion.

create extension if not exists postgis with schema public;
create extension if not exists pg_trgm with schema public;
create extension if not exists unaccent with schema public;
create extension if not exists btree_gist with schema public;

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
create type tipo_evento_uso    as enum ('mapa','detalle_ruta','horarios','frecuencias','busetas_vivo','eta','busqueda','planificacion');

create or replace function marcar_actualizacion() returns trigger
language plpgsql as $$
begin
  new.actualizado_en := now();
  return new;
end;
$$;
