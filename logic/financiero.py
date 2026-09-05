from __future__ import annotations

import os
import re
import time

import pytz

from logger_config import setup_logger
from logic.constants import (
    ENCABEZADOS_LIBRO_DIARIO,
    HOJA_LIBRO_DIARIO,
    HOJA_LIBRO_DIARIO_TEST,
    TIMEZONE,
)
from logic.logic import ConexionSheets

logger = setup_logger("financiero")

tz_py = pytz.timezone(TIMEZONE)


class AgenteFinanciero:
    """
    Class AgenteFinanciero.
    """

    def __init__(self, spreadsheet_id: str) -> None:
        """
        __init__ method/function.

        Args:
            spreadsheet_id: Description for spreadsheet_id.

        Returns:
            Description of the return value.

        Raises:
            Exception: Description of the exception.
        """
        self.spreadsheet_id = spreadsheet_id
        # ID del spreadsheet que contiene el Libro Diario, si se separó en una planilla distinta
        self.libro_contable_id = os.getenv("LIBRO_CONTABLE_ID") or spreadsheet_id
        # Validate LIBRO_CONTABLE_ID format (alphanumeric, dash, underscore)
        if not re.fullmatch(r"[A-Za-z0-9_-]+", self.libro_contable_id):
            logger.warning(
                f"LIBRO_CONTABLE_ID '{self.libro_contable_id}' "
                f"tiene un formato inesperado; "
                f"se usará spreadsheet_id por defecto."
            )
            self.libro_contable_id = spreadsheet_id
        self._wb = None
        self._libro_wb = None
        self._ws = None

    @property
    def cliente(self):
        """
        cliente method/function.

        Returns:
            Description of the return value.

        Raises:
            Exception: Description of the exception.
        """
        return ConexionSheets.obtener_cliente()

    @property
    def wb(self):
        """
        wb method/function.

        Returns:
            Description of the return value.

        Raises:
            Exception: Description of the exception.
        """
        if self._wb is None:
            self._wb = self.cliente.open_by_key(self.spreadsheet_id)
        return self._wb

    @staticmethod
    def _retry_operation(func, *args, max_attempts=3, backoff=0.5, **kwargs):
        """
        _retry_operation method/function.

        Args:
            func: Description for func.
            *args: Variable length argument list.
            **kwargs: Arbitrary keyword arguments.

        Returns:
            Description of the return value.

        Raises:
            Exception: Description of the exception.
        """
        for attempt in range(1, max_attempts + 1):
            try:
                return func(*args, **kwargs)
            except Exception as e:
                logger.error(
                    f"Intento {attempt}/{max_attempts} falló en operación de Google Sheets: {e}"
                )
                if attempt == max_attempts:
                    raise
                time.sleep(backoff * attempt)

    @property
    def ws(self):
        """
        ws method/function.

        Returns:
            Description of the return value.

        Raises:
            Exception: Description of the exception.
        """
        if self._ws is None:
            # Determine which workbook to use: separate Libro Diario worksheet or default workbook
            if self.libro_contable_id and self.libro_contable_id != self.spreadsheet_id:
                if self._libro_wb is None:
                    self._libro_wb = ConexionSheets.obtener_cliente().open_by_key(
                        self.libro_contable_id
                    )
                wb = self._libro_wb
                logger.info(
                    f"Usando workbook separado para Libro Diario: {self.libro_contable_id}"
                )
            else:
                wb = self.wb
                logger.info(
                    f"Usando workbook principal para Libro Diario: {self.spreadsheet_id}"
                )
            titulos_existentes = [h.title for h in wb.worksheets()]
            modo_dev = os.environ.get("MODO_DESARROLLADOR", "False").lower() == "true"
            nombre_hoja = HOJA_LIBRO_DIARIO_TEST if modo_dev else HOJA_LIBRO_DIARIO

            if nombre_hoja not in titulos_existentes:
                self._ws = wb.add_worksheet(title=nombre_hoja, rows=1000, cols=11)
                encabezados = ENCABEZADOS_LIBRO_DIARIO
                self._retry_operation(self._ws.update, "A1:K1", [encabezados])
                logger.info(f"✅ Se creó la pestaña {nombre_hoja} en Google Sheets.")
            else:
                self._ws = wb.worksheet(nombre_hoja)
        return self._ws

    def _obtener_o_crear_hoja_libro_diario(self):
        """
        _obtener_o_crear_hoja_libro_diario method/function.

        Returns:
            Description of the return value.

        Raises:
            Exception: Description of the exception.
        """
        self._ws = None
        _ = self.ws

    def limpiar_monto(self, valor) -> int:
        """
        limpiar_monto method/function.

        Args:
            valor: Description for valor.

        Returns:
            Description of the return value.

        Raises:
            Exception: Description of the exception.
        """
        import re

        if not valor:
            return 0
        s = str(valor)
        s = re.sub(r"[^\d-]", "", s)
        try:
            return int(s) if s else 0
        except ValueError:
            return 0

    def registrar_movimiento(self, datos: dict) -> str:
        """
        Inserta la fila en Libro_Diario.

        Args:
            datos: Dictionary containing movement details.

        Returns:
            A string message indicating success or failure.

        Raises:
            Exception: If an error occurs during sheet update.
        """
        # Validación de esquema básica
        if not datos or not isinstance(datos, dict) or "total" not in datos:
            logger.error("JSON devuelto no contiene las llaves esenciales")
            return "❌ Error: La IA no pudo estructurar correctamente la información."

        try:
            nro_factura = str(datos.get("nro_factura", "")).strip()

            # Evitar facturas duplicadas si tienen un número válido
            if nro_factura and nro_factura.upper() not in [
                "S/N",
                "SIN NUMERO",
                "SIN NÚMERO",
                "NO ESPECIFICADO",
            ]:
                facturas_registradas = self.ws.col_values(4)  # Columna D
                if nro_factura in facturas_registradas:
                    return (
                        f"⚠️ Factura Duplicada: Ya existe un registro "
                        f"con la factura Nro: {nro_factura}. "
                        f"Operación cancelada."
                    )

            # Obtener próxima fila vacía
            col_fechas = self.ws.col_values(1)
            fila = len(col_fechas) + 1

            # Sanitizar valores contra inyección de fórmulas (Reporte AppSec)
            def sanitizar(val):
                """
                sanitizar method/function.

                Args:
                    val: Description for val.

                Returns:
                    Description of the return value.

                Raises:
                    Exception: Description of the exception.
                """
                s = str(val)
                if s.startswith(("=", "+", "-", "@")):
                    return f"'{s}"
                return s

            valores = [
                sanitizar(datos.get("fecha", "")),
                sanitizar(datos.get("tipo_movimiento", "Desconocido")),
                sanitizar(datos.get("proveedor_cliente", "")),
                sanitizar(datos.get("nro_factura", "")),
                self.limpiar_monto(datos.get("neto", 0)),
                self.limpiar_monto(datos.get("iva", 0)),
                self.limpiar_monto(datos.get("total", 0)),
                sanitizar(datos.get("categoria", "")),
                sanitizar(datos.get("comprobante", "")),
                sanitizar(datos.get("file_id", "")),
                sanitizar(datos.get("mes", "")),
            ]

            self._retry_operation(self.ws.update, f"A{fila}:K{fila}", [valores])

            icono = "🟢" if datos.get("tipo_movimiento") == "Ingreso" else "🔴"
            monto_fmt = "{:,}".format(int(datos.get("total", 0))).replace(",", ".")
            return (
                f"✅ Movimiento guardado en Libro Diario:\n"
                f"{icono} {datos.get('tipo_movimiento')} "
                f"por Gs. {monto_fmt}\n"
                f"Categoría: {datos.get('categoria')}"
            )
        except Exception as e:
            logger.error(f"❌ Error registrando movimiento: {e}")
            return f"❌ Hubo un error al guardar en la planilla: {str(e)}"

    def obtener_balance(self) -> dict:
        """
        Calcula el Flujo Neto basado en el Libro Diario completo (o del mes actual).

        Returns:
            A dictionary with 'ingresos', 'gastos', and 'flujo_neto'.

        Raises:
            Exception: If there's an error reading from the sheet.
        """
        try:
            registros = self.ws.get_all_values()[1:]  # Omitir encabezado

            total_ingresos = 0
            total_gastos = 0

            for fila in registros:
                if len(fila) < 7:
                    continue
                tipo = fila[1].strip().lower()
                monto = fila[6].strip()
                try:
                    monto_val = int(monto)
                except ValueError:
                    continue
                if tipo == "ingreso":
                    total_ingresos += monto_val
                elif tipo == "gasto":
                    total_gastos += monto_val

            flujo_neto = total_ingresos - total_gastos

            return {
                "ingresos": total_ingresos,
                "gastos": total_gastos,
                "flujo_neto": flujo_neto,
            }
        except Exception as e:
            logger.error(f"❌ Error al obtener balance: {e}")
            return None

    def preparar_datos_reporte(self, mes=None):
        """
        preparar_datos_reporte method/function.

        Args:
            mes: Description for mes.

        Returns:
            Description of the return value.

        Raises:
            Exception: Description of the exception.
        """
        from logic.pdf_service import DatosReporte

        datos = self.ws.get_all_values()
        if not datos or len(datos) < 2:
            return None, "❌ El Libro Diario está vacío."

        datos[0]
        filas_raw = datos[1:]

        # Filtrar por mes si se especifica (Columna K es índice 10)
        if mes:
            filas_datos = [
                f
                for f in filas_raw
                if len(f) > 10 and f[10].strip().lower() == mes.lower()
            ]
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
        headers_filtrados = [
            "Fecha",
            "Tipo",
            "Detalle",
            "Factura",
            "Monto",
            "Categoría",
        ]
        filas_filtradas = []

        for f in filas_datos:
            f = (f + [""] * 11)[:11]
            tipo = f[1].strip().title()
            monto_str = f[6].strip()

            # Formatear el monto con separador de miles
            monto_val = 0
            try:
                monto_val = int(monto_str)
                monto_fmt = f"Gs. {monto_val:,}".replace(",", ".")
            except ValueError:
                monto_fmt = monto_str

            if tipo.lower() == "ingreso":
                total_ingresos += monto_val
            elif tipo.lower() == "gasto":
                total_gastos += monto_val

            filas_filtradas.append([f[0], tipo, f[2], f[3], monto_fmt, f[7]])

        flujo_neto = total_ingresos - total_gastos

        def gs(n):
            """
            gs method/function.

            Args:
                n: Description for n.

            Returns:
                Description of the return value.

            Raises:
                Exception: Description of the exception.
            """
            return f"Gs. {int(n):,}".replace(",", ".")

        resumen_data = [
            ["Total Ingresos", gs(total_ingresos)],
            ["Total Gastos", f"- {gs(total_gastos)}"],
            ["Flujo Neto", gs(flujo_neto)],
        ]

        nombre_archivo = (
            f"reporte_financiero_{titulo_mes.replace(' ', '_').replace(':', '')}.pdf"
        )

        reporte = DatosReporte(
            titulo="REPORTE FINANCIERO - LIBRO DIARIO",
            subtitulo=titulo_mes,
            encabezados=headers_filtrados,
            filas=filas_filtradas,
            lineas_resumen=resumen_data,
            nombre_archivo=nombre_archivo,
        )
        return reporte, None

