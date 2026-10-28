from __future__ import annotations  # noqa: E402

import json  # noqa: E402
import os  # noqa: E402
from typing import Any  # noqa: E402
import sqlite3  # noqa: E402
from datetime import datetime, timedelta, timezone  # noqa: E402
from pathlib import Path  # noqa: E402

from google import genai  # noqa: F401  # noqa: E402
from google.genai import types  # noqa: F401  # noqa: E402
import gspread  # noqa: E402

from dotenv import load_dotenv  # noqa: E402

from logger_config import setup_logger  # noqa: E402
from logic.constants import (  # noqa: E402
    COLUMNAS_DIRECTO,
    COLUMNAS_LETRAS,
    COLUMNAS_NORMAL,
    DIA_LIBRE,
    DIAS_LIMITE_AVISOS,
    DIAS_SEMANA,
    ENCABEZADOS_HORAS,
    ENCABEZADOS_MATERIAS,
    MAX_AVISOS_CALENDAR,
    MESES_ES,
    MONTO_POR_HORA_DEFAULT,
    TIMEZONE,
)

BASE_DIR = Path(__file__).resolve().parents[1]
load_dotenv(BASE_DIR / ".env")

# Zona horaria oficial para operaciones de Gamma Bot
TZ_PARAGUAY = timezone(timedelta(hours=-3))


def get_now_py() -> datetime:
    return datetime.now(TZ_PARAGUAY)


def get_today_py_date() -> datetime:
    now = get_now_py()
    return datetime(now.year, now.month, now.day, tzinfo=TZ_PARAGUAY)


def format_timestamp_py(
    dt: datetime | None = None, formato: str = "%d/%m/%Y %H:%M"
) -> str:
    if dt is None:
        dt = get_now_py()
    return dt.strftime(formato)


import re  # noqa: E402


def safe_int(value, default=0):
    if value is None or value == "":
        return default
    if isinstance(value, (int, float)):
        return int(value)
    if isinstance(value, str):
        # Si tiene un punto y lo que sigue NO son 3 dígitos, se asume decimal y se trunca.
        if "." in value and len(value.split(".")[-1]) != 3:
            value = value.split(".")[0]
        # Limpiar todo lo que no sea dígito o guión negativo
        value_clean = re.sub(r"[^\d-]", "", value).strip()
        if not value_clean:
            return default
        value = value_clean
    try:
        return int(value)
    except (ValueError, TypeError):
        return default


logger = setup_logger("logic")


# Helper to escape potential formula injection in Google Sheets
def sanitize_input(value: str) -> str:
    """Escape leading '=' to prevent formula injection.
    Returns the original value if not a string or does not start with '='.
    """
    if isinstance(value, str) and value.startswith("="):
        return "'" + value
    return value


def obtener_estado_periodos(repo=None, base_path: Path | None = None) -> dict:
    """Consulta y consolida el período activo en asistencia laboral y contabilidad.

    - Período Laboral: Leído de 'periodo_actual.txt' (con fallback a mes calendario vigente en UTC-3).
    - Período Contable: Deducido del último cierre en 'Cierres_Historicos', movimientos de 'Libro_Diario',
      o mes calendario vigente en UTC-3.
    - Sincronizados: Booleano que indica si ambos períodos coinciden.

    Returns:
        dict: {'periodo_laboral': str, 'periodo_contable': str, 'sincronizados': bool}
    """
    ahora = get_now_py()
    mes_actual_cal = f"{MESES_ES[ahora.month - 1]} {ahora.year}"

    if base_path is None:
        base_path = BASE_DIR

    # 1. Período Laboral
    path_txt = base_path / "periodo_actual.txt"
    if path_txt.exists():
        try:
            contenido = path_txt.read_text(encoding="utf-8").strip()
            periodo_laboral = contenido if contenido else mes_actual_cal
        except Exception:
            periodo_laboral = mes_actual_cal
    else:
        periodo_laboral = mes_actual_cal

    # 2. Período Contable
    periodo_contable = None
    if repo is None:
        try:
            from repositories.sheets_repository import SheetsRepository

            repo = SheetsRepository()
        except Exception as e:
            logger.warning(
                f"No se pudo instanciar SheetsRepository para periodo contable: {e}"
            )
            repo = None

    if repo is not None:
        try:
            last_cierre = repo.get_last_cierre_mensual()
            if last_cierre and last_cierre.get("Mes") and last_cierre.get("Anio"):
                mes_cierre = safe_int(last_cierre.get("Mes"))
                anio_cierre = safe_int(last_cierre.get("Anio"))
                if 1 <= mes_cierre <= 12 and anio_cierre > 2000:
                    if mes_cierre == 12:
                        mes_activo = 1
                        anio_activo = anio_cierre + 1
                    else:
                        mes_activo = mes_cierre + 1
                        anio_activo = anio_cierre
                    periodo_contable = f"{MESES_ES[mes_activo - 1]} {anio_activo}"
        except Exception as e:
            logger.warning(
                f"Error obteniendo periodo contable desde Cierres_Historicos: {e}"
            )

        if not periodo_contable:
            try:
                movimientos = repo.get_all_movimientos()
                if movimientos:
                    for m in reversed(movimientos):
                        mes_val = str(m.get("Mes", "")).strip()
                        if "/" in mes_val:
                            partes = mes_val.split("/")
                            m_num = safe_int(partes[0])
                            a_num = safe_int(partes[1])
                            if 1 <= m_num <= 12 and a_num > 2000:
                                periodo_contable = f"{MESES_ES[m_num - 1]} {a_num}"
                                break
                        elif any(
                            nom.lower() in mes_val.lower() for nom in MESES_ES
                        ) and any(c.isdigit() for c in mes_val):
                            periodo_contable = mes_val
                            break

                        fecha_val = str(m.get("Fecha", "")).strip()
                        if "/" in fecha_val:
                            f_partes = fecha_val.split("/")
                            if len(f_partes) == 3:
                                m_num = safe_int(f_partes[1])
                                a_num = safe_int(f_partes[2])
                                if 1 <= m_num <= 12 and a_num > 2000:
                                    periodo_contable = f"{MESES_ES[m_num - 1]} {a_num}"
                                    break
            except Exception as e:
                logger.warning(
                    f"Error obteniendo periodo contable desde Libro_Diario: {e}"
                )

    if not periodo_contable:
        periodo_contable = mes_actual_cal

    def _normalizar(p: str) -> str:
        return p.strip().lower().replace("septiembre", "setiembre")

    sincronizados = _normalizar(periodo_laboral) == _normalizar(periodo_contable)

    return {
        "periodo_laboral": periodo_laboral,
        "periodo_contable": periodo_contable,
        "sincronizados": sincronizados,
    }


