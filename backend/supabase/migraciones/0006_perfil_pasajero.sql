-- 0006: datos de contacto del pasajero (registro con perfil completo). NO aplicada automáticamente:
-- ver backend/scripts/aplicar_migracion.py (simulacro por defecto; --aplicar la ejecuta en UNA transacción).
-- perfil_usuario ya tenía `nombre`; se agregan `apellido` y `celular` (móvil colombiano normalizado: 10 dígitos, empieza por 3).
alter table perfil_usuario add column if not exists apellido text;
alter table perfil_usuario add column if not exists celular  text;

do $$
begin
  if not exists (select 1 from pg_constraint where conname = 'ck_perfil_celular') then
    alter table perfil_usuario
      add constraint ck_perfil_celular check (celular is null or celular ~ '^3[0-9]{9}$');
  end if;
end
$$;
