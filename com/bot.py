import telebot
import os
import pytz
from dotenv import load_dotenv
from logic.logic import AgenteAutonomoHoras
from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton, BotCommand
from datetime import datetime

tz_py = pytz.timezone('America/Buenos_Aires')
load_dotenv(dotenv_path="/home/kevin11000/.env")

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
        # Almacena los JSON de la IA indexados por el chat_id del usuario
        self.avisos_pendientes = {}

        self.agente_excel = AgenteAutonomoHoras(spreadsheet_id=self.sheet_id)
        self._registrar_manejadores()

    def _guardar_log(self, mensaje):
        """
        Registra un mensaje en el archivo de log del sistema.

        Agrega cada entrada con timestamp al archivo gen_log.txt.
        Si el archivo no existe, lo crea automáticamente.

        Args:
            mensaje (str): Texto a registrar en el log.

        Raises:
            OSError: Si no hay permisos de escritura en el directorio destino.

        Example:
            self._guardar_log("Proceso iniciado correctamente")
            # Escribe: [2026-06-15 10:32:45] Proceso iniciado correctamente
        """
        timestamp = datetime.now(tz_py).strftime("%Y-%m-%d %H:%M:%S")
        path = os.path.join("/home/kevin11000/mysite", "gen_log.txt")
        otpt = f"[{timestamp}] {mensaje}\n"
        with open(path, "a", encoding="utf-8") as f:
            f.write(otpt)
        print(otpt.strip())

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
        self._guardar_log(alerta)
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
        # ── Comando AVISOS ────────────────────────────────────────────────────
        @self.bot.message_handler(commands=['avisos'])
        def comando_avisos(message):
            if not self._es_autorizado(message.from_user.id):
                self._rechazar(message)
            return
            self._cmd_avisos(message)

    def _registrar_comandos_menu(self):
        """Sincroniza el menú '/' de Telegram con los comandos del bot."""
        comandos = [
            BotCommand("marcar", "Registra hora de marcación."),
            BotCommand("aviso", "Agendar un hito o recordatorio con IA."),
            BotCommand("avisos",  "Ver lista de avisos activos."),
            BotCommand("cierre", "Ejecutar cierre de período de marcaciones."),
            BotCommand("start",  "Actualizar menú de comandos"),
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
                "▶️ /marcar — Registrar entrada o salida\n"
                "✍️ /aviso  — Agendar recordatorios con lenguaje natural\n"
                "🔒 /cierre — Ejecutar cierre de período\n"
                "🔄 /start  — Reestablecer este menú\n"
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

            # FLUJO 1: Confirmación de cierre
            if call.data == "cierre_confirmar":
                self.bot.edit_message_text("⚙️ Ejecutando cierre de período en Google Sheets...", chat_id, msg_id)
                respuesta = self.agente_excel.ejecutar_cierre_periodo_manual()

                # Enviamos el resultado del cierre
                self.bot.send_message(chat_id, respuesta, parse_mode="Markdown")

                # Desplegamos la pregunta sobre los descuentos
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

            # FLUJO 2: El usuario indicó que NO hay descuento
            if call.data == "cierre_descuento_no":
                self.bot.edit_message_text("✅ Generando reporte sin descuentos...", chat_id, msg_id)
                self._generar_y_enviar_reporte(call.message, descuento=0)
                return

            # FLUJO 3: El usuario indicó que SÍ hay descuento
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

    # ─────────────────────────────────────────────────────────────────────────
    # NUEVOS MÉTODOS AUXILIARES PARA EL REPORTE
    # ─────────────────────────────────────────────────────────────────────────

    def _capturar_monto_descuento(self, message):
        """Atrapa el texto del usuario y valida que sea un número para el descuento."""
        try:
            texto_ingresado = message.text.strip().replace(".", "").replace(",", "")
            monto_descuento = float(texto_ingresado)

            # Si es exitoso, procedemos a generar el reporte
            self._generar_y_enviar_reporte(message, descuento=monto_descuento)
        except ValueError:
            self.bot.reply_to(
                message,
                "❌ *Error:* El monto debe ser numérico.\n"
                "Operación de reporte abortada. Podés pedir el reporte de nuevo más tarde o cerrar otro ciclo.",
                parse_mode="Markdown"
            )

    def _generar_y_enviar_reporte(self, message_obj, descuento):
        """Se encarga de pedirle el PDF a la lógica y enviarlo por Telegram."""
        self.bot.send_message(message_obj.chat.id, "📄 Procesando datos y armando PDF...")

        # Pasamos el descuento a la función que modificamos en logic.py
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


    # ─────────────────────────────────────────────────────────────────────────
    # 🆕 MÉTODOS DE LA FASE 3: MANEJO DEL FLUJO DE AVISOS INTERACTIVOS
    # ─────────────────────────────────────────────────────────────────────────

    def _capturar_frase_aviso_secuencial(self, message):
        """Captura la frase si el usuario optó por el flujo interactivo sin argumentos."""
        if not message.text or message.text.startswith('/'):
            self.bot.reply_to(message, "❌ Operación cancelada. No enviaste una frase válida.")
            return
        self._procesar_frase_aviso(message, message.text)

    def _procesar_frase_aviso(self, message, frase: str):
        """Envía la frase a la IA y despliega la tarjeta de confirmación."""
        msg_espera = self.bot.send_message(message.chat.id, "🧠 Analizando frase con Gemini...")

        # Consultamos a la lógica construida en la Fase 2
        datos_ia = self.agente_excel.interpretar_frase_con_ia(frase)

        if "error" in datos_ia:
            self.bot.edit_message_text(f"❌ {datos_ia['error']}", message.chat.id, msg_espera.message_id)
            return

        # Almacenamos el JSON resultante en la caché usando el chat_id como llave
        self.avisos_pendientes[message.chat.id] = datos_ia

        # Construimos el teclado interactivo
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
        """Maneja la pulsación de los botones Guardar o Cancelar aviso."""
        try:
            self.bot.answer_callback_query(call.id)
            chat_id = call.message.chat.id

            if call.data == "aviso_cancelar":
                # Limpiamos la caché y editamos
                self.avisos_pendientes.pop(chat_id, None)
                self.bot.edit_message_text("❌ Registro de aviso cancelado.", chat_id, call.message.message_id)
                return

            # Si es confirmar, extraemos los datos guardados en caché
            datos_evento = self.avisos_pendientes.get(chat_id)

            if not datos_evento:
                self.bot.edit_message_text("❌ Error: Expiró la sesión del aviso. Por favor, intentá de nuevo.", chat_id, call.message.message_id)
                return

            self.bot.edit_message_text("💾 Escribiendo en la base de datos de Google Sheets...", chat_id, call.message.message_id)

            # ── CONEXIÓN CON PLANILLA (Se consolidará en la Fase 4) ───────────
            # Llamamos a un método (que crearemos a continuación en logic.py)
            resultado_escritura = self.agente_excel.guardar_nuevo_aviso_en_sheets(datos_evento)

            # Limpiamos la caché tras la operación
            self.avisos_pendientes.pop(chat_id, None)

            # Mostramos el feedback final
            self.bot.edit_message_text(resultado_escritura, chat_id, call.message.message_id, parse_mode="Markdown")

        except Exception as e:
            self.bot.send_message(call.message.chat.id, f"❌ Error al procesar confirmación: {str(e)}")

    def _cmd_avisos(self, message):
        """Envía al chat la lista de avisos activos registrados en Sheets."""
        user = message.from_user
        self._guardar_log(
            f"[/avisos] Solicitado por ID: {user.id} | @{user.username or 'sin username'}"
        )
        try:
            respuesta = self.agente_excel.verificar_avisos_activos()

            if not respuesta or not respuesta.strip():
                self._guardar_log(f"[/avisos] Sin avisos activos para ID: {user.id}")
                self.bot.reply_to(message, "📭 No hay avisos activos en este momento.")
                return

            self._guardar_log(f"[/avisos] Lista enviada correctamente a ID: {user.id}")
            self.bot.reply_to(message, respuesta, parse_mode="Markdown")

        except Exception as e:
            self._guardar_log(f"[/avisos] ERROR — {type(e).__name__}: {str(e)} | Usuario ID: {user.id}")
            self.bot.reply_to(message, f"❌ Error al obtener avisos: {type(e).__name__} - {str(e)}")