class ConexionSheets:
    """
    Class ConexionSheets.
    """

    _cliente = None
    _servicio_calendar = None

    @classmethod
    def obtener_cliente(cls) -> "gspread.Client | None":
        """
        obtener_cliente method/function.

        Returns:
            Description of the return value.

        Raises:
            Exception: Description of the exception.
        """
        if cls._cliente is None:
            scopes = [
                "https://www.googleapis.com/auth/spreadsheets",
                "https://www.googleapis.com/auth/drive",
            ]
            path_json = BASE_DIR / "credentials.json"
            if not path_json.exists():
                logger.warning(
                    "⚠️ credentials.json not found; Google services will be unavailable."
                )
                return None
            import gspread
            from google.oauth2.service_account import Credentials
            from google.auth.exceptions import RefreshError

            try:
                credenciales = Credentials.from_service_account_file(
                    str(path_json), scopes=scopes
                )
                cls._cliente = gspread.authorize(credenciales)
                logger.info(
                    "🔌 Nueva conexión a Google Sheets establecida exitosamente (Singleton)."
                )
            except RefreshError as e:
                logger.error(
                    f"❌ Error de autenticación en Google Sheets: credenciales inválidas ({e})."
                )
                return None
            except Exception as e:
                logger.error(f"❌ Error al autorizar Google Sheets: {e}")
                return None
        return cls._cliente

    @classmethod
    def obtener_servicio_calendar(cls) -> "Any | None":
        """
        obtener_servicio_calendar method/function.

        Returns:
            Description of the return value.

        Raises:
            Exception: Description of the exception.
        """
        if cls._servicio_calendar is None:
            scopes = ["https://www.googleapis.com/auth/calendar"]
            path_json = BASE_DIR / "credentials.json"
            from google.oauth2.service_account import Credentials
            from googleapiclient.discovery import build

            credenciales = Credentials.from_service_account_file(
                path_json, scopes=scopes
            )
            cls._servicio_calendar = build("calendar", "v3", credentials=credenciales)
            logger.info(
                "📅 Nueva conexión a Google Calendar establecida exitosamente (Singleton)."
            )
        return cls._servicio_calendar


