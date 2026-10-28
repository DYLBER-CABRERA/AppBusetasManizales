# web-admin/ — Paneles de escritorio (Jefe de operaciones, Secretaría de Movilidad, Administrador)

> Lee antes: `../CLAUDE.md`, `../docs/01-alcance-y-datos-simulados.md`, `../docs/03-contrato-api.md` y los mockups `../docs/referencia/presentacion-mockup-{jefe,secretaria,admin}.png`.
> Solo editas `web-admin/`. Si falta un endpoint, anótalo en `../docs/solicitudes-entre-agentes.md` y trabaja con un *mock*.

## 1. Misión

Una **sola aplicación Next.js** con tres paneles según el rol. Se usa **en PC** (escritorio ≥ 1024 px; debe verse bien en 1280 px y no romperse en pantallas menores). El pasajero **no** usa esta app (usa Flutter y Telegram).

## 2. Stack y dependencias permitidas

| Uso | Paquete |
|---|---|
| Framework | `next` (App Router), `react`, `typescript` |
| Estilos | `tailwindcss` |
| Auth | `@supabase/supabase-js`, `@supabase/ssr` (**solo Auth**; los datos van por la API del backend) |
| Datos | `@tanstack/react-query`, `openapi-typescript` + `openapi-fetch` (tipos generados desde `../contrato/openapi.json`) |
| Formularios | `react-hook-form`, `zod` |
| Mapas | `leaflet`, `react-leaflet` (teselas por `NEXT_PUBLIC_MAP_TILE_URL`, atribución visible) |
| Gráficas | `recharts` |
| Calidad | `eslint`, `typescript` estricto |

Nada más sin anotarlo en `../docs/decisiones-agentes.md`. Fija versiones al crear el proyecto. No uses la clave `service_role`. El mapa de Leaflet se importa con carga dinámica sin SSR.

## 3. Estructura

```text
web-admin/
  package.json  .env.example
  src/
    middleware.ts                 # protege rutas por sesión y rol
    app/
      login/page.tsx              # correo + contraseña (Supabase Auth); redirige según rol
      (panel)/
        jefe/        rodamiento/ asignar/ horarios/ avisos/ excel/ uso/
        secretaria/  rutas/ paraderos/ movilidad/
        admin/       usuarios/ empresas/ parametros/ fuentes-gps/ avisos/ demo/
      layout.tsx
    componentes/                  # Tabla, Formulario, Modal, Aviso, BannerEjemplo, MapaBase, Esqueleto, Vacio...
    lib/
      api.ts                      # cliente tipado, adjunta el JWT, traduce errores del contrato
      auth.ts                     # sesión, rol, empresa
      tipos-api.d.ts              # GENERADO: npx openapi-typescript ../contrato/openapi.json
    estilos/
```

Guardia de rutas: un rol solo entra a su carpeta (`jefe` → `/jefe`, etc.); el administrador puede entrar a `/secretaria` y `/jefe` como superconjunto (BR-07) y ve el selector de empresa. Un 403 del backend muestra "No tienes permiso para esta sección".

## 4. Layout y marca

Barra lateral izquierda por rol + contenido; arriba el **banner permanente** "Datos de ejemplo · no son rutas oficiales" y el nombre/rol del usuario con "Cerrar sesión". Paleta y tipografías: `../CLAUDE.md` §6. Estados vacíos con título + causa + siguiente paso. Esqueletos de carga (nunca pantalla en blanco). Errores de red: banner rojo con **Reintentar**, conservando lo ya cargado. Texto de interfaz: el de `../docs/referencia/03-actividad-4-ux-prototipos.md` §7.

## 5. Pantallas

### 5.1 Jefe de operaciones (solo su empresa)

