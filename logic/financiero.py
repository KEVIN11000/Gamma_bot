import os
import json

from logger_config import setup_logger
logger = setup_logger("financiero")
from datetime import datetime
import pytz
from google import genai
from google.genai import types

from logic.logic import ConexionSheets

tz_py = pytz.timezone('America/Buenos_Aires')

class AgenteFinanciero:
    def __init__(self, spreadsheet_id):
        self.spreadsheet_id = spreadsheet_id
        self._wb = None
        self._ws = None

    @property
    def cliente(self):
        return ConexionSheets.obtener_cliente()

    @property
    def wb(self):
        if self._wb is None:
            self._wb = self.cliente.open_by_key(self.spreadsheet_id)
        return self._wb

    @property
    def ws(self):
        if self._ws is None:
            titulos_existentes = [h.title for h in self.wb.worksheets()]
            modo_dev = os.environ.get("MODO_DESARROLLADOR", "False").lower() == "true"
            nombre_hoja = "Libro_Diario_Test" if modo_dev else "Libro_Diario"
            
            if nombre_hoja not in titulos_existentes:
                self._ws = self.wb.add_worksheet(title=nombre_hoja, rows=1000, cols=11)
                encabezados = ["Fecha", "Movimiento", "Proveedor/Cliente", "Nro Factura", "Neto", "IVA", "Total", "Categoría", "Comprobante", "Rastro/Foto", "Mes"]
                self._ws.update("A1:K1", [encabezados])
                logger.info(f"✅ Se creó la pestaña {nombre_hoja} en Google Sheets.")
            else:
                self._ws = self.wb.worksheet(nombre_hoja)
        return self._ws

    def _obtener_o_crear_hoja_libro_diario(self):
        self._ws = None
        _ = self.ws

    def _limpiar_monto(self, valor) -> int:
        import re
        if not valor: return 0
        s = str(valor)
        s = re.sub(r'[^\d-]', '', s)
        try: return int(s) if s else 0
        except ValueError: return 0

    def registrar_movimiento(self, datos: dict) -> str:
        """
        Inserta la fila en Libro_Diario.
        """
        # Validación de esquema básica
        if not datos or not isinstance(datos, dict) or 'total' not in datos:
            logger.error("JSON devuelto no contiene las llaves esenciales")
            return "❌ Error: La IA no pudo estructurar correctamente la información."
            
        try:
            nro_factura = str(datos.get('nro_factura', '')).strip()
            
            # Evitar facturas duplicadas si tienen un número válido
            if nro_factura and nro_factura.upper() not in ["S/N", "SIN NUMERO", "SIN NÚMERO", "NO ESPECIFICADO"]:
                facturas_registradas = self.ws.col_values(4) # Columna D
                if nro_factura in facturas_registradas:
                    return f"⚠️ Factura Duplicada: Ya existe un registro con la factura Nro: {nro_factura}. Operación cancelada."

            # Obtener próxima fila vacía
            col_fechas = self.ws.col_values(1)
            fila = len(col_fechas) + 1
            
            # Sanitizar valores contra inyección de fórmulas (Reporte AppSec)
            def sanitizar(val):
                s = str(val)
                if s.startswith(('=', '+', '-', '@')):
                    return f"'{s}"
                return s

            valores = [
                sanitizar(datos.get('fecha', '')),
                sanitizar(datos.get('tipo_movimiento', 'Desconocido')),
                sanitizar(datos.get('proveedor_cliente', '')),
                sanitizar(datos.get('nro_factura', '')),
                self._limpiar_monto(datos.get('neto', 0)),
                self._limpiar_monto(datos.get('iva', 0)),
                self._limpiar_monto(datos.get('total', 0)),
                sanitizar(datos.get('categoria', '')),
                sanitizar(datos.get('comprobante', '')),
                sanitizar(datos.get('file_id', '')),
                sanitizar(datos.get('mes', ''))
            ]
            
            self.ws.update(f"A{fila}:K{fila}", [valores])
            
            icono = "🟢" if datos.get('tipo_movimiento') == "Ingreso" else "🔴"
            monto_fmt = "{:,}".format(int(datos.get('total', 0))).replace(",", ".")
            return f"✅ Movimiento guardado en Libro Diario:\n{icono} {datos.get('tipo_movimiento')} por Gs. {monto_fmt}\nCategoría: {datos.get('categoria')}"
        except Exception as e:
            logger.error(f"❌ Error registrando movimiento: {e}")
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
            logger.error(f"❌ Error al obtener balance: {e}")
            return None

    def preparar_datos_reporte(self, mes=None):
        from logic.pdf_service import DatosReporte
        
        datos = self.ws.get_all_values()
        if not datos or len(datos) < 2:
            return None, "❌ El Libro Diario está vacío."
            
        headers = datos[0]
        filas_raw = datos[1:]
        
        # Filtrar por mes si se especifica (Columna K es índice 10)
        if mes:
            filas_datos = [f for f in filas_raw if len(f) > 10 and f[10].strip().lower() == mes.lower()]
            if not filas_datos:
                return None, f"❌ No hay movimientos registrados para el mes de {mes}."
            titulo_mes = f"Mes: {mes}"
        else:
            filas_datos = filas_raw
            titulo_mes = "Histórico Completo"

        total_ingresos = 0
        total_gastos = 0
        
        # Filtramos columnas para el reporte: [Fecha, Movimiento, Proveedor, Factura, Total, Categoría]
        # Índices: 0, 1, 2, 3, 6, 7
        headers_filtrados = ["Fecha", "Tipo", "Detalle", "Factura", "Monto", "Categoría"]
        filas_filtradas = []
        
        for f in filas_datos:
            f = (f + [''] * 11)[:11]
            tipo = f[1].strip().title()
            monto_str = f[6].strip()
            
            # Formatear el monto con separador de miles
            monto_val = 0
            if monto_str.isdigit():
                monto_val = int(monto_str)
                monto_fmt = f"Gs. {monto_val:,}".replace(",", ".")
            else:
                monto_fmt = monto_str
                
            if tipo.lower() == 'ingreso':
                total_ingresos += monto_val
            elif tipo.lower() == 'gasto':
                total_gastos += monto_val
                
            filas_filtradas.append([f[0], tipo, f[2], f[3], monto_fmt, f[7]])

        flujo_neto = total_ingresos - total_gastos

        def gs(n):
            return f"Gs. {int(n):,}".replace(",", ".")

        resumen_data = [
            ["Total Ingresos", gs(total_ingresos)],
            ["Total Gastos", f"- {gs(total_gastos)}"],
            ["Flujo Neto", gs(flujo_neto)],
        ]

        nombre_archivo = f"reporte_financiero_{titulo_mes.replace(' ', '_').replace(':', '')}.pdf"

        reporte = DatosReporte(
            titulo="REPORTE FINANCIERO - LIBRO DIARIO",
            subtitulo=titulo_mes,
            encabezados=headers_filtrados,
            filas=filas_filtradas,
            lineas_resumen=resumen_data,
            nombre_archivo=nombre_archivo
        )
        return reporte, None
