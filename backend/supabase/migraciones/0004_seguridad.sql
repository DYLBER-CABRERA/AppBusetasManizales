-- 0004: seguridad a nivel de base de datos.
-- RLS activada y SIN políticas: nadie con la clave anónima o de usuario lee tablas directamente.
-- El backend entra con la cadena de conexión y aplica la autorización por rol y empresa (D-P06: sin RLS fina).
-- Quitadas las líneas de RLS de las tablas eliminadas.
alter table empresa               enable row level security;
alter table perfil_usuario        enable row level security;
alter table ruta                  enable row level security;
alter table ruta_trazado          enable row level security;
alter table paradero              enable row level security;
alter table ruta_paradero         enable row level security;
alter table hito                  enable row level security;
alter table servicio_ruta         enable row level security;
alter table horario               enable row level security;
alter table frecuencia            enable row level security;
alter table buseta                enable row level security;
alter table conductor             enable row level security;
alter table rodamiento            enable row level security;
alter table turno                 enable row level security;
alter table credencial_fuente_gps enable row level security;
alter table posicion_buseta       enable row level security;
alter table aviso                 enable row level security;
alter table aviso_afecta          enable row level security;
alter table favorito              enable row level security;
alter table alerta_llegada        enable row level security;
alter table evento_uso            enable row level security;
alter table parametro_global      enable row level security;

revoke execute on all functions in schema public from anon, authenticated;