| Ruta | Contenido | Reglas |
|---|---|---|
| `/jefe/rodamiento` | Selector de fecha (por defecto **mañana**; hoy a hoy + `dias_max_rodamiento_adelante`). Tabla **Buseta · Ruta · Conductor · Salida · Fin estimado**, editable en línea. Estado (`borrador`/`publicado`). | Al guardar muestra `advertencias`: banner amarillo "Hay N solapamiento(s). La buseta 1520 sale a las 06:40 y todavía está en el turno de las 06:00 a las 06:50." con botón **Corregir** que enfoca la fila; filas en conflicto con fondo rojo ladrillo claro **y** texto (no solo color). **Publicar rodamiento** deshabilitado con "Corrige el solapamiento para poder publicar." Si el servidor responde 409 `CONFLICTO_VERSION`: modal "Alguien más cambió esto. Recarga para ver los cambios." |
| `/jefe/asignar` | Formulario Ruta (solo `GET /mis-servicios`) · Buseta · Conductor · Salida · Fin → **agrega el turno al borrador** de la fecha elegida | Texto de ayuda: "Solo aparecen las rutas que la Secretaría asignó a tu empresa." y "Una buseta puede tener varias rutas en el día." |
| `/jefe/horarios` | Horarios y frecuencias por servicio y tipo de día; alta de busetas y conductores | Valida cierre ≥ última salida, franjas sin solape y min ≤ max; errores bajo el campo |
| `/jefe/avisos` | Título + mensaje con contador "0 de 500 caracteres" (el máximo viene de `parametro_global`) + **Publicar aviso**; lista de los avisos de la empresa con **Retirar** | Toast "Publicado" |
| `/jefe/excel` | Pantalla informativa con la carga **desactivada**: "No incluido en el prototipo" | HU-J03 fuera |
| `/jefe/uso` | Barras de consultas por día y tabla por ruta (`GET /estadisticas/uso`) | Sin datos → "Sin datos" |

### 5.2 Secretaría de Movilidad

| Ruta | Contenido | Reglas |
|---|---|---|
| `/secretaria/rutas` | Tarjetas de las rutas con empresas y botón **Eliminar**; formulario **Registrar ruta**: nombre, tipo de recorrido (**solo "Circular"** en el prototipo), variante de (opcional), empresa(s) y código público/interno opcionales, y **selector de paraderos en orden** (lista + mapa) | Ruta ya operada por otra empresa → modal "Esta ruta ya la opera otra empresa. Si también la opera esta empresa, cada una tendrá su propio horario y frecuencia." con **Confirmar compartida**. Eliminar con turnos futuros → modal con la lista y "Al eliminarla se cancelan los turnos futuros." → `confirmar=true`. Editar usa `version` |
| `/secretaria/paraderos` | Mapa para tocar y fijar la ubicación + nombre + **Guardar paradero**; lista con editar/eliminar | Duplicado → "Ya existe un paradero llamado X a 12 m. Edítalo o cambia el nombre." Baja de uno usado por rutas → advertencia con la lista |
| `/secretaria/movilidad` | Qué pasa (Cierre · Desvío · Obra · Condición), mensaje, rutas y paraderos afectados (selección múltiple), vigencia opcional, **Publicar cambio** | Origen `movilidad` lo fija el backend |

### 5.3 Administrador

| Ruta | Contenido | Reglas |
|---|---|---|
| `/admin/usuarios` | Búsqueda por correo, lista (correo · rol · empresa · activo), **Editar**, formulario **Crear cuenta** (correo, rol, empresa solo para jefe) | No se puede quitar el rol al último administrador (409 → mensaje) |
| `/admin/empresas` | Lista y edición con versión | — |
| `/admin/parametros` | Distancia de aviso de llegada, segundos para sin señal, máximo de caracteres de un aviso, etc., con mínimo y máximo | "Entre 50 y 2000. Se aplica a las alertas nuevas." Fuera de rango → error en el campo |
| `/admin/fuentes-gps` | Claves por empresa ("Último envío hace 4 s" / "Sin envíos"), **Revocar**, **Generar clave nueva** | La clave se muestra **una sola vez**: "Copia la clave ahora. No podrás verla otra vez." |
| `/admin/avisos` | Igual que el del jefe, con origen `aplicativo` | — |
| `/admin/demo` | **Panel de demo** (visible solo si `GET /demo/estado` responde 200): tabla de busetas (lateral, empresa, emitiendo, última posición), mapa con las busetas en vivo (WebSocket `/ws/rutas/{rutaId}`), y controles: **Perder señal / Restaurar** por buseta o empresa, **Activar GPS de Serviturismo**, **Desvío**, **Fijar hora** (selector `HH:MM` y "Volver a la hora real"), **Acelerar** (0.5–5×), **Reiniciar simulación** | Cada acción llama a `POST /demo/escenarios` y confirma con un toast |

