from __future__ import annotations

from typing import Any
from telebot import TeleBot
from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton
import shlex

from com.core.errors import safe_handler
from com.core.security import auth_required
from logger_config import setup_logger
from logic.financiero import (
    create_debt,
    get_active_debts,
    register_payment,
    execute_monthly_closing,
    simulate_project,
    approve_project,
    proyectar_cola_deudas,
    simular_impacto_abono,
    obtener_cronograma_vencimientos,
)
from com.core.states import set_state, get_state, clear_state
from com.utils.validators import parse_monto, parse_cuotas, validate_fecha
from app_queue.worker import enqueue
from logic.logic import get_now_py

logger = setup_logger("deudas_handler")


def register_deudas_handlers(bot: TeleBot, gamma_app: Any) -> Any:

    @bot.message_handler(commands=["nueva_deuda"])
    @auth_required(bot)
    @safe_handler(bot, logger)
    def handle_nueva_deuda(message):
        parts = shlex.split(message.text)
        if len(parts) >= 6:
            try:
                entity = parts[1]
                concept = parts[2]
                amount = parse_monto(parts[3])
                quotas = parse_cuotas(parts[4])
                first_due = validate_fecha(parts[5])
                dia_venc = int(parts[6]) if len(parts) > 6 else 0
                debt_id = create_debt(
                    entity,
                    concept,
                    amount,
                    quotas,
                    first_due,
                    dia_vencimiento=dia_venc,
                )
                bot.reply_to(
                    message,
                    f"✅ Deuda creada con ID: `{debt_id}`",
                    parse_mode="Markdown",
                )
            except Exception as e:
                bot.reply_to(
                    message,
                    f"❌ Error al crear deuda: {e}\n"
                    "Uso: `/nueva_deuda <Entidad> <Concepto> <Monto> <Cuotas> <DD/MM/YYYY> [Dia_Venc]`",
                    parse_mode="Markdown",
                )
            return

        set_state(message.from_user.id, "NUEVA_DEUDA_P1", {})
        bot.reply_to(message, "🏦 ¿Cómo se llama la entidad o acreedor?")

    @bot.message_handler(
        func=lambda msg: bool(get_state(msg.from_user.id))
        and (get_state(msg.from_user.id) or {}).get("estado") == "NUEVA_DEUDA_P1"
    )
    @auth_required(bot)
    @safe_handler(bot, logger)
    def handle_nueva_deuda_p1(message):
        state = get_state(message.from_user.id)
        if not state:
            return
        datos = state["datos"]
        datos["entidad"] = message.text.strip()
        set_state(message.from_user.id, "NUEVA_DEUDA_P2", datos)
        bot.reply_to(message, "📝 ¿Cuál es el concepto o nombre de la deuda?")

    @bot.message_handler(
        func=lambda msg: bool(get_state(msg.from_user.id))
        and (get_state(msg.from_user.id) or {}).get("estado") == "NUEVA_DEUDA_P2"
    )
    @auth_required(bot)
    @safe_handler(bot, logger)
    def handle_nueva_deuda_p2(message):
        state = get_state(message.from_user.id)
        if not state:
            return
        datos = state["datos"]
        datos["concepto"] = message.text.strip()
        set_state(message.from_user.id, "NUEVA_DEUDA_P3", datos)
        bot.reply_to(message, "💵 ¿Monto total de la deuda en Gs.?")

    @bot.message_handler(
        func=lambda msg: bool(get_state(msg.from_user.id))
        and (get_state(msg.from_user.id) or {}).get("estado") == "NUEVA_DEUDA_P3"
    )
    @auth_required(bot)
    @safe_handler(bot, logger)
    def handle_nueva_deuda_p3(message):
        try:
            monto = parse_monto(message.text)
        except ValueError:
            bot.reply_to(message, "Por favor ingresa un monto numérico válido.")
            return
        state = get_state(message.from_user.id)
        if not state:
            return
        datos = state["datos"]
        datos["monto"] = monto
        set_state(message.from_user.id, "NUEVA_DEUDA_P4", datos)
        bot.reply_to(message, "📅 ¿A cuántas cuotas?")

    @bot.message_handler(
        func=lambda msg: bool(get_state(msg.from_user.id))
        and (get_state(msg.from_user.id) or {}).get("estado") == "NUEVA_DEUDA_P4"
    )
    @auth_required(bot)
    @safe_handler(bot, logger)
    def handle_nueva_deuda_p4(message):
        try:
            cuotas = parse_cuotas(message.text)
        except ValueError:
            bot.reply_to(message, "Por favor ingresa un número de cuotas válido.")
            return
        state = get_state(message.from_user.id)
        if not state:
            return
        datos = state["datos"]
        datos["cuotas"] = cuotas
        set_state(message.from_user.id, "NUEVA_DEUDA_P5", datos)
        bot.reply_to(message, "📆 ¿Fecha del primer vencimiento? (DD/MM/YYYY)")

    @bot.message_handler(
        func=lambda msg: bool(get_state(msg.from_user.id))
        and (get_state(msg.from_user.id) or {}).get("estado") == "NUEVA_DEUDA_P5"
    )
    @auth_required(bot)
    @safe_handler(bot, logger)
    def handle_nueva_deuda_p5(message):
        try:
            fecha_val = validate_fecha(message.text)
        except ValueError:
            bot.reply_to(
                message, "Por favor ingresa una fecha válida en formato DD/MM/YYYY."
            )
            return
        state = get_state(message.from_user.id)
        if not state:
            return
        datos = state["datos"]
        datos["fecha"] = fecha_val

        set_state(message.from_user.id, "NUEVA_DEUDA_CONFIRMAR", datos)

        resumen = (
            f"📋 *Resumen de la deuda:*\n"
            f"🏦 Entidad: {datos['entidad']}\n"
            f"📝 Concepto: {datos['concepto']}\n"
            f"💵 Monto: Gs. {datos['monto']:,}\n"
            f"📅 Cuotas: {datos['cuotas']}\n"
            f"📆 Primer vencimiento: {datos['fecha']}\n\n"
            f"¿Confirmar?"
        ).replace(",", ".")

        markup = InlineKeyboardMarkup()
        markup.add(
            InlineKeyboardButton("✅ Confirmar", callback_data="confirmar_deuda:si"),
            InlineKeyboardButton("❌ Cancelar", callback_data="confirmar_deuda:no"),
        )

        bot.reply_to(message, resumen, parse_mode="Markdown", reply_markup=markup)

    @bot.callback_query_handler(
        func=lambda call: call.data.startswith("confirmar_deuda:")
    )
    @auth_required(bot)
    @safe_handler(bot, logger)
    def callback_confirmar_deuda(call):
        state = get_state(call.from_user.id)
        if not state or state.get("estado") != "NUEVA_DEUDA_CONFIRMAR":
            bot.answer_callback_query(call.id, "Estado no válido o expirado.")
            return

        action = call.data.split(":")[1]
        if action == "si":
            datos = state["datos"]
            enqueue(
                call.message.chat.id,
                "create_debt",
                {
                    "entidad": datos["entidad"],
                    "concepto": datos["concepto"],
                    "monto": datos["monto"],
                    "cuotas": datos["cuotas"],
                    "fecha": datos["fecha"],
                },
            )
            bot.edit_message_text(
                chat_id=call.message.chat.id,
                message_id=call.message.message_id,
                text="⏳ Registrando deuda... te avisaré cuando esté listo.",
            )
        else:
            bot.edit_message_text(
                chat_id=call.message.chat.id,
                message_id=call.message.message_id,
                text="❌ Registro de deuda cancelado.",
            )
        clear_state(call.from_user.id)

    @bot.message_handler(commands=["estrategia", "cola_deudas"])
    @auth_required(bot)
    @safe_handler(bot, logger)
    def handle_estrategia(message):
        parts = shlex.split(message.text)
        criterio = "prioridad"
        if len(parts) > 1 and parts[1] in ["saldo", "prioridad"]:
            criterio = parts[1]

        res = proyectar_cola_deudas(criterio)
        margen = res["margen_ataque"]
        proy = res["proyeccion"]

        if not proy:
            bot.reply_to(message, "No hay deudas en la cola.")
            return

        response = f"🎯 *Estrategia de Pago Bola de Nieve* ({criterio})\n"
        response += f"💰 *Margen de Ataque Base:* Gs. {margen:,}\n\n".replace(",", ".")

        for i, p in enumerate(proy, 1):
            estado = "🔴 VENCIDA" if p["vencida"] else "🟢 Al día"
            response += (
                f"{i}. *{p['nombre']}* (ID: `{p.get('id', 'N/A')}`)\n"
                f"   Estado: {estado}\n"
                f"   Pago mensual proyectado: Gs. {p['pago_mensual_proyectado']:,}\n".replace(
                    ",", "."
                )
                + f"   Meses estimados: {p['meses_estimados']} (Fin: {p['fecha_fin']})\n\n"
            )
        response += "_Nota: Proyección estimada sin intereses. Los plazos reales pueden variar._"
        bot.reply_to(message, response, parse_mode="Markdown")

    @bot.message_handler(commands=["foco"])
    @auth_required(bot)
    @safe_handler(bot, logger)
    def handle_foco(message):
        res = proyectar_cola_deudas("prioridad")
        proy = res["proyeccion"]
        if not proy:
            bot.reply_to(message, "No hay deudas en foco.")
            return
        foco = proy[0]
        bot.reply_to(
            message,
            f"🎯 *Foco Actual:* {foco['nombre']} (ID: `{foco.get('id', 'N/A')}`)\nPago mensual proyectado: Gs. {foco['pago_mensual_proyectado']:,}\nMeses estimados: {foco['meses_estimados']}".replace(
                ",", "."
            ),
            parse_mode="Markdown",
        )

    @bot.message_handler(commands=["evaluar_abono"])
    @auth_required(bot)
    @safe_handler(bot, logger)
    def handle_evaluar_abono(message):
        parts = shlex.split(message.text)
        if len(parts) >= 3:
            monto = int(parts[1])
            debt_id = parts[2]

            res = simular_impacto_abono(monto, debt_id)
            if "error" in res:
                bot.reply_to(message, f"Error: {res['error']}")
                return

            response = (
                f"💡 *Simulación de Abono Extra*\n"
                f"Monto Extra: Gs. {monto:,}\n".replace(",", ".")
                + f"Saldo Anterior: Gs. {res['saldo_anterior']:,}\n".replace(",", ".")
                + f"Saldo Nuevo: Gs. {res['saldo_nuevo']:,}\n".replace(",", ".")
                + f"Meses Ahorrados: {res['meses_ahorrados']}\n"
                f"Meses Restantes (Nueva Proyección): {res['meses_restantes']}"
            )
            bot.reply_to(message, response, parse_mode="Markdown")
            return

        debts = get_active_debts()
        if not debts:
            bot.reply_to(message, "No hay deudas activas para evaluar.")
            return

        markup = InlineKeyboardMarkup()
        for d in debts:
            debt_id = d.get("ID_Obligacion")
            nombre = d.get("Nombre", "N/A")
            markup.add(
                InlineKeyboardButton(
                    nombre, callback_data=f"eval_abono_deuda:{debt_id}"
                )
            )

        bot.reply_to(message, "Selecciona la deuda a simular:", reply_markup=markup)

    @bot.callback_query_handler(
        func=lambda call: call.data.startswith("eval_abono_deuda:")
    )
    @auth_required(bot)
    @safe_handler(bot, logger)
    def callback_evaluar_abono_deuda(call):
        debt_id = call.data.split(":")[1]
        set_state(call.from_user.id, "EVALUAR_ABONO_MONTO", {"debt_id": debt_id})
        bot.edit_message_text(
            chat_id=call.message.chat.id,
            message_id=call.message.message_id,
            text="💰 ¿Qué monto extra deseas simular (Gs.)?",
        )

    @bot.message_handler(
        func=lambda msg: bool(get_state(msg.from_user.id))
        and (get_state(msg.from_user.id) or {}).get("estado") == "EVALUAR_ABONO_MONTO"
    )
    @auth_required(bot)
    @safe_handler(bot, logger)
    def handle_evaluar_abono_monto(message):
        try:
            monto = parse_monto(message.text)
        except ValueError:
            bot.reply_to(message, "Por favor ingresa un monto numérico válido.")
            return

        state = get_state(message.from_user.id)
        if not state:
            return
        debt_id = state["datos"]["debt_id"]
        clear_state(message.from_user.id)

        res = simular_impacto_abono(monto, debt_id)
        if "error" in res:
            bot.reply_to(message, f"Error: {res['error']}")
            return

        response = (
            f"💡 *Simulación de Abono Extra*\n"
            f"Monto Extra: Gs. {monto:,}\n".replace(",", ".")
            + f"Saldo Anterior: Gs. {res['saldo_anterior']:,}\n".replace(",", ".")
            + f"Saldo Nuevo: Gs. {res['saldo_nuevo']:,}\n".replace(",", ".")
            + f"Meses Ahorrados: {res['meses_ahorrados']}\n"
            f"Meses Restantes (Nueva Proyección): {res['meses_restantes']}"
        )
        bot.reply_to(message, response, parse_mode="Markdown")

    @bot.message_handler(commands=["vencimientos"])
    @auth_required(bot)
    @safe_handler(bot, logger)
    def handle_vencimientos(message):
        res = obtener_cronograma_vencimientos()
        vencimientos = res["vencimientos"]
        if not vencimientos:
            bot.reply_to(message, "No hay vencimientos programados.")
            return

        response = f"📅 *Vencimientos del Mes ({res['mes_actual']})*\n\n"
        for v in vencimientos:
            response += (
                f"Día {v['dia_vencimiento']}: *{v['nombre']}* (ID: `{v['id']}`)\n"
                f"   Cuota: Gs. {v['cuota']:,} | Saldo: Gs. {v['saldo']:,}\n\n".replace(
                    ",", "."
                )
            )
        bot.reply_to(message, response, parse_mode="Markdown")

    @bot.message_handler(commands=["deudas"])
    @auth_required(bot)
    @safe_handler(bot, logger)
    def handle_deudas(message):
        def _safe_int(v):
            try:
                if isinstance(v, str):
                    v = v.strip()
                if not v or v == "N/A":
                    return 0
                return int(float(v))
            except Exception:
                return 0

        parts = shlex.split(message.text)
        debt_id = parts[1] if len(parts) > 1 else None
        debts = get_active_debts(debt_id)
        if not debts:
            bot.reply_to(message, "No hay deudas activas.")
            return
        response = "📋 *Deudas activas:*\n"
        for d in debts:
            nombre = d.get("Nombre", "N/A")
            monto = d.get("Monto_Inicial", 0)
            cuota = d.get("Cuota_Referencia_Gs", "N/A")
            saldo = d.get("Saldo_Actual", 0)
            response += (
                f"─────────────────\n"
                f"🆔 `{d.get('ID_Obligacion', 'N/A')}`\n"
                f"📝 {nombre}\n"
                f"💰 Monto: Gs. {_safe_int(monto):,}\n".replace(",", ".")
                + f"📊 Cuota Ref: Gs. {_safe_int(cuota):,}\n".replace(",", ".")
                + f"💳 Saldo: Gs. {_safe_int(saldo):,}\n".replace(",", ".")
            )
        bot.reply_to(message, response, parse_mode="Markdown")

    @bot.message_handler(commands=["abonar"])
    @auth_required(bot)
    @safe_handler(bot, logger)
    def handle_abonar(message):
        parts = shlex.split(message.text)
        if len(parts) >= 3:
            try:
                debt_id = parts[1]
                amount = parse_monto(parts[2])
                date = (
                    validate_fecha(parts[3])
                    if len(parts) >= 4
                    else get_now_py().strftime("%d/%m/%Y")
                )
                tasa_iva = parts[4] if len(parts) >= 5 else "Exento"
                register_payment(debt_id, amount, date, tasa_iva=tasa_iva)
                monto_fmt = "{:,}".format(amount).replace(",", ".")
                bot.reply_to(
                    message,
                    f"✅ Abono de Gs. {monto_fmt} registrado para la deuda `{debt_id}`.",
                    parse_mode="Markdown",
                )
            except Exception as e:
                bot.reply_to(
                    message,
                    f"❌ Error al registrar abono: {e}\n"
                    "Uso: `/abonar <ID_Deuda> <Monto> [Fecha: DD/MM/YYYY] [Tasa_IVA]`",
                    parse_mode="Markdown",
                )
            return

        debts = get_active_debts()
        if not debts:
            bot.reply_to(message, "No hay deudas activas para abonar.")
            return

        markup = InlineKeyboardMarkup()
        for d in debts:
            debt_id = d.get("ID_Obligacion")
            nombre = d.get("Nombre", "N/A")
            markup.add(
                InlineKeyboardButton(nombre, callback_data=f"abonar_deuda:{debt_id}")
            )

        bot.reply_to(message, "Selecciona la deuda a abonar:", reply_markup=markup)

    @bot.callback_query_handler(func=lambda call: call.data.startswith("abonar_deuda:"))
    @auth_required(bot)
    @safe_handler(bot, logger)
    def callback_abonar_deuda(call):
        debt_id = call.data.split(":")[1]
        set_state(call.from_user.id, "ABONAR_P2", {"debt_id": debt_id})
        bot.edit_message_text(
            chat_id=call.message.chat.id,
            message_id=call.message.message_id,
            text="💵 ¿Cuánto abonas (Gs.)?",
        )

    @bot.message_handler(
        func=lambda msg: bool(get_state(msg.from_user.id))
        and (get_state(msg.from_user.id) or {}).get("estado") == "ABONAR_P2"
    )
    @auth_required(bot)
    @safe_handler(bot, logger)
    def handle_abonar_p2(message):
        try:
            monto = parse_monto(message.text)
        except ValueError:
            bot.reply_to(message, "Por favor ingresa un monto numérico válido.")
            return

        state = get_state(message.from_user.id)
        if not state:
            return
        datos = state["datos"]
        datos["amount"] = monto
        set_state(message.from_user.id, "ABONAR_P3", datos)

        markup = InlineKeyboardMarkup()
        markup.add(
            InlineKeyboardButton("10%", callback_data="abonar_iva:10%"),
            InlineKeyboardButton("5%", callback_data="abonar_iva:5%"),
            InlineKeyboardButton("Exento", callback_data="abonar_iva:Exento"),
        )

        bot.reply_to(message, "📅 Tasa de IVA", reply_markup=markup)

    @bot.callback_query_handler(func=lambda call: call.data.startswith("abonar_iva:"))
    @auth_required(bot)
    @safe_handler(bot, logger)
    def callback_abonar_iva(call):
        state = get_state(call.from_user.id)
        if not state or state.get("estado") != "ABONAR_P3":
            bot.answer_callback_query(call.id, "Estado no válido o expirado.")
            return

        tasa_iva = call.data.split(":")[1]
        datos = state["datos"]

        date_today = get_now_py().strftime("%d/%m/%Y")

        enqueue(
            call.message.chat.id,
            "register_payment",
            {
                "debt_id": datos["debt_id"],
                "amount": datos["amount"],
                "date": date_today,
                "tasa_iva": tasa_iva,
            },
        )

        bot.edit_message_text(
            chat_id=call.message.chat.id,
            message_id=call.message.message_id,
            text="⏳ Registrando pago... te avisaré cuando esté listo.",
        )
        clear_state(call.from_user.id)

    @bot.message_handler(commands=["cierre_mensual"])
    @auth_required(bot)
    @safe_handler(bot, logger)
    def handle_cierre_mensual(message):
        parts = shlex.split(message.text)
        if len(parts) >= 3:
            month = int(parts[1])
            year = int(parts[2])

            drive_id = execute_monthly_closing(month, year)
            bot.reply_to(message, f"✅ Cierre mensual ejecutado. Backup ID: {drive_id}")
            return

        markup = InlineKeyboardMarkup()
        markup.row(
            InlineKeyboardButton(
                "📅 Cerrar Mes Actual", callback_data="cierre_mensual_actual"
            )
        )
        markup.row(
            InlineKeyboardButton(
                "✏️ Elegir mes manualmente", callback_data="cierre_mensual_manual"
            )
        )

        bot.reply_to(message, "⚙️ Opciones de Cierre Mensual:", reply_markup=markup)

    @bot.callback_query_handler(func=lambda call: call.data == "cierre_mensual_actual")
    @auth_required(bot)
    @safe_handler(bot, logger)
    def callback_cierre_mensual_actual(call):
        bot.answer_callback_query(call.id)
        from datetime import datetime

        now = datetime.now()
        bot.edit_message_text(
            chat_id=call.message.chat.id,
            message_id=call.message.message_id,
            text=f"⏳ Ejecutando cierre mensual para {now.month}/{now.year}, por favor espera...",
        )
        try:
            drive_id = execute_monthly_closing(now.month, now.year)
            bot.edit_message_text(
                chat_id=call.message.chat.id,
                message_id=call.message.message_id,
                text=f"✅ Cierre mensual ejecutado para {now.month}/{now.year}.\nBackup ID: `{drive_id}`",
                parse_mode="Markdown",
            )
        except Exception as e:
            bot.edit_message_text(
                chat_id=call.message.chat.id,
                message_id=call.message.message_id,
                text=f"❌ Error al ejecutar el cierre: {e}",
            )

    @bot.callback_query_handler(func=lambda call: call.data == "cierre_mensual_manual")
    @auth_required(bot)
    @safe_handler(bot, logger)
    def callback_cierre_mensual_manual(call):
        bot.answer_callback_query(call.id)
        markup = InlineKeyboardMarkup(row_width=3)
        botones = [
            InlineKeyboardButton(str(i), callback_data=f"cierre_mes:{i}")
            for i in range(1, 13)
        ]
        markup.add(*botones)

        bot.edit_message_text(
            chat_id=call.message.chat.id,
            message_id=call.message.message_id,
            text="📅 Selecciona el MES para el cierre mensual:",
            reply_markup=markup,
        )

    @bot.callback_query_handler(func=lambda call: call.data.startswith("cierre_mes:"))
    @auth_required(bot)
    @safe_handler(bot, logger)
    def callback_cierre_mes(call):
        mes = int(call.data.split(":")[1])
        set_state(call.from_user.id, "CIERRE_ANIO", {"mes": mes})

        from datetime import datetime

        current_year = datetime.now().year

        markup = InlineKeyboardMarkup()
        markup.row(
            InlineKeyboardButton(
                str(current_year - 1), callback_data=f"cierre_anio:{current_year - 1}"
            ),
            InlineKeyboardButton(
                str(current_year), callback_data=f"cierre_anio:{current_year}"
            ),
            InlineKeyboardButton(
                str(current_year + 1), callback_data=f"cierre_anio:{current_year + 1}"
            ),
        )

        bot.edit_message_text(
            chat_id=call.message.chat.id,
            message_id=call.message.message_id,
            text=f"📅 Mes seleccionado: {mes}\n\nSelecciona el AÑO:",
            reply_markup=markup,
        )

    @bot.callback_query_handler(func=lambda call: call.data.startswith("cierre_anio:"))
    @auth_required(bot)
    @safe_handler(bot, logger)
    def callback_cierre_anio(call):
        state = get_state(call.from_user.id)
        if not state or state.get("estado") != "CIERRE_ANIO":
            bot.answer_callback_query(call.id, "Estado expirado.")
            return

        mes = state["datos"]["mes"]
        anio = int(call.data.split(":")[1])
        clear_state(
            call.fromuser.id if hasattr(call, "fromuser") else call.from_user.id
        )

        bot.edit_message_text(
            chat_id=call.message.chat.id,
            message_id=call.message.message_id,
            text="⏳ Ejecutando cierre mensual, por favor espera...",
        )

        try:
            drive_id = execute_monthly_closing(mes, anio)
            bot.edit_message_text(
                chat_id=call.message.chat.id,
                message_id=call.message.message_id,
                text=f"✅ Cierre mensual ejecutado para {mes}/{anio}.\nBackup ID: `{drive_id}`",
                parse_mode="Markdown",
            )
        except Exception as e:
            bot.edit_message_text(
                chat_id=call.message.chat.id,
                message_id=call.message.message_id,
                text=f"❌ Error al ejecutar el cierre: {e}",
            )

    @bot.message_handler(commands=["simular"])
    @auth_required(bot)
    @safe_handler(bot, logger)
    def handle_simular(message):
        parts = shlex.split(message.text)
        if len(parts) >= 3:
            monto = int(parts[1])
            meses = int(parts[2])
            concept = " ".join(parts[3:]) if len(parts) > 3 else "N/A"

            msg_carga = bot.reply_to(
                message,
                "⏳ *Consultando presupuesto y calculando viabilidad...*",
                parse_mode="Markdown",
            )

            response_text = simulate_project(monto, meses, concept)
            bot.edit_message_text(
                chat_id=message.chat.id,
                message_id=msg_carga.message_id,
                text=response_text,
                parse_mode="Markdown",
            )
            return

        set_state(message.from_user.id, "SIMULAR_MONTO", {})
        bot.reply_to(
            message, "💰 ¿Cuál es el monto total del proyecto a simular (Gs.)?"
        )

    @bot.message_handler(
        func=lambda msg: bool(get_state(msg.from_user.id))
        and (get_state(msg.from_user.id) or {}).get("estado") == "SIMULAR_MONTO"
    )
    @auth_required(bot)
    @safe_handler(bot, logger)
    def handle_simular_monto(message):
        try:
            monto = parse_monto(message.text)
        except ValueError:
            bot.reply_to(message, "Por favor ingresa un monto numérico válido.")
            return

        set_state(message.from_user.id, "SIMULAR_MESES", {"monto": monto})
        bot.reply_to(
            message, "📅 ¿En cuántos meses planeas pagar o recuperar este proyecto?"
        )

    @bot.message_handler(
        func=lambda msg: bool(get_state(msg.from_user.id))
        and (get_state(msg.from_user.id) or {}).get("estado") == "SIMULAR_MESES"
    )
    @auth_required(bot)
    @safe_handler(bot, logger)
    def handle_simular_meses(message):
        try:
            meses = int(message.text.strip())
        except ValueError:
            bot.reply_to(
                message,
                "Por favor ingresa una cantidad de meses válida (número entero).",
            )
            return

        state = get_state(message.from_user.id)
        if not state:
            return
        monto = state["datos"]["monto"]
        clear_state(message.from_user.id)

        msg_carga = bot.reply_to(
            message,
            "⏳ *Consultando presupuesto y calculando viabilidad...*",
            parse_mode="Markdown",
        )

        response_text = simulate_project(monto, meses, "N/A")
        bot.edit_message_text(
            chat_id=message.chat.id,
            message_id=msg_carga.message_id,
            text=response_text,
            parse_mode="Markdown",
        )

    @bot.message_handler(commands=["aprobar_proyecto"])
    @auth_required(bot)
    @safe_handler(bot, logger)
    def handle_aprobar_proyecto(message):
        parts = shlex.split(message.text)
        if len(parts) < 2:
            bot.reply_to(message, "Uso: /aprobar_proyecto <ID_Proyecto>")
            return
        project_id = parts[1]
        approve_project(project_id)
        bot.reply_to(message, f"Proyecto {project_id} aprobado.")
