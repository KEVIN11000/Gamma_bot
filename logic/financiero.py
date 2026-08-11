import os
import json
from datetime import datetime
import pytz
from google import genai
from google.genai import types

from logic.logic import ConexionSheets, guardar_log

tz_py = pytz.timezone('America/Buenos_Aires')

class AgenteFinanciero:
    def __init__(self, spreadsheet_id):
        self.spreadsheet_id = spreadsheet_id
        try:
            self.cliente = ConexionSheets.obtener_cliente()
            self.wb = self.cliente.open_by_key(self.spreadsheet_id)
            self._obtener_o_crear_hoja_libro_diario()
        except Exception as e:
            guardar_log(f"❌ Error al conectar a Sheets en AgenteFinanciero: {e}")
            raise

    def _obtener_o_crear_hoja_libro_diario(self):
        titulos_existentes = [h.title for h in self.wb.worksheets()]
        nombre_hoja = "Libro_Diario"
        if nombre_hoja not in titulos_existentes:
            self.ws = self.wb.add_worksheet(title=nombre_hoja, rows="1000", cols="11")
            encabezados = ["Fecha", "Movimiento", "Proveedor/Cliente", "Nro Factura", "Neto", "IVA", "Total", "Categoría", "Comprobante", "Rastro/Foto", "Mes"]
            self.ws.update("A1:K1", [encabezados])
            guardar_log(f"✅ Se creó la pestaña {nombre_hoja} en Google Sheets.")
        else:
            self.ws = self.wb.worksheet(nombre_hoja)

    def procesar_movimiento_con_ia(self, texto_usuario: str, tipo_movimiento: str):
        """
        Llama a Gemini para extraer los datos de un gasto o ingreso enviado por texto.
        """
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
            f"3. 'neto': Monto antes de impuestos (si no se especifica IVA, pon el total aquí también, sin puntos ni comas).\n"
            f"4. 'iva': Monto del impuesto (si no se especifica, pon '0').\n"
            f"5. 'total': Monto total del movimiento (solo números, sin puntos ni comas).\n"
            f"6. 'categoria': Categoriza en una palabra (ej. Comida, Transporte, Honorarios, Sueldo, Ocio, Varios).\n"
            f"7. 'comprobante': Si no especifica que es virtual, pon 'No Legal' por defecto si es Gasto, o 'Física Legal' si tiene sentido.\n"
            f"Solo devuelve el JSON, sin markdown ni explicaciones adicionales."
        )

        try:
            client = genai.Client(api_key=api_key)
            respuesta_ia = client.models.generate_content(
                model='gemini-2.5-flash',
                contents=f"Contexto del Sistema:\n{prompt_sistema}\n\nMensaje del Usuario: {texto_usuario}",
                config=types.GenerateContentConfig(
                    response_mime_type="application/json"
                )
            )

            datos = json.loads(respuesta_ia.text)
            datos['fecha'] = fecha_hoy_str
            datos['mes'] = mes_actual
            datos['tipo_movimiento'] = tipo_movimiento.capitalize()
            guardar_log(f"🤖 IA Financiera interpretó: {datos}")
            return datos

        except json.JSONDecodeError as e:
            guardar_log(f"❌ Error al decodificar JSON financiero: {e}")
            return {"error": "La IA devolvió un formato ilegible."}
        except Exception as e:
            guardar_log(f"❌ Error API Gemini: {e}")
            return {"error": str(e)}

    def registrar_movimiento(self, datos: dict) -> str:
        """
        Inserta la fila en Libro_Diario.
        """
        try:
            # Obtener próxima fila vacía
            col_fechas = self.ws.col_values(1)
            fila = len(col_fechas) + 1
            
            valores = [
                datos.get('fecha', ''),
                datos.get('tipo_movimiento', ''),
                datos.get('proveedor_cliente', ''),
                datos.get('nro_factura', 'S/N'),
                str(datos.get('neto', '0')),
                str(datos.get('iva', '0')),
                str(datos.get('total', '0')),
                datos.get('categoria', 'Varios'),
                datos.get('comprobante', 'No Legal'),
                datos.get('file_id', 'null'),
                datos.get('mes', '')
            ]
            
            self.ws.update(f"A{fila}:K{fila}", [valores])
            
            icono = "🟢" if datos.get('tipo_movimiento') == "Ingreso" else "🔴"
            monto_fmt = "{:,}".format(int(datos.get('total', 0))).replace(",", ".")
            return f"✅ Movimiento guardado en Libro Diario:\n{icono} {datos.get('tipo_movimiento')} por Gs. {monto_fmt}\nCategoría: {datos.get('categoria')}"
        except Exception as e:
            guardar_log(f"❌ Error registrando movimiento: {e}")
            return f"❌ Hubo un error al guardar en la planilla: {str(e)}"

    def obtener_balance(self) -> dict:
        """
        Calcula el Flujo Neto basado en el Libro Diario completo (o del mes actual).
        """
        try:
            registros = self.ws.get_all_values()[1:] # Omitir encabezado
            
            total_ingresos = 0
            total_gastos = 0
            
            for fila in registros:
                if len(fila) < 7: continue
                tipo = fila[1].strip().lower()
                monto = fila[6].strip()
                if not monto.isdigit(): continue
                
                monto_val = int(monto)
                if tipo == 'ingreso':
                    total_ingresos += monto_val
                elif tipo == 'gasto':
                    total_gastos += monto_val
            
            flujo_neto = total_ingresos - total_gastos
            
            return {
                "ingresos": total_ingresos,
                "gastos": total_gastos,
                "flujo_neto": flujo_neto
            }
        except Exception as e:
            guardar_log(f"❌ Error al obtener balance: {e}")
            return None