## 6. Comportamiento común

- **Autenticación:** inicio de sesión con Supabase Auth; el JWT se envía como `Authorization: Bearer`. Tras iniciar sesión llama a `GET /yo` (`{usuarioId, correo, rol, empresaId, empresaNombre}`) para saber el rol y la empresa, y redirige al panel correspondiente. Sesión vencida o 401 → volver a `/login`. Nunca confíes en el rol guardado en el navegador para autorizar: el backend decide.
- **Control de versión:** toda edición envía `version`; en 409 `CONFLICTO_VERSION` ofrece Recargar.
- **Toasts** con el mismo verbo del botón (Publicar → "Publicado").
- **Accesibilidad:** contraste ≥ 4.5:1, foco visible, navegación por teclado, etiquetas en los campos, el color nunca es el único canal.
- Idioma `es`; horas `HH:MM` 24 h; zona `America/Bogota`.

## 7. Orden de construcción

1. **W0** Proyecto, Tailwind, tema, layout con banner, login con Supabase, guardia por rol, cliente de API tipado desde `../contrato/openapi.json` (con *mocks* mientras el backend responda 501).
2. **W1** Jefe: rodamiento + asignar (el flujo estrella de la demo).
3. **W2** Admin: panel de demo (necesita backend H2) + parámetros + fuentes GPS.
4. **W3** Secretaría: rutas, paraderos, movilidad.
5. **W4** Jefe: horarios, avisos, uso; Admin: usuarios, empresas, avisos.
6. **W5** Pulido: estados vacíos/errores, textos, rendimiento, `npm run lint && npm run build` sin errores.

## 8. Pruebas

- `npm run lint` y `npm run build` limpios.
- Recorridos manuales documentados en tu reporte: (a) jefe crea solapamiento → ve el aviso → corrige → publica; (b) Secretaría registra una ruta compartida (modal) y elimina otra (modal); (c) admin crea una clave GPS y comprueba que solo se muestra una vez; (d) 409 de versión abriendo dos pestañas.

## 8 bis. Ajustes por la revisión de las SPECs (tienen prioridad sobre las secciones anteriores)

- **Rodamiento (HU-J01):** si al guardar la API responde 409 `CONFLICTO_NEGOCIO` por reemplazo de asignación, abre un modal «La ruta ya tiene asignada la buseta 1520 a las 06:00. ¿Reemplazarla por la 1544?» con **Reemplazar** (reenvía con `confirmarReemplazo=true`) y **Cancelar**. Textos en `docs/01-alcance-y-datos-simulados.md` §3.1.
- **Jefe y rutas (HU-J02):** el jefe **no** crea ni edita rutas ni paraderos (BR-03). Su «datos operativos» son horarios, frecuencias, busetas y conductores de su empresa.
- **Estadísticas (HU-J06):** la demo trae 14 días de uso simulado (doc 01 §2.9). Aun así conserva el estado vacío «Sin datos».
- **Villamaría** aparece como una ruta más en los selectores y mapas.

## 9. Qué NO hacer

- No llamar a tablas de Supabase desde el navegador.
- No implementar importación de Excel ni Web Push.
- No ofrecer tipo de recorrido "Lineal" (D-P02).
- No inventar campos o endpoints fuera del contrato.
