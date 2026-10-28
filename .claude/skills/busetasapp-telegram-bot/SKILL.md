---
name: busetasapp-telegram-bot
description: Guía para construir el chatbot de Telegram de BusetasApp (rutas cerca de mí, ¿cuándo llega?, horarios, avisos, ayuda y alertas "avisarme cuando esté cerca"). Úsala al tocar backend/src/adaptadores_externos/bot_telegram.py.
---

# Chatbot de Telegram

Referencia visual y de textos: `docs/referencia/mockup-chatbot-telegram.png` y `.html`. Reglas del bot: `backend/CLAUDE.md` §10.

## Principios

- Es un **adaptador de entrada**: solo llama a casos de uso (`consultar_rutas_cercanas`, `calcular_eta_paradero`, `consultar_horarios`, `consultar_avisos_vigentes`, `crear_alerta_llegada`, `buscar_*`). Nunca SQL.
- Librería `python-telegram-bot` v21+ asíncrona, modo *polling* (no necesita servidor público). Arranca y se detiene en el *lifespan* de FastAPI; sin `TELEGRAM_BOT_TOKEN` queda desactivado sin romper nada.
- **Sin LLM.** Texto libre por palabras clave sin acentos; sin coincidencia → menú.
- La ubicación del usuario solo vive en memoria del chat (≤ 10 min). No se guarda.

## Conversación (copiar el tono del mockup)

1. `/start`: "¡Hola! Soy el asistente de BusetasApp. Te ayudo con las rutas de buses de Manizales: qué ruta te sirve, cada cuánto sale y cuándo llega. ¿Qué quieres hacer?" + teclado: **Rutas cerca de mí** · **¿Cuándo llega?** · **Horarios** · **Avisos** · **Ayuda**. Segundo mensaje: "También puedes escribirme tu pregunta, por ejemplo: «¿Qué ruta va a Villamaría?»". Incluir "Datos de ejemplo".
2. **Rutas cerca de mí:** "Compárteme tu ubicación para buscar. No la guardo." con botón de teclado que solicita ubicación → "Encontré N rutas a menos de 500 m:" y una línea por ruta/empresa "Ruta Sideral · paradero a 120 m" + botones **Ver ruta** y **¿Cuándo llega?**.
3. **¿Cuándo llega?:** con GPS → "Ruta Sideral · paradero a 120 m / Próxima buseta en 4 min / Según el GPS · actualizado hace 10 s" + botones **Avisarme cuando esté cerca** y **Ver en mapa**. Sin GPS → aviso destacado "Sin señal GPS en este momento. Te doy un estimado por horario: sale cada 4 min aprox. / Estimado por horario, no es una posición en vivo".
4. **Avisarme cuando esté cerca:** crea la alerta con el `chat_id` → "Listo, te aviso cuando la Sideral esté a 300 m de tu paradero." Cuando el sistema la dispara, el bot escribe primero.
5. **Horarios / Avisos:** elegir ruta (teclado en línea) → horarios por tipo de día ("Información pendiente de actualización" si falta); avisos vigentes con su origen.
6. **Ayuda:** qué es BusetasApp, qué hace el bot, que los datos son de ejemplo, los 4 roles en una línea cada uno, cómo conseguir la app (el APK se pide al equipo).

## Comprobaciones

- Probar cada botón y un texto libre («cuándo llega la sideral», «horarios el cable», «ruta a Villamaría»).
- Con el simulador activo: crear alerta, esperar el mensaje a 300 m y comprobar que no se repite antes del enfriamiento.
- Con Serviturismo sin GPS: ver el mensaje de respaldo por horario.

## Aviso de desvío (SPEC-009)

Si una alerta activa del chat está en una ruta cuya buseta se desvía del trazado, escribe primero: «⚠️ La buseta N se desvió de su recorrido. Tu llegada puede cambiar.» Una sola vez por episodio. Probar con el escenario `desvio` del Panel de demo. «¿Qué ruta va a Villamaría?» debe encontrar la ruta de Villamaría.
