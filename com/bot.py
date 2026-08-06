import telebot
import os
import pytz
from dotenv import load_dotenv
from logic.logic import AgenteAutonomoHoras, AgenteAsistenciaMaterias, EstadoGestor, guardar_log
from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton, BotCommand
from datetime import datetime

tz_py = pytz.timezone('America/Buenos_Aires')
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
load_dotenv(dotenv_path=os.path.join(BASE_DIR, ".env"))

class GAMMA:
    def __init__(self):
        self.token = os.getenv('TOKEN')
        self.sheet_id = os.getenv('SPREADSHEET_ID')

        if not all([self.token, self.sheet_id]):
            raise ValueError("Faltan variables en el archivo .env (TOKEN, CHAT_ID o SPREADSHEET_ID)")

        self.bot = telebot.TeleBot(self.token, threaded=False)

        chat_id_raw = os.getenv("CHAT_ID", "")
        self.usuarios_permitidos = {int(chat_id_raw)} if chat_id_raw.strip() else set()
        print(f"✅ Usuarios autorizados: {self.usuarios_permitidos}", flush=True)

        # 🆕 CACHÉ TEMPORAL DE AVISOS (Fase 3)
        # El caché en memoria (self.avisos_pendientes) fue reemplazado por EstadoGestor (JSON persistente)

        self.agente_excel = AgenteAutonomoHoras(spreadsheet_id=self.sheet_id)
        self.agente_materias = AgenteAsistenciaMaterias()
        self._registrar_manejadores()
        self._registrar_comandos_menu()

    def _es_autorizado(self, user_id: int) -> bool:
        return user_id in self.usuarios_permitidos

    def _rechazar(self, message):
        user = message.from_user
        alerta = (
            f"🚫 Acceso no autorizado\n"
            f"ID: {user.id} | @{user.username or 'sin username'}\n"
            f"Nombre: {user.first_name} {user.last_name or ''}"
        )
        print(alerta, flush=True)
        guardar_log(alerta)
        self.bot.reply_to(message, "🚫 No tenés acceso a este bot.")

    def _registrar_manejadores(self):
        # ── Comando START ─────────────────────────────────────────────────────
        @self.bot.message_handler(commands=['start'])
        def comando_start(message):
            if not self._es_autorizado(message.from_user.id):
                self._rechazar(message)
                return
            self._cmd_start(message)

        # ── Comando MARCAR ────────────────────────────────────────────────────
        @self.bot.message_handler(commands=['marcar'])
        def wrapper_registro(message):
            if not self._es_autorizado(message.from_user.id):
                self._rechazar(message)
                return
            self._mostrar_opciones_marcado(message)

        @self.bot.callback_query_handler(func=lambda call: call.data.startswith("marcar_"))
        def callback_marcado(call):
            if not self._es_autorizado(call.from_user.id):
                self.bot.answer_callback_query(call.id, "🚫 No estás autorizado.", show_alert=True)
                return
            self._procesar_callback_marcado(call)

        # ── Comando CIERRE ────────────────────────────────────────────────────
        @self.bot.message_handler(commands=['cierre'])
        def comando_cierre(message):
            if not self._es_autorizado(message.from_user.id):
                self._rechazar(message)
                return
            self._mostrar_confirmacion_cierre(message)

        @self.bot.callback_query_handler(func=lambda call: call.data.startswith("cierre_"))
        def callback_cierre(call):
            if not self._es_autorizado(call.from_user.id):
                self.bot.answer_callback_query(call.id, "🚫 No estás autorizado.", show_alert=True)
                return
            self._procesar_callback_cierre(call)

        # ── Comando REPORTE ──────────────────────────────────────────────────
        @self.bot.message_handler(commands=['reporte'])
        def comando_reporte(message):
            if not self._es_autorizado(message.from_user.id):
                self._rechazar(message)
                return
            self._mostrar_selector_hojas(message)

        @self.bot.callback_query_handler(func=lambda call: call.data.startswith("reporte_"))
        def callback_reporte(call):
            if not self._es_autorizado(call.from_user.id):
                self.bot.answer_callback_query(call.id, "🚫 No estás autorizado.", show_alert=True)
                return
            self._procesar_callback_reporte(call)

        # ── 🆕 COMANDO AVISO (Fase 3) ─────────────────────────────────────────
        @self.bot.message_handler(commands=['aviso'])
        def comando_aviso(message):
            if not self._es_autorizado(message.from_user.id):
                self._rechazar(message)
                return

            # Extrae la frase que viene después del comando /aviso
            partes = message.text.split(maxsplit=1)
            if len(partes) > 1:
                self._procesar_frase_aviso(message, partes[1])
            else:
                # Si escribió solo /aviso, le pide amablemente la frase usando el flujo secuencial
                msg = self.bot.reply_to(
                    message,
                    "✍️ *Por favor, escribí qué querés agendar.*\n"
                    "Ejemplo: `entregar el laboratorio de mecatrónica mañana a las 4 y media`",
                    parse_mode="Markdown"
                )
                self.bot.register_next_step_handler(msg, self._capturar_frase_aviso_secuencial)

        @self.bot.callback_query_handler(func=lambda call: call.data.startswith("aviso_"))
        def callback_aviso(call):
            if not self._es_autorizado(call.from_user.id):
                self.bot.answer_callback_query(call.id, "🚫 No estás autorizado.", show_alert=True)
                return
            self._procesar_callback_aviso(call)

        # ── Comando AVISOS (CORREGIDO Y INTEGRADO) ─────────────────────────────
        @self.bot.message_handler(commands=['avisos'])
        def comando_avisos(message):
            if not self._es_autorizado(message.from_user.id):
                self._rechazar(message)
                return
            self._cmd_avisos(message)

        @self.bot.callback_query_handler(func=lambda call: call.data.startswith("borrar_"))
        def callback_borrar_aviso(call):
            if not self._es_autorizado(call.from_user.id):
                self.bot.answer_callback_query(call.id, "🚫 No estás autorizado.", show_alert=True)
                return
            self._procesar_callback_borrar_aviso(call)

        # ── Comando MARCAR MATERIA ─────────────────────────────────────────────
        @self.bot.message_handler(commands=['marcar_materia'])
        def comando_marcar_materia(message):
            if not self._es_autorizado(message.from_user.id):
                self._rechazar(message)
                return
            msg = self.bot.reply_to(message, "⚙️ Registrando asistencia en la materia actual...")
            resultado = self.agente_materias.marcar_asistencia()
            self.bot.edit_message_text(resultado, message.chat.id, msg.message_id, parse_mode="Markdown")

    def _registrar_comandos_menu(self):
        """Sincroniza el menú '/' de Telegram con los comandos del bot."""
        comandos = [
            BotCommand("marcar",   "Registra hora de marcación."),
            BotCommand("marcar_materia", "Registrar asistencia a materia actual."),
            BotCommand("reporte",  "Generar reporte PDF de un período anterior."),
            BotCommand("aviso",    "Agendar un hito o recordatorio con IA."),
            BotCommand("avisos",   "Ver lista de avisos activos."),
            BotCommand("cierre",   "Ejecutar cierre de período de marcaciones."),
            BotCommand("start",    "Actualizar menú de comandos"),
        ]
        self.bot.set_my_commands(comandos)
        print("✅ Menú de comandos actualizado.", flush=True)

    def _cmd_start(self, message):
        try:
            self._registrar_comandos_menu()
            texto = (
                "🤖 *Bot de Gestión Avanzada (GAMMA)*\n"
                "━━━━━━━━━━━━━━━━━━━━━\n"
                "Menú de comandos sincronizado ✅\n\n"
                "*Comandos disponibles:*\n"
                "▶️ /marcar  — Registrar entrada o salida\n"
                "📚 /marcar\\_materia — Marcar asistencia a materias\n"
                "📄 /reporte — Generar PDF de un período anterior\n"
                "✍️ /aviso   — Agendar recordatorios con lenguaje natural\n"
                "📋 /avisos  — Gestionar recordatorios activos\n"
                "🔒 /cierre  — Ejecutar cierre de período\n"
                "🔄 /start   — Reestablecer este menú\n"
                "━━━━━━━━━━━━━━━━━━━━━"
            )
            self.bot.reply_to(message, texto, parse_mode="Markdown")
        except Exception as e:
            self.bot.reply_to(message, f"❌ Error al actualizar el menú: {e}")

    # ── Métodos Auxiliares de Marcado y Cierre ───────────────────────────────
    def _mostrar_opciones_marcado(self, message):
        teclado = InlineKeyboardMarkup()
        teclado.row(
            InlineKeyboardButton("▶️ Marcar",         callback_data="marcar_normal"),
            InlineKeyboardButton("🚪 Salida directa", callback_data="marcar_directo"),
        )
        self.bot.send_message(message.chat.id, "¿Qué tipo de registro querés hacer hoy?", reply_markup=teclado)

    def _procesar_callback_marcado(self, call):
        try:
            self.bot.answer_callback_query(call.id)
            modo = "directo" if call.data == "marcar_directo" else "normal"
            self.bot.edit_message_text("⚙️ Comando recibido. Abriendo Google Sheets...", call.message.chat.id, call.message.message_id)

            respuesta = self.agente_excel.ejecutar_marcado_para_bot(modo=modo)
            bloque_avisos = self.agente_excel.verificar_avisos_activos()

            self.bot.edit_message_text(f"{respuesta}{bloque_avisos}", call.message.chat.id, call.message.message_id, parse_mode="Markdown")
        except Exception as e:
            self.bot.send_message(call.message.chat.id, f"❌ Error interno: {type(e).__name__} - {str(e)}")

    def _mostrar_confirmacion_cierre(self, message):
        teclado = InlineKeyboardMarkup()
        teclado.row(
            InlineKeyboardButton("✅ Confirmar", callback_data="cierre_confirmar"),
            InlineKeyboardButton("❌ Cancelar",  callback_data="cierre_cancelar"),
        )
        self.bot.send_message(message.chat.id, "⚠️ *¿Ejecutar el cierre de período?*\n\n_Esta acción no se puede deshacer._", parse_mode="Markdown", reply_markup=teclado)

    def _procesar_callback_cierre(self, call):
        try:
            self.bot.answer_callback_query(call.id)
            chat_id = call.message.chat.id
            msg_id = call.message.message_id

            if call.data == "cierre_cancelar":
                self.bot.edit_message_text("❌ Cierre cancelado.", chat_id, msg_id)
                return

            if call.data == "cierre_confirmar":
                self.bot.edit_message_text("⚙️ Ejecutando cierre de período en Google Sheets...", chat_id, msg_id)
                respuesta = self.agente_excel.ejecutar_cierre_periodo_manual()
                self.bot.send_message(chat_id, respuesta, parse_mode="Markdown")

                teclado = InlineKeyboardMarkup()
                teclado.row(
                    InlineKeyboardButton("✅ Sí, aplicar descuento", callback_data="cierre_descuento_si"),
                    InlineKeyboardButton("❌ No, generar reporte directo", callback_data="cierre_descuento_no"),
                )
                self.bot.send_message(
                    chat_id,
                    "¿Deseas aplicar algún **descuento** al salario calculado de este mes?",
                    parse_mode="Markdown",
                    reply_markup=teclado
                )
                return

            if call.data == "cierre_descuento_no":
                self.bot.edit_message_text("✅ Generando reporte sin descuentos...", chat_id, msg_id)
                self._generar_y_enviar_reporte(call.message, descuento=0)
                return

            if call.data == "cierre_descuento_si":
                msg = self.bot.edit_message_text(
                    "✍️ *Por favor, enviame el monto exacto a descontar.*\n"
                    "Escribí sólo números (ej: `50000`).",
                    chat_id,
                    msg_id,
                    parse_mode="Markdown"
                )
                self.bot.register_next_step_handler(msg, self._capturar_monto_descuento)
                return

        except Exception as e:
            self.bot.send_message(call.message.chat.id, f"❌ Error interno en cierre: {str(e)}")

    def _capturar_monto_descuento(self, message):
        try:
            texto_ingresado = message.text.strip().replace(".", "").replace(",", "")
            monto_descuento = float(texto_ingresado)
            self._generar_y_enviar_reporte(message, descuento=monto_descuento)
        except ValueError:
            self.bot.reply_to(
                message,
                "❌ *Error:* El monto debe ser numérico.\n"
                "Operación de reporte abortada. Podés pedir el reporte de nuevo más tarde o cerrar otro ciclo.",
                parse_mode="Markdown"
            )

    def _generar_y_enviar_reporte(self, message_obj, descuento):
        self.bot.send_message(message_obj.chat.id, "📄 Procesando datos y armando PDF...")
        ruta_pdf, msg_pdf = self.agente_excel.generar_reporte_pdf(descuento=descuento)

        if ruta_pdf:
            with open(ruta_pdf, 'rb') as f:
                self.bot.send_document(
                    message_obj.chat.id,
                    f,
                    caption=f"📊 {msg_pdf}",
                    visible_file_name=os.path.basename(ruta_pdf)
                )
        else:
            self.bot.send_message(message_obj.chat.id, msg_pdf)

    # ── Métodos del comando /reporte ──────────────────────────────────
    def _mostrar_selector_hojas(self, message, limite: int = 6):
        """Muestra un menú inline con las últimas `limite` hojas disponibles para reportar."""
        nombres = self.agente_excel.obtener_nombres_hojas(limite=limite)

        if not nombres:
            self.bot.reply_to(message, "❌ No hay períodos anteriores disponibles para generar un reporte.")
            return

        teclado = InlineKeyboardMarkup()
        for nombre in nombres:
            # Truncamos a 30 chars por límite de Telegram en callback_data (64 bytes)
            safe = nombre[:30]
            teclado.row(InlineKeyboardButton(f"📅 {nombre}", callback_data=f"reporte_hoja_{safe}"))
        teclado.row(InlineKeyboardButton("❌ Cancelar", callback_data="reporte_cancelar"))

        self.bot.reply_to(
            message,
            "📄 *¿De qué período querés el reporte?*\n"
            "_Se muestran los últimos períodos cerrados._",
            parse_mode="Markdown",
            reply_markup=teclado
        )

    def _procesar_callback_reporte(self, call):
        """Maneja toda la lógica de callbacks del comando /reporte."""
        try:
            self.bot.answer_callback_query(call.id)
            chat_id  = call.message.chat.id
            msg_id   = call.message.message_id
            data     = call.data

            # ── Cancelar ───────────────────────────────────────────────
            if data == "reporte_cancelar":
                self.bot.edit_message_text("❌ Operación cancelada.", chat_id, msg_id)
                return

            # ── Elección de hoja ─────────────────────────────────────────
            if data.startswith("reporte_hoja_"):
                nombre_hoja = data[len("reporte_hoja_"):]
                # Guardamos la hoja elegida en el caché persistente
                EstadoGestor.set(f"reporte_{chat_id}", nombre_hoja)

                teclado = InlineKeyboardMarkup()
                teclado.row(
                    InlineKeyboardButton("✅ Sí, aplicar descuento",    callback_data="reporte_desc_si"),
                    InlineKeyboardButton("❌ No, reporte directo",       callback_data="reporte_desc_no"),
                )
                self.bot.edit_message_text(
                    f"📅 Período seleccionado: *{nombre_hoja}*\n\n"
                    f"¿Deseas aplicar algún *descuento* al salario calculado?",
                    chat_id, msg_id,
                    parse_mode="Markdown",
                    reply_markup=teclado
                )
                return

            # ── Sin descuento ─────────────────────────────────────────
            if data == "reporte_desc_no":
                nombre_hoja = EstadoGestor.pop(f"reporte_{chat_id}")
                if not nombre_hoja:
                    self.bot.edit_message_text("❌ Sesión expirada. Ejecutá /reporte de nuevo.", chat_id, msg_id)
                    return
                self.bot.edit_message_text("✅ Generando reporte sin descuentos...", chat_id, msg_id)
                self._generar_y_enviar_reporte_por_hoja(call.message, nombre_hoja, descuento=0)
                return

            # ── Con descuento ─────────────────────────────────────────
            if data == "reporte_desc_si":
                msg = self.bot.edit_message_text(
                    "✍️ *Ingresá el monto exacto a descontar.*\n"
                    "Solo números (ej: `50000`).",
                    chat_id, msg_id,
                    parse_mode="Markdown"
                )
                self.bot.register_next_step_handler(msg, self._capturar_descuento_reporte)
                return

        except Exception as e:
            self.bot.send_message(call.message.chat.id, f"❌ Error en /reporte: {str(e)}")

    def _capturar_descuento_reporte(self, message):
        """Captura el monto de descuento ingresado y genera el PDF."""
        try:
            chat_id = message.chat.id
            nombre_hoja = EstadoGestor.pop(f"reporte_{chat_id}")
            if not nombre_hoja:
                self.bot.reply_to(message, "❌ Sesión expirada. Ejecutá /reporte de nuevo.")
                return
            monto = float(message.text.strip().replace(".", "").replace(",", ""))
            self._generar_y_enviar_reporte_por_hoja(message, nombre_hoja, descuento=monto)
        except ValueError:
            self.bot.reply_to(
                message,
                "❌ El monto debe ser numérico. Operación cancelada.\n"
                "Ejecutá /reporte para intentar de nuevo."
            )

    def _generar_y_enviar_reporte_por_hoja(self, message_obj, nombre_hoja: str, descuento: float):
        """Genera y envía el PDF para una hoja específica por nombre."""
        self.bot.send_message(message_obj.chat.id, "📄 Procesando datos y armando PDF...")
        ruta_pdf, msg_pdf = self.agente_excel.generar_reporte_pdf(
            nombre_hoja=nombre_hoja,
            descuento=descuento
        )
        if ruta_pdf:
            with open(ruta_pdf, 'rb') as f:
                self.bot.send_document(
                    message_obj.chat.id,
                    f,
                    caption=f"📊 {msg_pdf}",
                    visible_file_name=os.path.basename(ruta_pdf)
                )
        else:
            self.bot.send_message(message_obj.chat.id, msg_pdf)

    def _capturar_frase_aviso_secuencial(self, message):
        if not message.text or message.text.startswith('/'):
            self.bot.reply_to(message, "❌ Operación cancelada. No enviaste una frase válida.")
            return
        self._procesar_frase_aviso(message, message.text)

    def _procesar_frase_aviso(self, message, frase: str):
        msg_espera = self.bot.send_message(message.chat.id, "🧠 Analizando frase con Gemini...")
        datos_ia = self.agente_excel.interpretar_frase_con_ia(frase)

        if "error" in datos_ia:
            self.bot.edit_message_text(f"❌ {datos_ia['error']}", message.chat.id, msg_espera.message_id)
            return

        EstadoGestor.set(message.chat.id, datos_ia)

        teclado = InlineKeyboardMarkup()
        teclado.row(
            InlineKeyboardButton("✅ Guardar Aviso", callback_data="aviso_confirmar"),
            InlineKeyboardButton("❌ Cancelar",       callback_data="aviso_cancelar")
        )

        tarjeta_previsualizacion = (
            f"📋 *Previsualización del Aviso:*\n"
            f"━━━━━━━━━━━━━━━━━━━━━\n"
            f"📌 *Título:* {datos_ia['titulo']}\n"
            f"📅 *Fecha:* {datos_ia['fecha']}\n"
            f"⏰ *Hora:* {datos_ia['hora']}\n"
            f"━━━━━━━━━━━━━━━━━━━━━\n"
            f"¿Los datos son correctos?"
        )

        self.bot.edit_message_text(
            tarjeta_previsualizacion,
            message.chat.id,
            msg_espera.message_id,
            parse_mode="Markdown",
            reply_markup=teclado
        )

    def _procesar_callback_aviso(self, call):
        try:
            self.bot.answer_callback_query(call.id)
            chat_id = call.message.chat.id

            if call.data == "aviso_cancelar":
                EstadoGestor.pop(chat_id)
                self.bot.edit_message_text("❌ Registro de aviso cancelado.", chat_id, call.message.message_id)
                return

            datos_evento = EstadoGestor.get(chat_id)

            if not datos_evento:
                self.bot.edit_message_text("❌ Error: Expiró la sesión del aviso. Por favor, intentá de nuevo.", chat_id, call.message.message_id)
                return

            self.bot.edit_message_text("💾 Escribiendo en la base de datos de Google Sheets...", chat_id, call.message.message_id)
            resultado_escritura = self.agente_excel.guardar_aviso_calendar(datos_evento)
            EstadoGestor.pop(chat_id)
            self.bot.edit_message_text(resultado_escritura, chat_id, call.message.message_id, parse_mode="Markdown")

        except Exception as e:
            self.bot.send_message(call.message.chat.id, f"❌ Error al procesar confirmación: {str(e)}")

    def _cmd_avisos(self, message):
        """Muestra el panel interactivo con la lista de recordatorios y botones de borrado."""
        user = message.from_user
        guardar_log(f"[/avisos] Panel de gestión solicitado por ID: {user.id}")
        try:
            lista_avisos = self.agente_excel.obtener_lista_avisos_calendar()

            if not lista_avisos:
                self.bot.reply_to(message, "📭 No tenés ningún aviso programado en este momento.")
                return

            texto = "📋 *TUS RECORDATORIOS ACTIVOS*\n━━━━━━━━━━━━━━━━━━━━━\n"
            teclado = InlineKeyboardMarkup()
            botones_fila = []

            for idx, aviso in enumerate(lista_avisos):
                texto += f"*{idx + 1}.* ⏳ *{aviso['titulo']}*\n    📅 {aviso['fecha_evento']} hs.\n\n"

                btn = InlineKeyboardButton(f"❌ Borrar {idx + 1}", callback_data=f"borrar_{idx}")
                botones_fila.append(btn)

                if len(botones_fila) == 2:
                    teclado.row(*botones_fila)
                    botones_fila = []

            if botones_fila:
                teclado.row(*botones_fila)

            texto += "━━━━━━━━━━━━━━━━━━━━━\n_¿Querés eliminar alguno? Tocá el botón correspondiente._"
            self.bot.reply_to(message, texto, parse_mode="Markdown", reply_markup=teclado)

        except telebot.apihelper.ApiTelegramException as tel_e:
            guardar_log(f"⚠️ Error de red/API en Telegram: {str(tel_e)}")
            self.bot.reply_to(message, "⚠️ No pude enviarte la lista por un error de conexión con Telegram.")
        except Exception as e:
            guardar_log(f"❌ Error en _cmd_avisos: {str(e)}")
            self.bot.reply_to(message, f"❌ Error al cargar el panel de avisos: {str(e)}")

    def _procesar_callback_borrar_aviso(self, call):
        """Procesa la baja física del aviso y redibuja la lista en tiempo real."""
        try:
            self.bot.answer_callback_query(call.id)
            chat_id = call.message.chat.id
            msg_id = call.message.message_id

            indice = int(call.data.split("_")[1])
            lista_avisos_actual = self.agente_excel.obtener_lista_avisos_calendar()
            
            if 0 <= indice < len(lista_avisos_actual):
                evento_a_borrar = lista_avisos_actual[indice]
                exito = self.agente_excel.eliminar_aviso_calendar(evento_a_borrar["id"])
                
                if exito:
                    self.bot.send_message(chat_id, f"🗑️ El aviso *'{evento_a_borrar['titulo']}'* fue eliminado correctamente.", parse_mode="Markdown")
                else:
                    self.bot.send_message(chat_id, "❌ Hubo un error al eliminar el evento de Calendar.")
            else:
                self.bot.send_message(chat_id, "❌ El aviso seleccionado ya no existe.")

            # RE-RENDERIZADO: Volvemos a leer y a actualizar la misma tarjeta visual
            lista_avisos = self.agente_excel.obtener_lista_avisos_calendar()
            if not lista_avisos:
                self.bot.edit_message_text("📭 No te quedan más avisos programados.", chat_id, msg_id)
                return

            texto = "📋 *TUS RECORDATORIOS ACTIVOS*\n━━━━━━━━━━━━━━━━━━━━━\n"
            teclado = InlineKeyboardMarkup()
            botones_fila = []

            for idx, aviso in enumerate(lista_avisos):
                texto += f"*{idx + 1}.* ⏳ *{aviso['titulo']}*\n    📅 {aviso['fecha_evento']} hs.\n\n"
                btn = InlineKeyboardButton(f"❌ Borrar {idx + 1}", callback_data=f"borrar_{idx}")
                botones_fila.append(btn)
                if len(botones_fila) == 2:
                    teclado.row(*botones_fila)
                    botones_fila = []
            if botones_fila:
                teclado.row(*botones_fila)

            texto += "━━━━━━━━━━━━━━━━━━━━━\n_¿Querés eliminar alguno? Tocá el botón correspondiente._"
            self.bot.edit_message_text(texto, chat_id, msg_id, parse_mode="Markdown", reply_markup=teclado)

        except Exception as e:
            self.bot.send_message(call.message.chat.id, f"❌ Error al procesar la baja del aviso: {str(e)}")