class AgenteAutonomoHoras:
    """
    Class AgenteAutonomoHoras.
    """

    MONTO_POR_HORA = int(MONTO_POR_HORA_DEFAULT)

    def __init__(
        self, spreadsheet_id: str | None = None, mes: str | None = None
    ) -> None:
        """__init__ method/function.

        Args:
            spreadsheet_id: Description for spreadsheet_id.
            mes: Description for mes.

        Returns:
            Description of the return value.

        Raises:
            Exception: Description of the exception.
        """
        self.mes = mes
        self.spreadsheet_id = spreadsheet_id or os.getenv("SPREADSHEET_ID", "")
        self._wb = None
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
            import gspread

            base_path = BASE_DIR
            path_txt = base_path / "periodo_actual.txt"
            # Ensure the directory exists
            path_txt.parent.mkdir(parents=True, exist_ok=True)
            if not path_txt.exists():
                if self.mes:
                    nombre_inicial = self.mes
                else:
                    meses_es = [
                        "Enero",
                        "Febrero",
                        "Marzo",
                        "Abril",
                        "Mayo",
                        "Junio",
                        "Julio",
                        "Agosto",
                        "Setiembre",
                        "Octubre",
                        "Noviembre",
                        "Diciembre",
                    ]
                    ahora = get_now_py()
                    nombre_inicial = f"{meses_es[ahora.month - 1]} {ahora.year}"
                path_txt.write_text(nombre_inicial, encoding="utf-8")
            nombre_hoja = path_txt.read_text(encoding="utf-8").strip()

            try:
                self._ws = self.wb.worksheet(nombre_hoja)
            except gspread.exceptions.WorksheetNotFound:
                logger.warning(
                    f"⚠️ La hoja '{nombre_hoja}' no existe. Creándola automáticamente."
                )
                self._ws = self.wb.add_worksheet(
                    title=nombre_hoja, rows="60", cols="10"
                )
                encabezados = ENCABEZADOS_HORAS
                self._ws.update("A1:G1", [encabezados])

        return self._ws

    def fin_de(self):
        """
        fin_de method/function.

        Returns:
            Description of the return value.

        Raises:
            Exception: Description of the exception.
        """
        ahora = get_now_py()
        dia = DIAS_SEMANA[ahora.weekday()]
        free_day = DIA_LIBRE

        if dia != free_day:
            return None
        else:
            return 1

    def _cargar_hoja_activa(self):
        """
        _cargar_hoja_activa method/function.

        Returns:
            Description of the return value.

        Raises:
            Exception: Description of the exception.
        """
        self._ws = None  # Force reload next time ws is accessed
        _ = self.ws

    def _obtener_o_crear_fila_hoy(self):
        """Busca la fecha de hoy en la hoja del período activo actual.

        Returns:
            int or None: The row number corresponding to today's date, or None if the limit is reached.

        Raises:
            Exception: If an error occurs communicating with Google Sheets.
        """
        ahora = get_now_py()
        hoy_str = ahora.strftime("%d/%m/%Y")

        self._cargar_hoja_activa()

        nombre_dia = DIAS_SEMANA[ahora.weekday()]

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
                self.ws.update(
                    f"A{primera_fila_vacia}:B{primera_fila_vacia}",
                    [[nombre_dia, hoy_str]],
                    value_input_option="USER_ENTERED",
                )

                # Fórmula matemática dinámica
                formula_horas = (
                    f'=SI(VALOR(D{primera_fila_vacia})<>""; '
                    f"(VALOR(D{primera_fila_vacia})-VALOR(C{primera_fila_vacia}))"
                    f"+(VALOR(F{primera_fila_vacia})-VALOR(E{primera_fila_vacia})); "
                    f"VALOR(F{primera_fila_vacia})-VALOR(C{primera_fila_vacia})) * 24"
                )

                self.ws.update(
                    f"G{primera_fila_vacia}",
                    [[formula_horas]],
                    value_input_option="USER_ENTERED",
                )
                return primera_fila_vacia
        return None

    def ejecutar_marcado_para_bot(self, modo="normal"):
        """
        ejecutar_marcado_para_bot method/function.

        Args:
            modo: Description for modo.

        Returns:
            Description of the return value.

        Raises:
            Exception: Description of the exception.
        """
        fila = self._obtener_o_crear_fila_hoy()
        if not fila:
            msg = "❌ Límite de filas alcanzado o error en fecha."
            logger.info(msg)
            return msg

        hora_ahora = get_now_py().strftime("%H:%M")

        if hasattr(self, "fin_de") and self.fin_de():
            log_msg = f"{hora_ahora} Dia libre, no hay marcas que hacer!!!"
            logger.info(log_msg)
            return "ℹ️ Hoy es tu día libre, no es necesario registrar marcas."

        columnas = COLUMNAS_DIRECTO if modo == "directo" else COLUMNAS_NORMAL

        valores_fila = self.ws.row_values(fila)

        def celda_vacia(col_index):
            """
            celda_vacia method/function.

            Args:
                col_index: Description for col_index.

            Returns:
                Description of the return value.

            Raises:
                Exception: Description of the exception.
            """
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
                letra_celda = COLUMNAS_LETRAS[col_index]
                self.ws.update(
                    f"{letra_celda}{fila}",
                    [[hora_ahora]],
                    value_input_option="USER_ENTERED",
                )

                log_msg = f"Marcado [{modo}] {nombre}: {hora_ahora} en fila {fila}"
                logger.info(log_msg)
                return f"✅ *{nombre}* registrado a las {hora_ahora}."

        return "ℹ️ Ya completaste todos los registros of hoy."

    def ejecutar_cierre_periodo_manual(self):
        """
        ejecutar_cierre_periodo_manual method/function.

        Returns:
            Description of the return value.

        Raises:
            Exception: Description of the exception.
        """
        base_path = BASE_DIR
        path_txt = base_path / "periodo_actual.txt"

        if path_txt.exists():
            with open(path_txt, "r", encoding="utf-8") as f:
                hoja_actual = f.read().strip()
        else:
            meses_es = [
                "Enero",
                "Febrero",
                "Marzo",
                "Abril",
                "Mayo",
                "Junio",
                "Julio",
                "Agosto",
                "Setiembre",
                "Octubre",
                "Noviembre",
                "Diciembre",
            ]
            ahora = get_now_py()
            hoja_actual = f"{meses_es[ahora.month - 1]} {ahora.year}"

        meses = [
            "Enero",
            "Febrero",
            "Marzo",
            "Abril",
            "Mayo",
            "Junio",
            "Julio",
            "Agosto",
            "Septiembre",
            "Octubre",
            "Noviembre",
            "Diciembre",
        ]

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
            ahora = get_now_py()
            nombre_hoja_nueva = f"Periodo_{ahora.strftime('%d_%m_%Y')}"

        try:
            # ── Verificar si la hoja destino ya existe ────────────────────────
            titulos_existentes = [h.title for h in self.wb.worksheets()]
            hoja_ya_existia = nombre_hoja_nueva in titulos_existentes

            if hoja_ya_existia:
                # La hoja ya fue creada (cierre previo parcial): la reutilizamos
                nueva_hoja = self.wb.worksheet(nombre_hoja_nueva)
                logger.error(
                    f"⚠️ La hoja '{nombre_hoja_nueva}' ya existía. Reutilizando sin recrear encabezados."
                )
                mensaje_creacion = (
                    f"⚠️ La pestaña *{nombre_hoja_nueva}* ya existía y fue reutilizada."
                )
            else:
                # Flujo normal: crear hoja nueva con encabezados
                nueva_hoja = self.wb.add_worksheet(
                    title=nombre_hoja_nueva, rows="60", cols="10"
                )
                encabezados = ENCABEZADOS_HORAS
                nueva_hoja.update("A1:G1", [encabezados])
                mensaje_creacion = f"Se ha creado la pestaña *{nombre_hoja_nueva}* con sus encabezados."

            # ── Siempre actualizar el período activo ──────────────────────────
            with open(path_txt, "w", encoding="utf-8") as f:
                f.write(nombre_hoja_nueva)

            logger.info(
                f"🔄 CIERRE PROCESADO: Finalizado '{hoja_actual}'. Activo '{nombre_hoja_nueva}'"
            )
            return (
                f"✅ Cierre de período exitoso.\n\n"
                f"{mensaje_creacion} "
                f"A partir de ahora, todas las marcaciones se registrarán ahí."
            )

        except Exception as e:
            # ── Si falla algo inesperado, aún así intentamos salvar el período ─
            logger.error(f"❌ Error inesperado en cierre: {e}")
            return f"❌ Error al ejecutar el cierre: {e}"

    @staticmethod
    def _parsear_horas_a_decimal(valor_str: str) -> float:
        """
        _parsear_horas_a_decimal method/function.

        Args:
            valor_str: Description for valor_str.

        Returns:
            Description of the return value.

        Raises:
            Exception: Description of the exception.
        """
        valor_str = str(valor_str).strip().replace(",", ".")
        if not valor_str or "horas" in valor_str.lower():
            return 0.0
        try:
            if ":" in valor_str:
                partes = valor_str.split(":")
                return int(partes[0]) + int(partes[1]) / 60
            valor_float = float(valor_str)
            return valor_float
        except (ValueError, IndexError):
            return 0.0

    def preparar_datos_reporte(
        self,
        nombre_hoja=None,
        descuento=0,
        incluir_iva=True,
        saldo_anterior=0,
    ):
        """Prepara los datos estructurados para compilar los reportes laboral en PDF y Excel.

        Calcula el cuadro resumen con: mes, hora, por Horas, IVA 10%, INCLUIDO,
        y opcionalmente SALDO ANTERIOR o Descuento si es distinto de cero, finalizando en FACTURA.
        """
        from logic.pdf_service import DatosReporte

        hojas = self.wb.worksheets()
        if nombre_hoja:
            hoja = self.wb.worksheet(nombre_hoja)
        else:
            if len(hojas) >= 2:
                hoja = hojas[-2]
            elif len(hojas) == 1:
                hoja = hojas[0]
            else:
                return None, "❌ No hay hoja de cierre disponible todavía."

        nombre_periodo = hoja.title
        datos = hoja.get_all_values()
        if not datos or len(datos) < 2:
            return None, "❌ La hoja de cierre está vacía."

        headers = datos[0]
        filas_raw = datos[1:]
        # Filtrar filas de datos excluyendo filas del cuadro resumen previo si existieran
        filas_datos = [
            f
            for f in filas_raw
            if any(c.strip() for c in f)
            and f[0].strip().lower() != "resumen"
            and f[0].strip().lower() != "mes"
        ]

        col_horas = next(
            (i for i, h in enumerate(headers) if "horas" in h.lower()), None
        )
        if col_horas is None:
            return None, "❌ No se encontró columna de horas. Verificá el encabezado."

        total_decimal = sum(
            self._parsear_horas_a_decimal(f[col_horas])
            for f in filas_datos
            if col_horas < len(f)
        )
        total_decimal_redondeado = round(total_decimal, 1)

        monto_por_hora = int(float(os.getenv("MONTO_POR_HORA", MONTO_POR_HORA_DEFAULT)))
        monto_por_horas = int(round(total_decimal * monto_por_hora))

        if incluir_iva:
            monto_iva = int(round(monto_por_horas * 0.10))
            subtotal_incluido = monto_por_horas + monto_iva
        else:
            monto_iva = 0
            subtotal_incluido = monto_por_horas

        monto_saldo_anterior = int(round(float(saldo_anterior or 0)))
        monto_descuento = int(round(float(descuento or 0)))

        if monto_saldo_anterior > 0:
            total_factura = subtotal_incluido + monto_saldo_anterior
        elif monto_descuento > 0:
            total_factura = subtotal_incluido - monto_descuento
        else:
            total_factura = subtotal_incluido

        def fmt_m(val: int | float) -> str:
            return f"${int(round(val)):,}"

        resumen_data = [
            ["mes", f"{total_decimal_redondeado:.1f}"],
            ["hora", fmt_m(monto_por_hora)],
            ["por Horas", fmt_m(monto_por_horas)],
            ["IVA 10%", fmt_m(monto_iva)],
            ["INCLUIDO", fmt_m(subtotal_incluido)],
        ]

        if monto_saldo_anterior > 0:
            resumen_data.append(["SALDO ANTERIOR", fmt_m(monto_saldo_anterior)])
        elif monto_descuento > 0:
            resumen_data.append(["Descuento", f"-{fmt_m(monto_descuento)}"])

        resumen_data.append(["FACTURA", fmt_m(total_factura)])

        nombre_archivo = (
            f"reporte_horas_{nombre_periodo.replace(' ', '_').replace('/', '-')}.pdf"
        )

        reporte = DatosReporte(
            titulo="REPORTE DE ASISTENCIA Y HORAS",
            subtitulo=nombre_periodo,
            encabezados=headers,
            filas=filas_datos,
            lineas_resumen=resumen_data,
            nombre_archivo=nombre_archivo,
        )
        # Inyectar metadatos enriquecidos para generación de Excel y analíticas
        reporte.resumen_calculado = {
            "mes": total_decimal_redondeado,
            "hora": monto_por_hora,
            "por_horas": monto_por_horas,
            "iva_10": monto_iva,
            "incluido": subtotal_incluido,
            "saldo_anterior": monto_saldo_anterior,
            "descuento": monto_descuento,
            "factura": total_factura,
        }
        return reporte, None

    def escribir_cuadro_resumen_en_sheet(
        self,
        nombre_hoja=None,
        saldo_anterior=0,
        descuento=0,
        incluir_iva=True,
    ):
        """Escribe el cuadro resumen de dos columnas al pie de la hoja en Google Sheets."""
        try:
            if nombre_hoja:
                hoja = self.wb.worksheet(nombre_hoja)
            else:
                hoja = self.ws

            datos = hoja.get_all_values()
            if not datos:
                return False, "❌ La hoja está vacía."

            ultima_fila = len(datos)
            for idx in range(len(datos) - 1, -1, -1):
                fila_vals = datos[idx]
                if len(fila_vals) > 0 and fila_vals[0].strip().lower() == "resumen":
                    ultima_fila = idx
                    break
                elif any(c.strip() for c in fila_vals):
                    ultima_fila = idx + 1
                    break

            headers = datos[0]
            col_horas = next(
                (i for i, h in enumerate(headers) if "horas" in h.lower()), 6
            )

            filas_datos = [
                f
                for f in datos[1:ultima_fila]
                if any(c.strip() for c in f)
                and f[0].strip().lower() != "resumen"
                and f[0].strip().lower() != "mes"
            ]

            total_decimal = sum(
                self._parsear_horas_a_decimal(f[col_horas])
                for f in filas_datos
                if col_horas < len(f)
            )
            total_decimal_redondeado = round(total_decimal, 1)

            monto_por_hora = int(
                float(os.getenv("MONTO_POR_HORA", MONTO_POR_HORA_DEFAULT))
            )
            monto_por_horas = int(round(total_decimal * monto_por_hora))
            monto_iva = int(round(monto_por_horas * 0.10)) if incluir_iva else 0
            subtotal_incluido = monto_por_horas + monto_iva

            monto_saldo_anterior = int(round(float(saldo_anterior or 0)))
            monto_descuento = int(round(float(descuento or 0)))

            if monto_saldo_anterior > 0:
                total_factura = subtotal_incluido + monto_saldo_anterior
            elif monto_descuento > 0:
                total_factura = subtotal_incluido - monto_descuento
            else:
                total_factura = subtotal_incluido

            def fmt_m(val: int | float) -> str:
                return f"${int(round(val)):,}"

            filas_resumen = [
                ["Resumen", "Cantidades"],
                ["mes", f"{total_decimal_redondeado:.1f}"],
                ["hora", fmt_m(monto_por_hora)],
                ["por Horas", fmt_m(monto_por_horas)],
                ["IVA 10%", fmt_m(monto_iva)],
                ["INCLUIDO", fmt_m(subtotal_incluido)],
            ]

            if monto_saldo_anterior > 0:
                filas_resumen.append(["SALDO ANTERIOR", fmt_m(monto_saldo_anterior)])
            elif monto_descuento > 0:
                filas_resumen.append(["Descuento", f"-{fmt_m(monto_descuento)}"])

            filas_resumen.append(["FACTURA", fmt_m(total_factura)])

            fila_inicio = (
                ultima_fila + 2 if ultima_fila == len(datos) else ultima_fila + 1
            )
            fila_fin = fila_inicio + len(filas_resumen) - 1

            hoja.update(
                f"A{fila_inicio}:B{fila_fin}",
                filas_resumen,
                value_input_option="USER_ENTERED",
            )
            return (
                True,
                f"✅ Cuadro resumen escrito en A{fila_inicio}:B{fila_fin}",
            )
        except Exception as e:
            logger.error(f"Error escribiendo cuadro resumen en sheet: {e}")
            return False, f"❌ Error escribiendo resumen en Google Sheets: {e}"

    @staticmethod
    def formatear_horas_decimal(decimal_val: float) -> str:
        """Convierte un valor decimal de horas a formato legible 'Xh Ym'.

        Args:
            decimal_val: Cantidad de horas en formato decimal (positivo o negativo).

        Returns:
            str: Representación legible ej. '107h 18m', '-1h 25m' o '0h 00m'.
        """
        es_negativo = decimal_val < 0
        val_abs = abs(decimal_val)
        horas = int(val_abs)
        minutos = int(round((val_abs - horas) * 60))
        if minutos >= 60:
            horas += 1
            minutos = 0
        if horas == 0 and minutos == 0:
            return "0h 00m"
        signo = "-" if es_negativo else ""
        return f"{signo}{horas}h {minutos:02d}m"

    def calcular_analiticas_asistencia(self, nombre_hoja: str | None = None):
        """Calcula métricas analíticas de asistencia laboral para el período activo o especificado.

        Procesa las jornadas con horas registradas (> 0):
        - Horas perdidas (< 8h estándar por jornada laboral trabajada)
        - Horas extras (> 8h estándar)
        - Balance neto (total horas - días trabajados * 8h)
        - Total acumulado MTD (horas y dinero devengado)

        Args:
            nombre_hoja: Nombre de la hoja/período a analizar. Si es None, usa la hoja activa.

        Returns:
            tuple[dict | None, str | None]: (analiticas_dict, error_msg)
        """
        try:
            if nombre_hoja:
                hoja = self.wb.worksheet(nombre_hoja)
            else:
                hoja = self.ws
        except Exception as e:
            logger.error(f"Error accediendo a la hoja de horas: {e}")
            return None, f"❌ No se pudo acceder a la hoja de horas: {e}"

        nombre_periodo = hoja.title
        datos = hoja.get_all_values()
        if not datos or len(datos) < 1:
            return None, "❌ La hoja de horas está vacía."

        headers = datos[0]
        col_horas = next(
            (i for i, h in enumerate(headers) if "horas" in h.lower()), None
        )
        if col_horas is None:
            return None, "❌ No se encontró la columna de horas en los encabezados."

        filas_raw = datos[1:]
        conceptos_excluidos = {
            "resumen",
            "mes",
            "hora",
            "por horas",
            "iva 10%",
            "incluido",
            "saldo anterior",
            "descuento",
            "factura",
        }
        filas_datos = [
            f
            for f in filas_raw
            if any(c.strip() for c in f)
            and f[0].strip().lower() not in conceptos_excluidos
        ]

        jornadas_horas: list[float] = []
        for f in filas_datos:
            if col_horas < len(f):
                val_h = self._parsear_horas_a_decimal(f[col_horas])
                if val_h > 0.0:
                    jornadas_horas.append(val_h)

        dias_trabajados = len(jornadas_horas)
        total_horas = sum(jornadas_horas)

        horas_perdidas = 0.0
        horas_extras = 0.0
        for h in jornadas_horas:
            if h < 8.0:
                horas_perdidas += 8.0 - h
            elif h > 8.0:
                horas_extras += h - 8.0

        balance_neto = total_horas - (dias_trabajados * 8.0)
        promedio_dia = (
            round(total_horas / dias_trabajados, 2) if dias_trabajados > 0 else 0.0
        )

        monto_por_hora = int(float(os.getenv("MONTO_POR_HORA", MONTO_POR_HORA_DEFAULT)))
        salario_acumulado_gs = int(round(total_horas * monto_por_hora))

        analiticas = {
            "periodo": nombre_periodo,
            "monto_por_hora": monto_por_hora,
            "dias_trabajados": dias_trabajados,
            "total_horas_decimal": round(total_horas, 2),
            "total_horas_formato": self.formatear_horas_decimal(total_horas),
            "salario_acumulado_gs": salario_acumulado_gs,
            "horas_perdidas_decimal": round(horas_perdidas, 2),
            "horas_extras_decimal": round(horas_extras, 2),
            "balance_neto_decimal": round(balance_neto, 2),
            "horas_perdidas_formato": self.formatear_horas_decimal(horas_perdidas),
            "horas_extras_formato": self.formatear_horas_decimal(horas_extras),
            "balance_neto_formato": self.formatear_horas_decimal(balance_neto),
            "promedio_horas_por_dia": promedio_dia,
        }
        return analiticas, None

    def obtener_estado_periodos(self, repo=None, base_path: Path | None = None) -> dict:
        """Consulta el estado consolidado de períodos laboral y contable."""
        return obtener_estado_periodos(repo=repo, base_path=base_path)

    def guardar_aviso_calendar(self, datos_evento: dict) -> str:
        """
        Guarda el aviso interpretado por Gemini directamente en Google Calendar.

        Args:
            datos_evento: Dictionary with event details (titulo, fecha, hora).

        Returns:
            str: A confirmation message or error message.

        Raises:
            Exception: If an error occurs communicating with Google Calendar.
        """
        calendar_id = os.getenv("CALENDAR_ID")
        if not calendar_id:
            return "❌ Error: Falta configurar CALENDAR_ID en tu archivo .env."

        try:
            servicio = ConexionSheets.obtener_servicio_calendar()
            fecha_hora_str = f"{datos_evento['fecha']} {datos_evento['hora']}"
            try:
                dt_inicio = datetime.strptime(fecha_hora_str, "%d/%m/%Y %H:%M")
            except ValueError:
                return "❌ Error: La IA no devolvió un formato de fecha válido. Por favor, intenta de nuevo."
            dt_inicio = dt_inicio.replace(tzinfo=TZ_PARAGUAY)
            dt_fin = dt_inicio + timedelta(hours=1)

            reminders_overrides = datos_evento.get(
                "reminders",
                [
                    {"method": "popup", "minutes": 24 * 60},
                    {"method": "popup", "minutes": 2 * 60},
                    {"method": "popup", "minutes": 60},
                    {"method": "popup", "minutes": 15},
                ],
            )

            evento = {
                "summary": datos_evento["titulo"],
                "start": {
                    "dateTime": dt_inicio.isoformat(),
                    "timeZone": TIMEZONE,
                },
                "end": {
                    "dateTime": dt_fin.isoformat(),
                    "timeZone": TIMEZONE,
                },
                "reminders": {
                    "useDefault": False,
                    "overrides": reminders_overrides,
                },
            }

            servicio.events().insert(calendarId=calendar_id, body=evento).execute()
            logger.info(
                f"📅 Nuevo aviso guardado en Calendar: '{datos_evento['titulo']}'"
            )

            return (
                f"✅ *¡Aviso guardado en Google Calendar!*\n\n"
                f"📌 *{datos_evento['titulo']}*\n"
                f"📅 Agendado: {datos_evento['fecha']} a las {datos_evento['hora']} hs.\n\n"
                f"🔔 _Recibirás notificaciones nativas en tu teléfono._"
            )
        except Exception as e:
            logger.error(f"❌ Error al guardar en Google Calendar: {e}")
            return f"❌ Error interno de Google Calendar: {str(e)}"

    def obtener_lista_avisos_calendar(self):
        """Devuelve la lista de los próximos eventos desde Google Calendar.

        Returns:
            list: List of dictionaries containing formatted event data.

        Raises:
            Exception: If an error occurs fetching events from Calendar API.
        """
        calendar_id = os.getenv("CALENDAR_ID")
        if not calendar_id:
            return []

        try:
            servicio = ConexionSheets.obtener_servicio_calendar()
            ahora = get_now_py()
            ahora_iso = ahora.isoformat()

            # 🆕 Limitar la búsqueda
            limite_mes = ahora + timedelta(days=DIAS_LIMITE_AVISOS)
            limite_iso = limite_mes.isoformat()

            eventos_result = (
                servicio.events()
                .list(
                    calendarId=calendar_id,
                    timeMin=ahora_iso,
                    timeMax=limite_iso,
                    maxResults=MAX_AVISOS_CALENDAR,
                    singleEvents=True,
                    orderBy="startTime",
                )
                .execute()
            )

            eventos = eventos_result.get("items", [])

            avisos_formateados = []
            for evento in eventos:
                start = evento["start"].get("dateTime", evento["start"].get("date"))
                # Formatear la fecha para que sea legible en Telegram
                try:
                    dt = datetime.fromisoformat(start)
                    fecha_str = dt.strftime("%d/%m/%Y %H:%M")
                except Exception as e:
                    logger.error(f"Error parsing event start date: {e}")
                    fecha_str = start

                avisos_formateados.append(
                    {
                        "id": evento["id"],
                        "titulo": evento.get("summary", "Sin título"),
                        "fecha_evento": fecha_str,
                    }
                )
            return avisos_formateados
        except Exception as e:
            logger.error(f"❌ Error al obtener eventos de Calendar: {e}")
            return []

    def eliminar_aviso_calendar(self, event_id: str):
        """Elimina un evento de Google Calendar por su ID.

        Args:
            event_id (str): The Google Calendar event ID to delete.

        Returns:
            bool or None: True if successful, None otherwise.

        Raises:
            Exception: If an error occurs during deletion.
        """
        calendar_id = os.getenv("CALENDAR_ID")
        if not calendar_id:
            return None

        try:
            servicio = ConexionSheets.obtener_servicio_calendar()
            servicio.events().delete(calendarId=calendar_id, eventId=event_id).execute()
            return True
        except Exception as e:
            logger.error(f"❌ Error al eliminar evento en Calendar: {e}")
            return None

    def obtener_nombres_hojas(self, limite: int = 6) -> list:
        """
        Devuelve los títulos de las últimas `limite` hojas del spreadsheet,
        excluyendo la hoja activa actual (donde se están registrando las marcas).
        Se usa para el comando /reporte para que el usuario elija el período.

        Args:
            limite (int, optional): The maximum number of sheet names to retrieve. Defaults to 6.

        Returns:
            list: A list of string sheet titles.

        Raises:
            Exception: If an error occurs while fetching sheet names.
        """
        try:
            base_path = BASE_DIR
            path_txt = base_path / "periodo_actual.txt"
            hoja_activa = ""
            if path_txt.exists():
                with open(path_txt, "r", encoding="utf-8") as f:
                    hoja_activa = f.read().strip()

            hojas = self.wb.worksheets()
            nombres = [h.title for h in hojas if h.title != hoja_activa]
            return nombres[-limite:][::-1]  # Las más recientes primero
        except Exception as e:
            logger.error(f"❌ Error en obtener_nombres_hojas: {e}")
            return []


