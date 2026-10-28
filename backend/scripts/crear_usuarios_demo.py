"""Crea las cuentas de demostración (docs/01 §5) en Supabase Auth y su fila en perfil_usuario.

Uso:
  python scripts/crear_usuarios_demo.py             # simulacro: muestra qué haría, no llama a nada
  python scripts/crear_usuarios_demo.py --aplicar   # llama a la API admin de Supabase Auth y escribe en la BD

Requiere en backend/.env: SUPABASE_URL, SUPABASE_SERVICE_ROLE_KEY, DATABASE_URL y DEMO_PASSWORD_*.
Las empresas deben existir (corre antes cargar_semillas --aplicar). No imprime contraseñas ni claves.
La clave service_role solo vive en el backend.
"""

from __future__ import annotations

import sys

import httpx

from _comun import conectar
from nucleo.configuracion import obtener_configuracion

# (correo, nombre, rol, empresa, variable de contraseña)
CUENTAS = [
    ("admin@busetasapp.example", "Administrador (ejemplo)", "administrador", None, "demo_password_admin"),
    ("movilidad@alcaldia.example", "Secretaría de Movilidad (ejemplo)", "secretaria_movilidad", None, "demo_password_movilidad"),
    ("jefe@sideral.example", "Jefe Sideral (ejemplo)", "jefe_operaciones", "Sideral", "demo_password_jefe"),
    ("jefe@socobuses.example", "Jefe Socobuses (ejemplo)", "jefe_operaciones", "Socobuses", "demo_password_jefe"),
    ("pasajera@correo.example", "Pasajera (ejemplo)", "pasajero", None, "demo_password_pasajero"),
]


def _cabeceras(clave: str) -> dict[str, str]:
    return {"apikey": clave, "Authorization": f"Bearer {clave}", "Content-Type": "application/json"}


def obtener_o_crear_usuario(cliente: httpx.Client, base: str, clave: str, correo: str, password: str) -> str:
    r = cliente.post(f"{base}/auth/v1/admin/users", headers=_cabeceras(clave),
                     json={"email": correo, "password": password, "email_confirm": True})
    if r.status_code in (200, 201):
        return r.json()["id"]
    if r.status_code == 422:  # ya existe: se busca para reutilizar su id
        pagina = 1
        while True:
            lista = cliente.get(f"{base}/auth/v1/admin/users", headers=_cabeceras(clave),
                                params={"page": pagina, "per_page": 200})
            lista.raise_for_status()
            usuarios = lista.json().get("users", [])
            for u in usuarios:
                if (u.get("email") or "").lower() == correo.lower():
                    return u["id"]
            if len(usuarios) < 200:
                break
            pagina += 1
    raise RuntimeError(f"No se pudo crear/ubicar la cuenta {correo.split('@')[0]}@… (HTTP {r.status_code})")


def main() -> int:
    if "--aplicar" not in sys.argv:
        print("Modo simulacro. Con --aplicar se crearían estas cuentas en Supabase Auth + perfil_usuario:")
        for correo, _, rol, empresa, _ in CUENTAS:
            print(f" - {correo} · {rol}" + (f" · {empresa}" if empresa else ""))
        return 0
    cfg = obtener_configuracion()
    clave = cfg.supabase_service_role_key.get_secret_value()
    if not cfg.supabase_url or not clave:
        raise SystemExit("Faltan SUPABASE_URL o SUPABASE_SERVICE_ROLE_KEY en backend/.env")
    print(f"Supabase Auth destino: {cfg.supabase_url}")
    with httpx.Client(timeout=30) as cliente, conectar() as conn:
        for correo, nombre, rol, empresa, variable in CUENTAS:
            password = getattr(cfg, variable).get_secret_value()
            if not password:
                raise SystemExit(f"Falta {variable.upper()} en backend/.env")
            usuario_id = obtener_o_crear_usuario(cliente, cfg.supabase_url.rstrip("/"), clave, correo, password)
            empresa_id = None
            if empresa:
                fila = conn.execute("select id from empresa where nombre=%s and estado='activo'", (empresa,)).fetchone()
                if not fila:
                    raise SystemExit(f"La empresa {empresa} no existe: corre antes cargar_semillas.py --aplicar")
                empresa_id = fila[0]
            conn.execute(
                "insert into perfil_usuario (id, correo, nombre, rol, empresa_id) values (%s, %s, %s, %s::rol_usuario, %s) "
                "on conflict (id) do update set correo=excluded.correo, nombre=excluded.nombre, rol=excluded.rol, "
                "empresa_id=excluded.empresa_id, activo=true",
                (usuario_id, correo, nombre, rol, empresa_id),
            )
            print(f" - perfil listo: {rol}" + (f" · {empresa}" if empresa else ""))
    print("Cuentas demo listas.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