# Business logic for Data Schema Abstractions
from repositories.sheets_repository import SheetsRepository
from services.calendar_service import CalendarService
from services.drive_service import DriveService
import uuid

def create_debt(entity: str, concept: str, total_amount: int, quotas: int, first_due_date: str) -> str:
    repo = SheetsRepository()
    debt_id = str(uuid.uuid4())[:8]
    deuda_dict = {
        "id_deuda": debt_id,
        "entidad": entity,
        "concepto": concept,
        "monto_total": total_amount,
        "cuotas": quotas,
        "primer_vencimiento": first_due_date,
        "estado": "activa"
    }
    repo.insert_deuda(deuda_dict)
    CalendarService.create_event(f"Vencimiento {entity}", first_due_date, f"Pago de deuda: {concept}")
    return debt_id

def get_active_debts(debt_id: str = None) -> list[dict]:
    repo = SheetsRepository()
    debts = repo.get_deudas_activas()
    if debt_id:
        debts = [d for d in debts if d.get("id_deuda") == debt_id]
    return debts

def register_payment(debt_id: str, amount: int, date: str) -> None:
    repo = SheetsRepository()
    pago_dict = {
        "id_deuda": debt_id,
        "monto": amount,
        "fecha": date
    }
    repo.insert_pago_abono(pago_dict)
    
    movimiento_dict = {
        "fecha": date,
        "tipo_movimiento": "Gasto",
        "proveedor_cliente": "Pago Deuda",
        "nro_factura": "S/N",
        "neto": amount,
        "iva": 0,
        "total": amount,
        "categoria": "Pago Deuda",
        "comprobante": "S/N",
        "file_id": "",
        "mes": date[5:7] if len(date) >= 7 else ""
    }
    repo.insert_movimiento_diario(movimiento_dict)
    
    # In a real scenario we'd query the event_id for the debt.
    CalendarService.mark_event_completed(f"mock_event_id_for_{debt_id}")