class AgenteAsistenciaMaterias:
    """
    Class AgenteAsistenciaMaterias.
    """

    SPREADSHEET_ID = "1VJe98WHoL5U7aDiGLIw55ZHnG-M6bAuLmIZx9LNbWnY"

    def __init__(self):
        """
        __init__ method/function.

        Returns:
            Description of the return value.

        Raises:
            Exception: Description of the exception.
        """
        self._wb = None
        self._horarios_materias = None

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
            self._wb = self.cliente.open_by_key(self.SPREADSHEET_ID)
        return self._wb

    @property
    def HORARIOS_MATERIAS(self):
        """
        HORARIOS_MATERIAS method/function.

        Returns:
            Description of the return value.

        Raises:
            Exception: Description of the exception.
        """
        if self._horarios_materias is None:
            self._cargar_horarios()
        return self._horarios_materias

    def _normalizar_hora(self, hora_str: str) -> str:
        """
        _normalizar_hora method/function.

        Args:
            hora_str: Description for hora_str.

        Returns:
            Description of the return value.

        Raises:
            Exception: Description of the exception.
        """
        if not hora_str:
            return ""
        hora_str = str(hora_str).replace("\u202f", " ").strip().lower()

        es_pm = "p" in hora_str
        es_am = "a" in hora_str

        import re

        match = re.search(r"(\d{1,2}):(\d{2})", hora_str)
        if not match:
            return hora_str[:5]

        hh, mm = match.groups()
        hh_int = int(hh)

        if es_pm and hh_int < 12:
            hh_int += 12
        elif es_am and hh_int == 12:
            hh_int = 0

        return f"{hh_int:02d}:{mm}"

    def _cargar_horarios(self):
        """
        _cargar_horarios method/function.

        Returns:
            Description of the return value.

        Raises:
            Exception: Description of the exception.
        """
        try:
            ws = self.wb.worksheet("Config_bot")
            filas = ws.get_all_values()[1:]  # Ignorar encabezados
            self._horarios_materias = {}
            for fila in filas:
                if len(fila) < 6:
                    continue
                materia = str(fila[0]).strip()
                dia = str(fila[1]).strip()
                inicio_teo = str(fila[2]).strip()
                fin_teo = str(fila[3]).strip()
                inicio_prac = str(fila[4]).strip()
                fin_prac = str(fila[5]).strip()

                # Ignorar filas vacías o sin horarios completos
                if (
                    not materia
                    or not dia
                    or not inicio_teo
                    or not fin_teo
                    or not inicio_prac
                    or not fin_prac
                ):
                    continue

                # Asegurar formato HH:MM (convertir de AM/PM a 24h si es necesario)
                inicio_teo = self._normalizar_hora(inicio_teo)
                fin_teo = self._normalizar_hora(fin_teo)
                inicio_prac = self._normalizar_hora(inicio_prac)
                fin_prac = self._normalizar_hora(fin_prac)

                # Tratar caracteres extraños en los días (ej. tildes) estandarizando a los de Python
                dia = dia.capitalize()
                if "bad" in dia.lower():
                    dia = "Sábado"
                if "rcol" in dia.lower():
                    dia = "Miércoles"

                self._horarios_materias[materia] = {
                    "dia": dia,
                    "teoria": (inicio_teo, fin_teo),
                    "practica": (inicio_prac, fin_prac),
                }
            logger.info(
                f"✅ Horarios cargados desde Config_bot: {len(self._horarios_materias)} materias."
            )
        except Exception as e:
            logger.error(f"❌ Error al cargar horarios desde Config_bot: {e}")
            # IMPORTANTE: resetear a None (no a {}) para que el próximo intento
            # vuelva a cargar desde Sheets en lugar de quedar con caché vacía permanente.
            self._horarios_materias = None

    def obtener_materia_actual(self, ahora):
        """
        obtener_materia_actual method/function.

        Args:
            ahora: Description for ahora.

        Returns:
            Description of the return value.

        Raises:
            Exception: Description of the exception.
        """
        dia_actual = DIAS_SEMANA[ahora.weekday()]
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
        """
        marcar_asistencia method/function.

        Returns:
            Description of the return value.

        Raises:
            Exception: Description of the exception.
        """
        try:
            ahora = get_now_py()
            materia, tipo = self.obtener_materia_actual(ahora)
            if not materia:
                return (
                    "ℹ️ No hay ninguna clase en curso en este momento según el horario."
                )

            # Verificar si existe la hoja de la materia, si no, crearla
            titulos_existentes = [h.title for h in self.wb.worksheets()]
            if materia not in titulos_existentes:
                ws = self.wb.add_worksheet(title=materia, rows="100", cols="6")
                ws.update("A1:F1", [ENCABEZADOS_MATERIAS])
            else:
                ws = self.wb.worksheet(materia)

            hoy_str = ahora.strftime("%d/%m/%Y")
            dia_actual = DIAS_SEMANA[ahora.weekday()]

            fechas_col = ws.col_values(2)
            fila = None
            for i, fecha in enumerate(fechas_col):
                if fecha == hoy_str:
                    fila = i + 1
                    break

            if fila is None:
                fila = len(fechas_col) + 1
                if fila == 1:
                    ws.update("A1:F1", [ENCABEZADOS_MATERIAS])
                    fila = 2
                ws.update(f"A{fila}:B{fila}", [[dia_actual, hoy_str]])

            hora_str = ahora.strftime("%H:%M")
            if tipo == "teoria":
                ws.update(f"C{fila}:D{fila}", [[hora_str, "x"]])
            else:
                ws.update(f"E{fila}:F{fila}", [[hora_str, "x"]])

            log_msg = f"Asistencia marcada para {materia} ({tipo}) a las {hora_str} en fila {fila}"
            logger.info(log_msg)
            return f"✅ Asistencia de *{materia}* ({tipo}) registrada exitosamente a las {hora_str}."

        except Exception as e:
            logger.error(f"❌ Error marcando materia: {e}")
            return f"❌ Error interno al marcar asistencia: {str(e)}"


