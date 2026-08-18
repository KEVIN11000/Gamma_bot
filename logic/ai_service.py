from __future__ import annotations

import json
import os
from datetime import datetime

import pytz
from google import genai
from google.genai import types

from logger_config import setup_logger

logger = setup_logger("ai_service")

tz_py = pytz.timezone("America/Buenos_Aires")


class AIService:
    @staticmethod
    def procesar_movimiento_con_ia(texto_usuario: str, tipo_movimiento: str) -> dict:
        api_key = os.getenv("GEMINI_API_KEY")
        if not api_key:
            return {"error": "Configuración de IA incompleta en el servidor."}
        ahora = datetime.now(tz_py)
        fecha_hoy_str = ahora.strftime("%d/%m")
        mes_actual = ahora.strftime("%B")
        prompt_sistema = (
            f"Eres un experto analista financiero personal.\n"
            f"Tu tarea es analizar la frase enviada y extraer los datos de un movimiento financiero.\n"
            f"El movimiento es de tipo: {tipo_movimiento.upper()}.\n"
            f"Debes devolver obligatoriamente un objeto JSON con las siguientes llaves (todas strings):\n"
            f"1. 'proveedor_cliente': Nombre de la empresa o persona involucrada.\n"
            f"2. 'nro_factura': Si no se menciona, devuelve 'S/N'.\n"
            f"3. 'neto': Monto antes de impuestos (si no se especifica IVA, "
            f"pon el total aquí también, sin puntos ni comas).\n"
            f"4. 'iva': Monto del impuesto (si no se especifica, pon '0').\n"
            f"5. 'total': Monto total del movimiento (solo números, sin puntos ni comas).\n"
            f"6. 'categoria': Categoriza en una palabra "
            f"(ej. Comida, Transporte, Honorarios, Sueldo, Ocio, Varios).\n"
            f"7. 'comprobante': Si no especifica que es virtual, pon 'No Legal' "
            f"por defecto si es Gasto, o 'Física Legal' si tiene sentido.\n"
            f"Solo devuelve el JSON, sin markdown ni explicaciones adicionales."
        )
        try:
            client = genai.Client(api_key=api_key)
            respuesta_ia = client.models.generate_content(
                model="gemini-2.5-flash",
                contents=f"Contexto del Sistema:\n{prompt_sistema}\n\nMensaje del Usuario: {texto_usuario}",
                config=types.GenerateContentConfig(
                    response_mime_type="application/json"
                ),
            )
            datos = json.loads(respuesta_ia.text)
            datos["fecha"] = fecha_hoy_str
            datos["mes"] = mes_actual
            datos["tipo_movimiento"] = tipo_movimiento.capitalize()
            logger.info(f"🤖 IA Financiera interpretó: {datos}")
            return datos
        except json.JSONDecodeError as e:
            logger.error(f"❌ Error al decodificar JSON financiero: {e}")
            return {"error": "La IA devolvió un formato ilegible."}
        except Exception as e:
            logger.error(f"❌ Error API Gemini OCR: {e}")
            return {"error": str(e)}

    @staticmethod
    def generar_insights_financieros(totales: dict, resumen_filas: str) -> str:
        api_key = os.getenv("GEMINI_API_KEY")
        if not api_key:
            return "❌ Configuración de IA incompleta en el servidor."

        prompt_sistema = (
            "Eres el 'Asesor Financiero Proactivo' de Gamma, "
            "un contador estricto y analítico.\n"
            "Tu tarea es analizar el resumen del Libro Diario de tu cliente "
            "y enviarle un mensaje corto y directo a Telegram.\n"
            "Debes:\n"
            "1. Evaluar el balance general (Ingresos vs Gastos).\n"
            "2. Identificar la categoría con mayor gasto y juzgar si es excesivo.\n"
            "3. Dar exactamente UN tip accionable de ahorro o recomendación financiera agresiva.\n"
            "Mantén un tono profesional pero muy estricto, casi como un sargento financiero.\n"
            "Usa formato Markdown compatible con Telegram "
            "(negritas *, listas -, pero NO uses encabezados # ni tablas).\n"
            "El mensaje no debe superar los 3 párrafos."
        )

        contexto = (
            f"TOTALES DEL PERÍODO:\n{json.dumps(totales, indent=2)}\n\n"
            f"RESUMEN DE MOVIMIENTOS RECIENTES:\n{resumen_filas}"
        )

        try:
            client = genai.Client(api_key=api_key)
            respuesta_ia = client.models.generate_content(
                model="gemini-2.5-flash",
                contents=f"Contexto del Sistema:\n{prompt_sistema}\n\nDatos Financieros:\n{contexto}",
            )
            logger.info("🤖 Asesor IA generó insights exitosamente.")
            return respuesta_ia.text.strip()
        except Exception as e:
            logger.error(f"❌ Error al generar insights financieros: {e}")
            return f"❌ Error de IA: {e}"

    @staticmethod
    def analizar_ticket_con_ia(
        imagen_bytes: bytes, mime_type: str = "image/jpeg"
    ) -> dict:
        api_key = os.getenv("GEMINI_API_KEY")
        mi_ruc = os.getenv("MI_RUC", "Sin RUC")
        mi_nombre = os.getenv("MI_NOMBRE_FACTURA", "Sin Nombre")
        if not api_key:
            return {"error": "Configuración de IA incompleta en el servidor."}
        ahora = datetime.now(tz_py)
        fecha_hoy_str = ahora.strftime("%d/%m")
        mes_actual = ahora.strftime("%B")
        prompt_sistema = (
            f"Eres un experto contador público y analista financiero en Paraguay.\n"
            f"Tu tarea es analizar el ticket o factura provisto en la imagen "
            f"y extraer los datos del gasto.\n"
            f"REGLA CRÍTICA PARA 'comprobante':\n"
            f"1. Si el documento dice explícitamente 'Factura Virtual' y está "
            f"a nombre de '{mi_nombre}' o RUC '{mi_ruc}', pon 'Virtual Legal'.\n"
            f"2. Si es una factura impresa o normal válida a nombre de "
            f"'{mi_nombre}' o RUC '{mi_ruc}', pon 'Física Legal'.\n"
            f"3. Si es un ticket común de supermercado/despensa que dice "
            f"'Sin Nombre', o RUC 'XXXXX', o no es factura válida, "
            f"pon 'No Legal'.\n\n"
            f"Devuelve obligatoriamente un objeto JSON con las siguientes "
            f"llaves (todas strings):\n"
            f"1. 'proveedor_cliente': Nombre de la empresa o comercio "
            f"que emite el ticket.\n"
            f"2. 'nro_factura': Número de factura si existe, sino 'S/N'.\n"
            f"3. 'neto': Monto antes del IVA (Total - IVA). "
            f"Si no hay desglose, repite el Total (solo números).\n"
            f"4. 'iva': Monto total del IVA (suma de IVA 5% e IVA 10%). "
            f"Si no hay, pon '0' (solo números).\n"
            f"5. 'total': Monto total a pagar (solo números, sin puntos ni comas).\n"
            f"6. 'categoria': Categoriza en una palabra "
            f"(ej. Supermercado, Combustible, Farmacia, Comida, Varios).\n"
            f"7. 'comprobante': Aplica la REGLA CRÍTICA estrictamente "
            f"('Virtual Legal', 'Física Legal' o 'No Legal').\n"
            f"Solo devuelve el JSON, sin markdown ni explicaciones adicionales."
        )
        try:
            client = genai.Client(api_key=api_key)
            imagen_part = types.Part.from_bytes(data=imagen_bytes, mime_type=mime_type)
            respuesta_ia = client.models.generate_content(
                model="gemini-2.5-flash",
                contents=[imagen_part, prompt_sistema],
                config=types.GenerateContentConfig(
                    response_mime_type="application/json"
                ),
            )
            datos = json.loads(respuesta_ia.text)
            datos["fecha"] = fecha_hoy_str
            datos["mes"] = mes_actual
            datos["tipo_movimiento"] = "Gasto"
            logger.info(f"🤖 IA Financiera OCR extrajo: {datos}")
            return datos
        except json.JSONDecodeError as e:
            logger.error(f"❌ Error OCR al decodificar JSON: {e}")
            return {"error": "La IA devolvió un formato ilegible del ticket."}
        except Exception as e:
            logger.error(f"❌ Error OCR API Gemini: {e}")
            return {"error": str(e)}

    @staticmethod
    def interpretar_frase_con_ia(frase_usuario: str) -> dict:
        api_key = os.getenv("GEMINI_API_KEY")
        if not api_key:
            return {"error": "Configuración de IA incompleta en el servidor."}
        ahora = datetime.now(tz_py)
        dias_semana = [
            "Lunes",
            "Martes",
            "Miércoles",
            "Jueves",
            "Viernes",
            "Sábado",
            "Domingo",
        ]
        dia_nombre = dias_semana[ahora.weekday()]
        fecha_hoy_str = ahora.strftime("%d/%m/%Y")
        hora_hoy_str = ahora.strftime("%H:%M")
        prompt_sistema = (
            f"Eres un asistente virtual experto en procesamiento "
            f"de lenguaje natural y extracción de cronogramas.\n"
            f"CONTEXTO TEMPORAL REAL: Hoy es {dia_nombre} "
            f"{fecha_hoy_str} y la hora actual en Paraguay "
            f"es {hora_hoy_str}.\n\n"
            f"Tu tarea es analizar la frase enviada por el usuario "
            f"y extraer un evento para su agenda.\n"
            f"Debes devolver obligatoriamente un objeto JSON "
            f"estructurado con las siguientes tres llaves (strings):\n"
            f"1. 'titulo': Descripción clara y concisa de la tarea "
            f"o evento (corrige ortografía si es necesario, "
            f"usa mayúsculas iniciales).\n"
            f"2. 'fecha': Fecha del evento formateada estrictamente "
            f"como DD/MM/AAAA. (Calcula el día correcto basándote "
            f"en que hoy es {fecha_hoy_str}. Si el usuario dice "
            f"'el próximo lunes', calcula la fecha exacta del "
            f"próximo lunes).\n"
            f"3. 'hora': Hora del evento formateada estrictamente "
            f"como HH:MM (formato 24h). Si el usuario no especifica "
            f"una hora (ej: 'tengo médico el martes'), asume por "
            f"defecto la hora '08:00'.\n\n"
            f"Restricción absoluta: No agregues introducciones, "
            f"explicaciones ni comentarios. Tu respuesta debe ser "
            f"puramente el JSON."
        )
        try:
            client = genai.Client(api_key=api_key)
            respuesta_ia = client.models.generate_content(
                model="gemini-2.5-flash",
                contents=f"Contexto del Sistema:\n{prompt_sistema}\n\nMensaje del Usuario: {frase_usuario}",
                config=types.GenerateContentConfig(
                    response_mime_type="application/json"
                ),
            )
            datos_formateados = json.loads(respuesta_ia.text)
            logger.info(f"🤖 IA interpretó con éxito: {datos_formateados}")
            return datos_formateados
        except json.JSONDecodeError as jde:
            logger.error(
                f"❌ Error al decodificar JSON de la IA: {jde}. Respuesta cruda: {respuesta_ia.text}"
            )
            return {"error": "La IA devolvió un formato ilegible. Intentá refrasear."}
        except Exception as e:
            logger.error(f"❌ Error en la llamada a Gemini API: {e}")
            return {"error": f"No se pudo conectar con el motor de IA: {str(e)}"}
