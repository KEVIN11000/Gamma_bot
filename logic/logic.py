import gspread
from google.oauth2.service_account import Credentials
from datetime import datetime
from dotenv import load_dotenv
import os
import pytz
import json

# 🆕 IMPORTS DE LA FASE 2 & 3 (Google GenAI moderno)
from google import genai
from google.genai import types

base_path = "/home/kevin11000/mysite"
load_dotenv(os.path.join(base_path, ".env"))

tz_py = pytz.timezone('America/Buenos_Aires')

class AgenteAutonomoHoras:
    MONTO_POR_HORA = 14634

    def __init__(self, spreadsheet_id, mes="Mayo"):
        self.mes = mes
        scopes = ["https://www.googleapis.com/auth/spreadsheets", "https://www.googleapis.com/auth/drive"]

        # Ruta absoluta para PythonAnywhere
        base_path = "/home/kevin11000/mysite"
        path_json = os.path.join(base_path, "credentials.json")

        try:
            credenciales = Credentials.from_service_account_file(path_json, scopes=scopes)
            self.cliente = gspread.authorize(credenciales)
            self.wb = self.cliente.open_by_key(spreadsheet_id)
            self._cargar_hoja_activa()
        except Exception as e:
            msj = f"❌ Error al abrir credenciales en {path_json}: {e}"
            self._guardar_log(msj)
            print(msj)
            raise

    def _guardar_log(self, mensaje):
        timestamp = datetime.now(tz_py).strftime("%Y-%m-%d %H:%M:%S")
        path = os.path.join("/home/kevin11000/mysite", "gen_log.txt")
        otpt = f"[{timestamp}] {mensaje}\n"
        with open(path, "a", encoding="utf-8") as f:
            f.write(otpt)
        print(otpt.strip())

    def fin_de(self):
        ahora = datetime.now(tz_py)
        dias_semana = ["Lunes", "Martes", "Miércoles", "Jueves", "Viernes", "Sábado", "Domingo"]
        dia = dias_semana[ahora.weekday()]
        free_day = "Domingo"

        if dia != free_day:
            return None
        else:
            return 1

    def _cargar_hoja_activa(self):
        """Lee el archivo local para saber qué hoja está abierta para registros."""
        base_path = "/home/kevin11000/mysite"
        path_txt = os.path.join(base_path, "periodo_actual.txt")

        if not os.path.exists(path_txt):
            nombre_inicial = self.mes if self.mes else "Mayo 2026"
            with open(path_txt, "w", encoding="utf-8") as f:
                f.write(nombre_inicial)

        with open(path_txt, "r", encoding="utf-8") as f:
            nombre_hoja = f.read().strip()

        self.ws = self.wb.worksheet(nombre_hoja)

    def _obtener_o_crear_fila_hoy(self):
        """Busca la fecha de hoy en la hoja del período activo actual."""
        ahora = datetime.now(tz_py)
        hoy_str = ahora.strftime("%d/%m/%Y")

        self._cargar_hoja_activa()

        dias_semana = ["Lunes", "Martes", "Miércoles", "Jueves", "Viernes", "Sábado", "Domingo"]
        nombre_dia = dias_semana[ahora.weekday()]

        fechas_columna_b = self.ws.col_values(2)
        primera_fila_vacia = None

        for i in range(1, 40):
            fila = i + 1
            if i < len(fechas_columna_b):
                celda = fechas_columna_b[i].strip()
                if celda == hoy_str:
                    return fila
            elif primera_fila_vacia is None:
                primera_fila_vacia = fila

                # Insertamos el Día y la Fecha en las columnas A y B
                self.ws.update(f"A{primera_fila_vacia}:B{primera_fila_vacia}", [[nombre_dia, hoy_str]],
                               value_input_option='USER_ENTERED')

                # Fórmula matemática dinámica
                formula_horas = (
                    f'=SI(VALOR(D{primera_fila_vacia})<>""; '
                    f'(VALOR(D{primera_fila_vacia})-VALOR(C{primera_fila_vacia}))+(VALOR(F{primera_fila_vacia})-VALOR(E{primera_fila_vacia})); '
                    f'VALOR(F{primera_fila_vacia})-VALOR(C{primera_fila_vacia})) * 24')

                self.ws.update(f"G{primera_fila_vacia}", [[formula_horas]], value_input_option='USER_ENTERED')
                return primera_fila_vacia
        return None

    def ejecutar_marcado_para_bot(self, modo="normal"):
        fila = self._obtener_o_crear_fila_hoy()
        if not fila:
            msg = "❌ Límite de filas alcanzado o error en fecha."
            self._guardar_log(msg)
            return msg

        hora_ahora = datetime.now(tz_py).strftime("%H:%M")

        if hasattr(self, 'fin_de') and self.fin_de():
            log_msg = f"{hora_ahora} Dia libre, no hay marcas que hacer!!!"
            self._guardar_log(log_msg)
            return "ℹ️ Hoy es tu día libre, no es necesario registrar marcas."

        COLUMNAS_NORMAL  = [(3, "Entrada"), (4, "S. Almuerzo"), (5, "V. Almuerzo"), (6, "Salida")]
        COLUMNAS_DIRECTO = [(3, "Entrada"), (6, "Salida")]
        columnas = COLUMNAS_DIRECTO if modo == "directo" else COLUMNAS_NORMAL

        LETRAS_COLUMNAS = {3: "C", 4: "D", 5: "E", 6: "F"}
        valores_fila = self.ws.row_values(fila)

        def celda_vacia(col_index):
            idx = col_index - 1
            return idx >= len(valores_fila) or not valores_fila[idx].strip()

        if modo == "directo":
            almerzo_ocupado = not celda_vacia(4) or not celda_vacia(5)
            if almerzo_ocupado:
                return (
                    "⚠️ Ya hay registros de almuerzo en la planilla.\n"
                    "Usá el marcado normal (▶️ Marcar) para registrar la salida."
                )

        for col_index, nombre in columnas:
            if celda_vacia(col_index):
                letra_celda = LETRAS_COLUMNAS[col_index]
                self.ws.update(f"{letra_celda}{fila}", [[hora_ahora]], value_input_option="USER_ENTERED")

                log_msg = f"Marcado [{modo}] {nombre}: {hora_ahora} en fila {fila}"
                print(f"✅ {log_msg}")
                self._guardar_log(log_msg)
                return f"✅ *{nombre}* registrado a las {hora_ahora}."

        return "ℹ️ Ya completaste todos los registros of hoy."

    def ejecutar_cierre_periodo_manual(self):
        base_path = "/home/kevin11000/mysite"
        path_txt = os.path.join(base_path, "periodo_actual.txt")

        if os.path.exists(path_txt):
            with open(path_txt, "r", encoding="utf-8") as f:
                hoja_actual = f.read().strip()
        else:
            hoja_actual = "Mayo 2026"

        meses = ["Enero", "Febrero", "Marzo", "Abril", "Mayo", "Junio",
                 "Julio", "Agosto", "Septiembre", "Octubre", "Noviembre", "Diciembre"]

        partes = hoja_actual.split()
        if len(partes) == 2 and partes[0] in meses:
            mes_nombre = partes[0]
            anio_actual = int(partes[1])
            idx = meses.index(mes_nombre)
            if idx == 11:
                mes_siguiente = meses[0]
                anio_siguiente = anio_actual + 1
            else:
                mes_siguiente = meses[idx + 1]
                anio_siguiente = anio_actual
            nombre_hoja_nueva = f"{mes_siguiente} {anio_siguiente}"
        else:
            ahora = datetime.now(tz_py)
            nombre_hoja_nueva = f"Periodo_{ahora.strftime('%d_%m_%Y')}"

        try:
            # ── Verificar si la hoja destino ya existe ────────────────────────
            titulos_existentes = [h.title for h in self.wb.worksheets()]
            hoja_ya_existia = nombre_hoja_nueva in titulos_existentes

            if hoja_ya_existia:
                # La hoja ya fue creada (cierre previo parcial): la reutilizamos
                nueva_hoja = self.wb.worksheet(nombre_hoja_nueva)
                self._guardar_log(f"⚠️ La hoja '{nombre_hoja_nueva}' ya existía. Reutilizando sin recrear encabezados.")
                mensaje_creacion = f"⚠️ La pestaña *{nombre_hoja_nueva}* ya existía y fue reutilizada."
            else:
                # Flujo normal: crear hoja nueva con encabezados
                nueva_hoja = self.wb.add_worksheet(title=nombre_hoja_nueva, rows="60", cols="10")
                encabezados = ["Dia", "Fecha", "Hora entrada", "Salgo almuerzo", "Vuelta almuerzo", "Hora salida", "Horas"]
                nueva_hoja.update("A1:G1", [encabezados])
                mensaje_creacion = f"Se ha creado la pestaña *{nombre_hoja_nueva}* con sus encabezados."

            # ── Siempre actualizar el período activo ──────────────────────────
            with open(path_txt, "w", encoding="utf-8") as f:
                f.write(nombre_hoja_nueva)

            self._guardar_log(f"🔄 CIERRE PROCESADO: Finalizado '{hoja_actual}'. Activo '{nombre_hoja_nueva}'")
            return (
                f"✅ Cierre de período exitoso.\n\n"
                f"{mensaje_creacion} "
                f"A partir de ahora, todas las marcaciones se registrarán ahí."
            )

        except Exception as e:
            # ── Si falla algo inesperado, aún así intentamos salvar el período ─
            self._guardar_log(f"❌ Error inesperado en cierre: {e}")
            return f"❌ Error al ejecutar el cierre: {e}"

    def _parsear_horas_a_decimal(self, valor_str: str) -> float:
        valor_str = str(valor_str).strip().replace(',','.')

        if not valor_str or "horas" in valor_str.lower():
            return 0.0

        try:
            if ':' in valor_str:
                partes = valor_str.split(':') # Corregido typo 'splt' -> 'split'
                return int(partes[0]) + int(partes[1]) / 60

            valor_float = float(valor_str)
            return valor_float

        except (ValueError, IndexError):
            return 0.0

    def generar_reporte_pdf(self, nombre_hoja=None, descuento=0):
        try:
            from reportlab.lib.pagesizes import A4
            from reportlab.lib import colors
            from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer, HRFlowable
            from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
            from reportlab.lib.units import cm
            from reportlab.lib.enums import TA_CENTER

            hojas = self.wb.worksheets()
            if nombre_hoja:
                hoja = self.wb.worksheet(nombre_hoja)
            else:
                if len(hojas) < 2:
                    return None, "❌ No hay hoja de cierre disponible todavía."
                hoja = hojas[-2]

            nombre_periodo = hoja.title
            datos = hoja.get_all_values()
            if not datos or len(datos) < 2:
                return None, "❌ La hoja de cierre está vacía."

            headers = datos[0]
            filas_raw = datos[1:]
            filas_datos = [f for f in filas_raw if any(c.strip() for c in f)]

            col_horas = next((i for i, h in enumerate(headers) if 'horas' in h.lower()), None)
            if col_horas is None:
                return None, "❌ No se encontró columna de horas. Verificá el encabezado."

            total_decimal = sum(self._parsear_horas_a_decimal(f[col_horas]) for f in filas_datos if col_horas < len(f))
            h_enteras = int(total_decimal)
            m_resto = int(round((total_decimal - h_enteras) * 60))
            total_str = f"{h_enteras}h {m_resto:02d}m"

            salario_bruto = total_decimal * self.MONTO_POR_HORA
            salario_neto = salario_bruto - float(descuento)

            def gs(n):
                return f"Gs. {int(n):,}".replace(",", ".")

            directorio = "/home/kevin11000/mysite/reportes"
            os.makedirs(directorio, exist_ok=True)
            nombre_archivo = f"reporte_{nombre_periodo.replace(' ', '_').replace('/', '-')}.pdf"
            ruta_pdf = f"{directorio}/{nombre_archivo}"

            doc = SimpleDocTemplate(ruta_pdf, pagesize=A4, leftMargin=1.5*cm, rightMargin=1.5*cm, topMargin=1.5*cm, bottomMargin=1.5*cm)
            estilos = getSampleStyleSheet()

            def estilo(nombre, **kw):
                return ParagraphStyle(nombre, parent=estilos['Normal'], **kw)

            e_titulo = estilo('Tit', fontSize=16, alignment=TA_CENTER, fontName='Helvetica-Bold', spaceAfter=3)
            e_sub = estilo('Sub', fontSize=10, alignment=TA_CENTER, textColor=colors.HexColor('#555555'), spaceAfter=2)
            e_seccion = estilo('Sec', fontSize=11, fontName='Helvetica-Bold', spaceBefore=14, spaceAfter=6, textColor=colors.HexColor('#1a1a2e'))

            AZUL = colors.HexColor('#1a1a2e')
            GRIS = colors.HexColor('#f5f5f5')
            GRIS2 = colors.HexColor('#cccccc')

            story = []
            story.append(Paragraph("REPORTE DE PERÍODO", e_titulo))
            story.append(Paragraph(nombre_periodo, e_sub))
            story.append(Paragraph(f"Generado: {datetime.now(tz_py).strftime('%d/%m/%Y  %I:%M %p')}", e_sub))
            story.append(HRFlowable(width="100%", thickness=2, color=AZUL, spaceAfter=14))

            story.append(Paragraph("Registros del período", e_seccion))
            ancho_util = A4[0] - 3*cm
            col_w = [ancho_util / len(headers)] * len(headers)

            tabla_filas = [headers]
            for f in filas_datos:
                f_completa = (f + [''] * len(headers))[:len(headers)]
                tabla_filas.append(f_completa)

            tabla = Table(tabla_filas, colWidths=col_w, repeatRows=1)
            tabla.setStyle(TableStyle([
                ('BACKGROUND', (0, 0), (-1, 0), AZUL),
                ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
                ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                ('FONTSIZE', (0, 0), (-1, 0), 8),
                ('ALIGN', (0, 0), (-1, 0), 'CENTER'),
                ('FONTSIZE', (0, 1), (-1, -1), 8),
                ('ALIGN', (0, 1), (-1, -1), 'CENTER'),
                ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, GRIS]),
                ('GRID', (0, 0), (-1, -1), 0.4, GRIS2),
                ('BOX', (0, 0), (-1, -1), 1, AZUL),
                ('TOPPADDING', (0, 0), (-1, -1), 5),
                ('BOTTOMPADDING', (0, 0), (-1, -1), 5),
            ]))
            story.append(tabla)

            story.append(Spacer(1, 20))
            story.append(HRFlowable(width="100%", thickness=0.5, color=GRIS2, spaceAfter=6))
            story.append(Paragraph("Resumen del período", e_seccion))

            resumen_data = [
                ["Total horas trabajadas", total_str],
                ["Monto por hora",         gs(self.MONTO_POR_HORA)],
                ["Salario bruto",          gs(salario_bruto)],
            ]

            if descuento > 0:
                resumen_data.append(["Descuentos aplicados", f"- {gs(descuento)}"])
                resumen_data.append(["Salario neto a cobrar", gs(salario_neto)])
            else:
                resumen_data.append(["Salario del mes", gs(salario_neto)])

            cw = [ancho_util * 0.6, ancho_util * 0.4]
            tabla_resumen = Table(resumen_data, colWidths=cw)
            tabla_resumen.setStyle(TableStyle([
                ('FONTNAME', (0, 0), (-1, -2), 'Helvetica'),
                ('FONTNAME', (0, -1), (-1, -1), 'Helvetica-Bold'),
                ('FONTSIZE', (0, 0), (-1, -2), 10),
                ('FONTSIZE', (0, -1), (-1, -1), 12),
                ('ALIGN', (1, 0), (1, -1), 'RIGHT'),
                ('ROWBACKGROUNDS', (0, 0), (-1, -2), [colors.white, GRIS]),
                ('BACKGROUND', (0, -1), (-1, -1), AZUL),
                ('TEXTCOLOR', (0, -1), (-1, -1), colors.white),
                ('BOX', (0, 0), (-1, -1), 1, AZUL),
                ('LINEABOVE', (0, -1), (-1, -1), 1.5, AZUL),
                ('TOPPADDING', (0, 0), (-1, -1), 8),
                ('BOTTOMPADDING', (0, 0), (-1, -1), 8),
                ('LEFTPADDING', (0, 0), (-1, -1), 10),
                ('RIGHTPADDING', (0, 0), (-1, -1), 10),
            ]))
            story.append(tabla_resumen)

            doc.build(story)
            return ruta_pdf, f"✅ Reporte generado — {nombre_periodo}"
        except Exception as e:
            return None, f"❌ Error al generar reporte: {type(e).__name__} - {str(e)}"

    def verificar_avisos_activos(self):
        """
        Escanea los avisos agendados, elimina automáticamente los que ya vencieron
        y arma un bloque de texto formateado si coincide con los hitos de tiempo
        (30, 7, 5, 3 o 1 día antes del evento). Evita repetir alertas ya enviadas.
        """
        base_path = "/home/kevin11000/mysite"
        path_json = os.path.join(base_path, "avisos.json")

        if not os.path.exists(path_json):
            return ""

        try:
            with open(path_json, "r", encoding="utf-8") as f:
                avisos = json.load(f)
        except Exception as e:
            self._guardar_log(f"❌ Error al leer avisos.json: {e}")
            return ""

        ahora = datetime.now(tz_py)
        hoy_date = ahora.date()

        avisos_actualizados = []
        alertas_a_mostrar = []
        hitos_objetivo = [30, 7, 5, 3, 1]
        modificado = False

        for aviso in avisos:
            try:
                # Parseamos la fecha del evento guardada (Formato esperado: DD/MM/AAAA HH:MM)
                fecha_ev = datetime.strptime(aviso["fecha_evento"], "%d/%m/%Y %H:%M")
                fecha_ev = tz_py.localize(fecha_ev) if fecha_ev.tzinfo is None else fecha_ev
            except Exception:
                # Si algún registro está corrupto por error manual, lo salta para no romper el bucle
                modificado = True
                continue

            # 1. 🗑️ AUTO-LIMPIEZA: Si la fecha y hora del evento ya pasaron, se elimina del JSON
            if ahora > fecha_ev:
                modificado = True
                self._guardar_log(f"🗑️ Aviso auto-eliminado por expiración: '{aviso['titulo']}'")
                continue

            # Calcular la diferencia de días exactos (basado puramente en fechas)
            dias_restantes = (fecha_ev.date() - hoy_date).days

            # 2. 🛡️ CONTROL DE HITOS Y ANTI-SPAM
            if dias_restantes in hitos_objetivo:
                hito_str = str(dias_restantes)

                # Si este hito en particular no fue disparado anteriormente para este aviso
                if hito_str not in aviso.get("alertas_disparadas", []):
                    alertas_a_mostrar.append((dias_restantes, aviso["titulo"], aviso["fecha_evento"]))

                    if "alertas_disparadas" not in aviso:
                        aviso["alertas_disparadas"] = []

                    aviso["alertas_disparadas"].append(hito_str)
                    modificado = True

            avisos_actualizados.append(aviso)

        # Si hubo alertas disparadas o registros borrados por vencimiento, guardamos los cambios
        if modificado:
            try:
                with open(path_json, "w", encoding="utf-8") as f:
                    json.dump(avisos_actualizados, f, indent=2, ensure_ascii=False)
            except Exception as e:
                self._guardar_log(f"❌ Error al guardar modificaciones en avisos.json: {e}")

        # 3. 📝 FORMATEO DEL MENSAJE PARA TELEGRAM
        if not alertas_a_mostrar:
            return ""

        # Ordenamos las alertas para poner primero las más urgentes (1 día, luego 3, etc.)
        alertas_a_mostrar.sort(key=lambda x: x[0])

        lineas = ["\n\n─── 📢 *RECORDATORIOS ACTIVOS* ───"]
        for dias, titulo, fecha_str in alertas_a_mostrar:
            txt_dias = f"{dias} día" if dias == 1 else f"{dias} días"
            lineas.append(f"⏳ *Faltan {txt_dias}:* {titulo} ({fecha_str})")

        return "\n".join(lineas)

    # ─────────────────────────────────────────────────────────────────────────
    # 🧠 MÉTODOS DE LA FASE 3: INTEGRACIÓN CON GEMINI 2.5 Y PERSISTENCIA DE AVISOS
    # ─────────────────────────────────────────────────────────────────────────

    def interpretar_frase_con_ia(self, frase_usuario: str):
        """
        Toma una frase libre del usuario, le inyecta el contexto temporal dinámico
        y le pide a Gemini 2.5 que extraiga el título, la fecha y la hora en un JSON limpio.
        """
        api_key = os.getenv("GEMINI_API_KEY")
        if not api_key:
            self._guardar_log("❌ Error: No se encontró GEMINI_API_KEY en el entorno.")
            return {"error": "Configuración de IA incompleta en el servidor."}

        # 📅 ANCLAJE TEMPORAL DINÁMICO
        ahora = datetime.now(tz_py)
        dias_semana = ["Lunes", "Martes", "Miércoles", "Jueves", "Viernes", "Sábado", "Domingo"]
        dia_nombre = dias_semana[ahora.weekday()]
        fecha_hoy_str = ahora.strftime("%d/%m/%Y")
        hora_hoy_str = ahora.strftime("%H:%M")

        prompt_sistema = (
            f"Eres un asistente virtual experto en procesamiento de lenguaje natural y extracción de cronogramas.\n"
            f"CONTEXTO TEMPORAL REAL: Hoy es {dia_nombre} {fecha_hoy_str} y la hora actual en Paraguay es {hora_hoy_str}.\n\n"
            f"Tu tarea es analizar la frase enviada por el usuario y extraer un evento para su agenda.\n"
            f"Debes devolver obligatoriamente un objeto JSON estructurado con las siguientes tres llaves (strings):\n"
            f"1. 'titulo': Descripción clara y concisa de la tarea o evento (corrige ortografía si es necesario, usa mayúsculas iniciales).\n"
            f"2. 'fecha': Fecha del evento formateada estrictamente como DD/MM/AAAA. (Calcula el día correcto basándote en que hoy es {fecha_hoy_str}. Si el usuario dice 'el próximo lunes', calcula la fecha exacta del próximo lunes).\n"
            f"3. 'hora': Hora del evento formateada estrictamente como HH:MM (formato 24h). Si el usuario no especifica una hora (ej: 'tengo médico el martes'), asume por defecto la hora '08:00'.\n\n"
            f"Restricción absoluta: No agregues introducciones, explicaciones ni comentarios. Tu respuesta debe ser puramente el JSON."
        )

        try:
            client = genai.Client(api_key=api_key)

            respuesta_ia = client.models.generate_content(
                model='gemini-2.5-flash',  # 🚀 Modelo de última generación compatible con google-genai
                contents=f"Contexto del Sistema:\n{prompt_sistema}\n\nMensaje del Usuario: {frase_usuario}",
                config=types.GenerateContentConfig(
                    response_mime_type="application/json"
                )
            )

            datos_formateados = json.loads(respuesta_ia.text)
            self._guardar_log(f"🤖 IA interpretó con éxito: {datos_formateados}")
            return datos_formateados

        except json.JSONDecodeError as jde:
            self._guardar_log(f"❌ Error al decodificar JSON de la IA: {jde}. Respuesta cruda: {respuesta_ia.text}")
            return {"error": "La IA devolvió un formato ilegible. Intentá refrasear."}
        except Exception as e:
            self._guardar_log(f"❌ Error en la llamada a Gemini API: {e}")
            return {"error": f"No se pudo conectar con el motor de IA: {str(e)}"}

    def guardar_nuevo_aviso_en_sheets(self, datos_evento: dict) -> str:
        """
        Recibe los datos validados del bot de Telegram tras la confirmación del usuario,
        los adapta al esquema requerido por verificar_avisos_activos y los guarda en avisos.json.
        """
        base_path = "/home/kevin11000/mysite"
        path_json = os.path.join(base_path, "avisos.json")

        # Combinar fecha y hora para el formato estándar del lector de la Fase 1
        fecha_evento_completa = f"{datos_evento['fecha']} {datos_evento['hora']}"

        nuevo_registro = {
            "titulo": datos_evento["titulo"],
            "fecha_evento": fecha_evento_completa,
            "alertas_disparadas": []
        }

        try:
            # Leer registros existentes
            if os.path.exists(path_json):
                with open(path_json, "r", encoding="utf-8") as f:
                    try:
                        lista_avisos = json.load(f)
                        if not isinstance(lista_avisos, list):
                            lista_avisos = []
                    except json.JSONDecodeError:
                        lista_avisos = []
            else:
                lista_avisos = []

            # Insertar el nuevo hito
            lista_avisos.append(nuevo_registro)

            # Persistir los cambios en disco
            with open(path_json, "w", encoding="utf-8") as f:
                json.dump(lista_avisos, f, indent=2, ensure_ascii=False)

            self._guardar_log(f"💾 Nuevo aviso guardado en json: '{datos_evento['titulo']}' para el {fecha_evento_completa}")

            return (
                f"✅ *¡Aviso guardado con éxito!*\n\n"
                f"📌 *{datos_evento['titulo']}*\n"
                f"📅 Agendado: {datos_evento['fecha']} a las {datos_evento['hora']} hs.\n\n"
                f"🔔 _Las alertas se dispararán automáticamente a los 30, 7, 5, 3 y 1 días antes._"
            )
        except Exception as e:
            self._guardar_log(f"❌ Error al persistir el nuevo aviso en avisos.json: {e}")
            return f"❌ Error interno al guardar en la base de datos: {str(e)}"

    def obtener_lista_avisos(self):
        """Devuelve la lista completa de todos los avisos programados haciendo antes una limpieza de expirados."""
        base_path = "/home/kevin11000/mysite"
        path_json = os.path.join(base_path, "avisos.json")
        if not os.path.exists(path_json):
            return []
        try:
            with open(path_json, "r", encoding="utf-8") as f:
                avisos = json.load(f)
        except Exception:
            return []

        ahora = datetime.now(tz_py)
        avisos_filtrados = []
        modificado = False

        for aviso in avisos:
            try:
                fecha_ev = datetime.strptime(aviso["fecha_evento"], "%d/%m/%Y %H:%M")
                fecha_ev = tz_py.localize(fecha_ev) if fecha_ev.tzinfo is None else fecha_ev
                if ahora <= fecha_ev:
                    avisos_filtrados.append(aviso)
                else:
                    modificado = True
            except Exception:
                modificado = True

        if modificado:
            try:
                with open(path_json, "w", encoding="utf-8") as f:
                    json.dump(avisos_filtrados, f, indent=2, ensure_ascii=False)
            except Exception as e:
                self._guardar_log(f"❌ Error al guardar en obtener_lista_avisos: {e}")

        return avisos_filtrados

    def eliminar_aviso_por_indice(self, index: int):
        """Elimina un aviso específico por su posición en la lista y persiste el cambio."""
        base_path = "/home/kevin11000/mysite"
        path_json = os.path.join(base_path, "avisos.json")
        if not os.path.exists(path_json):
            return None
        try:
            with open(path_json, "r", encoding="utf-8") as f:
                avisos = json.load(f)

            if 0 <= index < len(avisos):
                aviso_eliminado = avisos.pop(index)
                with open(path_json, "w", encoding="utf-8") as f:
                    json.dump(avisos, f, indent=2, ensure_ascii=False)
                return aviso_eliminado["titulo"]
        except Exception as e:
            self._guardar_log(f"❌ Error al eliminar aviso por índice: {e}")
        return None

    def obtener_nombres_hojas(self, limite: int = 6) -> list:
        """
        Devuelve los títulos de las últimas `limite` hojas del spreadsheet,
        excluyendo la hoja activa actual (donde se están registrando las marcas).
        Se usa para el comando /reporte para que el usuario elija el período.
        """
        try:
            base_path = "/home/kevin11000/mysite"
            path_txt = os.path.join(base_path, "periodo_actual.txt")
            hoja_activa = ""
            if os.path.exists(path_txt):
                with open(path_txt, "r", encoding="utf-8") as f:
                    hoja_activa = f.read().strip()

            hojas = self.wb.worksheets()
            nombres = [h.title for h in hojas if h.title != hoja_activa]
            return nombres[-limite:][::-1]  # Las más recientes primero
        except Exception as e:
            self._guardar_log(f"❌ Error en obtener_nombres_hojas: {e}")
            return []