class EstadoGestor:
    """Clase para guardar y recuperar estado temporal usando SQLite.

    Diseñada para soportar múltiples workers en PythonAnywhere.
    """

    PATH_DB = BASE_DIR / "estado_temporal.db"

    @classmethod
    def _get_conn(cls):
        """
        _get_conn method/function.

        Returns:
            Description of the return value.

        Raises:
            Exception: Description of the exception.
        """
        conn = sqlite3.connect(cls.PATH_DB, timeout=5.0)
        conn.execute(
            "CREATE TABLE IF NOT EXISTS estado (clave TEXT PRIMARY KEY, valor TEXT)"
        )
        return conn

    @classmethod
    def set(cls, clave, valor):
        """
        set method/function.

        Args:
            clave: Description for clave.
            valor: Description for valor.

        Returns:
            Description of the return value.

        Raises:
            Exception: Description of the exception.
        """
        conn = cls._get_conn()
        try:
            valor_str = json.dumps(valor, ensure_ascii=False)
            conn.execute(
                "INSERT OR REPLACE INTO estado (clave, valor) VALUES (?, ?)",
                (str(clave), valor_str),
            )
            conn.commit()
        except Exception as e:
            logger.error(f"Error escribiendo en EstadoGestor: {e}")
        finally:
            conn.close()

    @classmethod
    def get(cls, clave, default=None):
        """
        get method/function.

        Args:
            clave: Description for clave.
            default: Description for default.

        Returns:
            Description of the return value.

        Raises:
            Exception: Description of the exception.
        """
        conn = cls._get_conn()
        try:
            cur = conn.execute(
                "SELECT valor FROM estado WHERE clave = ?", (str(clave),)
            )
            row = cur.fetchone()
            if row:
                return json.loads(row[0])
            return default
        except Exception as e:
            logger.error(f"Error leyendo en EstadoGestor: {e}")
            return default
        finally:
            conn.close()

    @classmethod
    def pop(cls, clave, default=None):
        """
        pop method/function.

        Args:
            clave: Description for clave.
            default: Description for default.

        Returns:
            Description of the return value.

        Raises:
            Exception: Description of the exception.
        """
        valor = cls.get(clave, default)
        conn = cls._get_conn()
        try:
            conn.execute("DELETE FROM estado WHERE clave = ?", (str(clave),))
            conn.commit()
        except Exception as e:
            logger.error(f"Error borrando en EstadoGestor: {e}")
        finally:
            conn.close()
        return valor