def execute_monthly_closing(month: int, year: int) -> str:
    repo = SheetsRepository()
    # Logic to aggregate data from Libro_Diario
    movimientos = repo.get_movimientos_mes(month, year)
    total_gastos = sum(m.get("total", 0) for m in movimientos if m.get("tipo_movimiento") == "Gasto")
    total_ingresos = sum(m.get("total", 0) for m in movimientos if m.get("tipo_movimiento") == "Ingreso")
    
    cierre_dict = {
        "mes": month,
        "year": year,
        "total_gastos": total_gastos,
        "total_ingresos": total_ingresos,
        "balance": total_ingresos - total_gastos
    }
    repo.insert_cierre_mensual(cierre_dict)
    
    import tempfile
    import os
    # Generate backup
    backup_path = os.path.join(tempfile.gettempdir(), f"backup_{year}_{month}.csv")
    with open(backup_path, "w") as f:
        f.write("mock backup content")
        
    drive_id = DriveService.upload_backup(backup_path)
    return drive_id

def simulate_project(monto: int, meses: int, concept: str = "") -> str:
    repo = SheetsRepository()
    presupuesto = repo.get_presupuesto_base()
    
    # 1. Gastos fijos
    GF = int(presupuesto.get("gastos_fijos", presupuesto.get("Gastos Fijos", 0)))
    
    # 2. Lógica de Ingresos (Fijo vs Promedio Variable)
    I = int(presupuesto.get("ingresos", presupuesto.get("Ingresos", 0)))
    origen_ingreso = "Fijo (Presupuesto Base)"
    
    if I == 0:
        movimientos = repo.get_all_movimientos()
        meses_activos = set()
        total_ingresos_historicos = 0
        
        for m in movimientos:
            tipo = str(m.get("tipo_movimiento", m.get("Tipo Movimiento", ""))).strip().lower()
            if tipo == "ingreso":
                monto_mov = int(m.get("total", m.get("Total", 0)))
                fecha = str(m.get("fecha", m.get("Fecha", ""))).strip()
                mes_str = fecha[:7] if len(fecha) >= 7 else "desc"
                meses_activos.add(mes_str)
                total_ingresos_historicos += monto_mov
                
        cantidad_meses = len(meses_activos)
        if cantidad_meses > 0:
            I = total_ingresos_historicos // cantidad_meses
            origen_ingreso = f"Promedio variable ({cantidad_meses} meses)"
        else:
            I = 1 # Para evitar división por cero en la fórmula
            origen_ingreso = "Sin historial (Asumido 0)"
        
    deudas = repo.get_deudas_activas()
    QD_act = 0
    for d in deudas:
        m_total = int(d.get("monto_total", 0))
        cuotas = int(d.get("cuotas", 1))
        if cuotas > 0:
            QD_act += m_total // cuotas
            
    QD_new = monto // meses if meses > 0 else monto
    
    MLD = I - GF - QD_act - QD_new
    DTI = ((QD_act + QD_new) / I) * 100 if I > 0 else 100
    
    if DTI <= 30 and MLD > 0:
        semaforo = "🟢 Viable"
        mensaje = "Tu salud financiera soporta esta nueva cuota cómodamente."
    elif DTI <= 40 and MLD > 0:
        semaforo = "🟡 Ajustado"
        mensaje = "Puedes pagarlo, pero tu presupuesto quedará muy ajustado para emergencias."
    else:
        semaforo = "🔴 Riesgo"
        mensaje = "Operación de Alto Riesgo. La cuota supera tu capacidad de pago o te deja en saldo rojo."
        
    project_id = str(uuid.uuid4())[:8]
    sim_dict = {
        "id_proyecto": project_id,
        "monto": monto,
        "meses": meses,
        "concepto": concept,
        "cuota_estimada": QD_new,
        "estado": "simulado"
    }
    repo.insert_simulacion(sim_dict)
    
    def gs(num):
        return f"{int(num):,}".replace(",", ".")
        
    return (
        f"📊 *Simulador de Viabilidad Financiera*\n\n"
        f"*Tu Realidad Financiera Actual:*\n"
        f"Ingresos: ₲ {gs(I)} _{origen_ingreso}_\n"
        f"Gastos Fijos: ₲ {gs(GF)}\n"
        f"Cuotas Actuales: ₲ {gs(QD_act)}\n"
        f"--------------------------------\n"
        f"*Tu Proyecto:* {concept if concept else 'N/A'}\n"
        f"*Nueva Cuota Estimada:* ₲ {gs(QD_new)}\n"
        f"*Margen Libre Post-Proyecto (MLD):* ₲ {gs(MLD)}\n\n"
        f"🚦 *Diagnóstico:* {semaforo}\n"
        f"*Endeudamiento Global (DTI):* {DTI:.1f}%\n\n"
        f"_{mensaje}_\n\n"
        f"(Usa `/aprobar_proyecto {project_id}` para registrarlo)"
    )

def approve_project(project_id: str) -> None:
    repo = SheetsRepository()
    repo.update_simulacion_estado(project_id, "aprobado")
    # Transition to Deudas_Maestro could be done here as well by getting simulation details