class AgenteAsistenciaMaterias:
    SPREADSHEET_ID = "1VJe98WHoL5U7aDiGLIw55ZHnG-M6bAuLmIZx9LNbWnY"
    HORARIOS_MATERIAS = {
        "Electricidad y Magnetismo": {
            "dia": "Viernes",
            "teoria": ("13:00", "16:00"),
            "practica": ("16:00", "18:00")
        },
        "Ecuaciones diferenciales": {
            "dia": "Sábado",
            "teoria": ("11:30", "13:30"),
            "practica": ("13:30", "15:30")
        },
        "Estática": {
            "dia": "Viernes",
            "teoria": ("07:30", "10:30"),
            "practica": ("10:30", "12:30")
        },
        "Probabilidad": {
            "dia": "Sábado",
            "teoria": ("07:30", "09:30"),
            "practica": ("09:30", "11:30")
        }
    }

    def __init__(self):
        scopes = ["https://www.googleapis.com/auth/spreadsheets", "https://www.googleapis.com/auth/drive"]
        base_path = "/home/kevin11000/mysite"
        path_json = os.path.join(base_path, "credentials.json")
        try:
            credenciales = Credentials.from_service_account_file(path_json, scopes=scopes)
            self.cliente = gspread.authorize(credenciales)
            self.wb = self.cliente.open_by_key(self.SPREADSHEET_ID)
        except Exception as e:
            self._guardar_log(f"❌ Error al conectar a Sheets de materias: {e}")
            raise

    def _guardar_log(self, mensaje):
        timestamp = datetime.now(tz_py).strftime("%Y-%m-%d %H:%M:%S")
        path = os.path.join("/home/kevin11000/mysite", "gen_log.txt")
        otpt = f"[{timestamp}] {mensaje}\n"
        with open(path, "a", encoding="utf-8") as f:
            f.write(otpt)
        print(otpt.strip())

    def obtener_materia_actual(self, ahora):
        dias_semana = ["Lunes", "Martes", "Miércoles", "Jueves", "Viernes", "Sábado", "Domingo"]
        dia_actual = dias_semana[ahora.weekday()]
        hora_actual = ahora.time()

        for materia, datos in self.HORARIOS_MATERIAS.items():
            if datos["dia"] == dia_actual:
                start_t = datetime.strptime(datos["teoria"][0], "%H:%M").time()
                end_t = datetime.strptime(datos["teoria"][1], "%H:%M").time()
                if start_t <= hora_actual <= end_t:
                    return materia, "teoria"

                start_p = datetime.strptime(datos["practica"][0], "%H:%M").time()
                end_p = datetime.strptime(datos["practica"][1], "%H:%M").time()
                if start_p <= hora_actual <= end_p:
                    return materia, "practica"
        return None, None

    def marcar_asistencia(self):
        try:
            ahora = datetime.now(tz_py)
            materia, tipo = self.obtener_materia_actual(ahora)
            if not materia:
                return "ℹ️ No hay ninguna clase en curso en este momento según el horario."

            # Verificar si existe la hoja de la materia, si no, crearla
            titulos_existentes = [h.title for h in self.wb.worksheets()]
            if materia not in titulos_existentes:
                ws = self.wb.add_worksheet(title=materia, rows="100", cols="6")
                ws.update("A1:F1", [["Día", "Fecha", "Hora Teoría", "Asistencia Teoría", "Hora Práctica", "Asistencia Práctica"]])
            else:
                ws = self.wb.worksheet(materia)
            
            hoy_str = ahora.strftime("%d/%m/%Y")
            dias_semana = ["Lunes", "Martes", "Miércoles", "Jueves", "Viernes", "Sábado", "Domingo"]
            dia_actual = dias_semana[ahora.weekday()]
            
            fechas_col = ws.col_values(2)
            fila = None
            for i, fecha in enumerate(fechas_col):
                if fecha == hoy_str:
                    fila = i + 1
                    break
            
            if fila is None:
                fila = len(fechas_col) + 1
                if fila == 1:
                    ws.update("A1:F1", [["Día", "Fecha", "Hora Teoría", "Asistencia Teoría", "Hora Práctica", "Asistencia Práctica"]])
                    fila = 2
                ws.update(f"A{fila}:B{fila}", [[dia_actual, hoy_str]])

            hora_str = ahora.strftime("%H:%M")
            if tipo == "teoria":
                ws.update(f"C{fila}:D{fila}", [[hora_str, "x"]])
            else:
                ws.update(f"E{fila}:F{fila}", [[hora_str, "x"]])

            log_msg = f"Asistencia marcada para {materia} ({tipo}) a las {hora_str} en fila {fila}"
            self._guardar_log(log_msg)
            return f"✅ Asistencia de *{materia}* ({tipo}) registrada exitosamente a las {hora_str}."
            
        except Exception as e:
            self._guardar_log(f"❌ Error marcando materia: {e}")
            return f"❌ Error interno al marcar asistencia: {str(e)}"