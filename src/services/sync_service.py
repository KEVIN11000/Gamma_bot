from __future__ import annotations

import os
from datetime import datetime
from typing import Any

from logger_config import setup_logger
from logic.constants import ENCABEZADOS_HORAS, ENCABEZADOS_MATERIAS, MESES_ES
from logic.logic import ConexionSheets, get_now_py
from repositories.local_repository import LocalRepository, get_local_repository
from repositories.sheets_repository import SheetsRepository

logger = setup_logger("sync_service")


class SyncService:
    """
    Servicio de sincronización bidireccional entre la base de datos local
    (LocalRepository - SQLite) y las hojas de cálculo en la nube (Google Sheets).
    """

    def __init__(
        self,
        local_repo: LocalRepository | None = None,
        sheets_repo: SheetsRepository | None = None,
        spreadsheet_id: str | None = None,
    ) -> None:
        self.local_repo = (
            local_repo if local_repo is not None else get_local_repository()
        )
        self.spreadsheet_id = (
            spreadsheet_id
            or os.getenv("LIBRO_CONTABLE_ID")
            or os.getenv("SPREADSHEET_ID")
            or ""
        )
        self.sheets_repo = (
            sheets_repo if sheets_repo is not None else SheetsRepository()
        )
        if self.spreadsheet_id and hasattr(self.sheets_repo, "_init_agents"):
            try:
                self.sheets_repo._init_agents(self.spreadsheet_id)
            except Exception:
                pass

    def _obtener_cliente_sheets(self) -> Any:
        cliente = ConexionSheets.obtener_cliente()
        if cliente is None:
            raise ConnectionError(
                "No se pudo autorizar cliente de Google Sheets (credenciales ausentes o inválidas)."
            )
        return cliente

    def _obtener_workbook(self) -> Any:
        cliente = self._obtener_cliente_sheets()
        if not self.spreadsheet_id:
            raise ValueError("SPREADSHEET_ID no está configurado.")
        return cliente.open_by_key(self.spreadsheet_id)

    def _nombre_hoja_horas(
        self, mes: int | None = None, anio: int | None = None
    ) -> str:
        ahora = get_now_py()
        m = mes if mes is not None else ahora.month
        y = anio if anio is not None else ahora.year
        return f"{MESES_ES[m - 1]} {y}"

    def _obtener_o_crear_hoja_laboral(
        self, wb: Any, mes: int | None = None, anio: int | None = None
    ) -> Any:
        nombre = self._nombre_hoja_horas(mes=mes, anio=anio)
        titulos = [h.title for h in wb.worksheets()]
        if nombre not in titulos:
            ws = wb.add_worksheet(title=nombre, rows="60", cols="10")
            ws.update("A1:G1", [ENCABEZADOS_HORAS])
            return ws
        return wb.worksheet(nombre)

    def _obtener_o_crear_hoja_materia(self, wb: Any, materia: str) -> Any:
        titulos = [h.title for h in wb.worksheets()]
        if materia not in titulos:
            ws = wb.add_worksheet(title=materia, rows="100", cols="6")
            ws.update("A1:F1", [ENCABEZADOS_MATERIAS])
            return ws
        return wb.worksheet(materia)

    @staticmethod
    def _normalizar_a_iso(fecha_str: str) -> str | None:
        """Convierte una cadena de fecha a formato ISO 'YYYY-MM-DD'."""
        limpia = fecha_str.strip()
        if not limpia:
            return None
        # Intentar formato DD/MM/YYYY
        try:
            dt = datetime.strptime(limpia, "%d/%m/%Y")
            return dt.strftime("%Y-%m-%d")
        except ValueError:
            pass
        # Intentar formato YYYY-MM-DD
        try:
            dt = datetime.strptime(limpia, "%Y-%m-%d")
            return dt.strftime("%Y-%m-%d")
        except ValueError:
            pass
        return None

    @staticmethod
    def _normalizar_a_display(fecha_iso: str) -> str:
        """Convierte fecha 'YYYY-MM-DD' a 'DD/MM/YYYY'."""
        try:
            dt = datetime.strptime(fecha_iso, "%Y-%m-%d")
            return dt.strftime("%d/%m/%Y")
        except Exception:
            return fecha_iso

    def volcar_local_a_sheets(
        self,
        mes: int | None = None,
        anio: int | None = None,
        modulo: str = "laboral",
    ) -> dict[str, Any]:
        """
        Vuelca registros pendientes (sincronizado_sheets = 0) desde SQLite hacia Google Sheets.
        Al confirmarse la escritura, marca sincronizado_sheets = 1.
        """
        try:
            wb = self._obtener_workbook()
            total_sincronizados = 0

            # 1. Sincronizar Asistencia Laboral
            if modulo in ("laboral", "todo"):
                pendientes = self.local_repo.listar_jornadas_pendientes_sincronizacion()
                fechas_ok: list[str] = []

                # Agrupar jornadas por período (mes y año)
                for j in pendientes:
                    f_iso = j.get("fecha", "")
                    try:
                        dt = datetime.strptime(f_iso, "%Y-%m-%d")
                        if mes is not None and dt.month != mes:
                            continue
                        if anio is not None and dt.year != anio:
                            continue
                    except Exception:
                        continue

                    ws = self._obtener_o_crear_hoja_laboral(
                        wb, mes=dt.month, anio=dt.year
                    )
                    fecha_display = self._normalizar_a_display(f_iso)
                    fechas_col = ws.col_values(2)

                    fila_encontrada: int | None = None
                    for idx, val in enumerate(fechas_col):
                        val_iso = self._normalizar_a_iso(val)
                        if val_iso == f_iso:
                            fila_encontrada = idx + 1
                            break

                    fila_datos = [
                        j.get("dia", ""),
                        fecha_display,
                        j.get("hora_entrada") or "",
                        j.get("hora_salida_almuerzo") or "",
                        j.get("hora_vuelta_almuerzo") or "",
                        j.get("hora_salida") or "",
                        float(j.get("horas_decimal", 0.0) or 0.0),
                    ]

                    if fila_encontrada is not None:
                        ws.update(
                            f"A{fila_encontrada}:G{fila_encontrada}", [fila_datos]
                        )
                    else:
                        ws.append_row(fila_datos)

                    fechas_ok.append(f_iso)

                if fechas_ok:
                    self.local_repo.marcar_jornadas_sincronizadas(fechas_ok)
                    total_sincronizados += len(fechas_ok)

            # 2. Sincronizar Asistencia Materias
            if modulo in ("materias", "todo"):
                pendientes_mat = (
                    self.local_repo.listar_materias_pendientes_sincronizacion()
                )
                ids_ok: list[int] = []

                for m in pendientes_mat:
                    f_iso = m.get("fecha", "")
                    try:
                        dt = datetime.strptime(f_iso, "%Y-%m-%d")
                        if mes is not None and dt.month != mes:
                            continue
                        if anio is not None and dt.year != anio:
                            continue
                    except Exception:
                        continue

                    materia = m.get("materia", "").strip()
                    if not materia:
                        continue

                    ws_mat = self._obtener_o_crear_hoja_materia(wb, materia)
                    fecha_display = self._normalizar_a_display(f_iso)
                    fechas_col = ws_mat.col_values(2)

                    fila_mat: int | None = None
                    for idx, val in enumerate(fechas_col):
                        val_iso = self._normalizar_a_iso(val)
                        if val_iso == f_iso:
                            fila_mat = idx + 1
                            break

                    tipo_turno = m.get("tipo_turno", "").lower()
                    hora_in = m.get("hora_entrada", "")

                    if fila_mat is None:
                        fila_mat = len(fechas_col) + 1
                        if fila_mat == 1:
                            ws_mat.update("A1:F1", [ENCABEZADOS_MATERIAS])
                            fila_mat = 2
                        ws_mat.update(
                            f"A{fila_mat}:B{fila_mat}",
                            [[m.get("dia", ""), fecha_display]],
                        )

                    if "teor" in tipo_turno:
                        ws_mat.update(
                            f"C{fila_mat}:D{fila_mat}",
                            [[hora_in, "Presente"]],
                        )
                    else:
                        ws_mat.update(
                            f"E{fila_mat}:F{fila_mat}",
                            [[hora_in, "Presente"]],
                        )

                    if m.get("id"):
                        ids_ok.append(int(m["id"]))

                if ids_ok:
                    self.local_repo.marcar_materias_sincronizadas(ids_ok)
                    total_sincronizados += len(ids_ok)

            return {
                "exito": True,
                "registros_sincronizados": total_sincronizados,
                "detalles": (
                    f"Volcado completado exitosamente: {total_sincronizados} "
                    f"registros sincronizados a Google Sheets."
                ),
            }

        except Exception as e:
            logger.error(f"Error en volcar_local_a_sheets: {e}")
            return {
                "exito": False,
                "registros_sincronizados": 0,
                "detalles": f"Error conectando con Google Sheets: {str(e)}",
            }

    def volcar_sheets_a_local(
        self,
        mes: int | None = None,
        anio: int | None = None,
        modulo: str = "laboral",
    ) -> dict[str, Any]:
        """
        Lee registros desde Google Sheets e inserta o actualiza en la base de datos local SQLite.
        Útil para rescatar ediciones directas en Google Sheets o restaurar estado local.
        """
        try:
            wb = self._obtener_workbook()
            total_importados = 0

            # 1. Importar Asistencia Laboral
            if modulo in ("laboral", "todo"):
                nombre_hoja = self._nombre_hoja_horas(mes=mes, anio=anio)
                try:
                    ws = wb.worksheet(nombre_hoja)
                    filas = ws.get_all_values()
                except Exception as e_ws:
                    logger.warning(
                        f"Hoja laboral '{nombre_hoja}' no encontrada en Sheets: {e_ws}"
                    )
                    filas = []

                if len(filas) > 1:
                    # Omitir fila 0 (encabezados)
                    for r in filas[1:]:
                        if len(r) < 2:
                            continue
                        dia = r[0].strip()
                        fecha_raw = r[1].strip()
                        fecha_iso = self._normalizar_a_iso(fecha_raw)
                        if not fecha_iso:
                            continue

                        # Extraer marcas
                        entrada = r[2].strip() if len(r) > 2 else ""
                        s_almuerzo = r[3].strip() if len(r) > 3 else ""
                        v_almuerzo = r[4].strip() if len(r) > 4 else ""
                        salida = r[5].strip() if len(r) > 5 else ""
                        horas_raw = r[6].strip() if len(r) > 6 else "0.0"

                        try:
                            horas_num = float(horas_raw.replace(",", "."))
                        except ValueError:
                            horas_num = 0.0

                        self.local_repo.obtener_o_crear_jornada(
                            fecha=fecha_iso, dia=dia, modo="normal"
                        )
                        self.local_repo.actualizar_jornada(
                            fecha=fecha_iso,
                            hora_entrada=entrada or None,
                            hora_salida_almuerzo=s_almuerzo or None,
                            hora_vuelta_almuerzo=v_almuerzo or None,
                            hora_salida=salida or None,
                            horas_decimal=horas_num,
                            sincronizado_sheets=1,
                        )
                        total_importados += 1

            # 2. Importar Asistencia Materias
            if modulo in ("materias", "todo"):
                for ws in wb.worksheets():
                    titulo = ws.title
                    if (
                        titulo.lower()
                        in (
                            "materias",
                            "resumen",
                            "config",
                            "libro_diario",
                            "cierres_historicos",
                            "presupuesto_base",
                        )
                        or "cierre" in titulo.lower()
                    ):
                        continue
                    # Si coincide con formato 'Mes Anio', es laboral, no materia
                    partes = titulo.split()
                    if (
                        len(partes) == 2
                        and partes[0].capitalize() in MESES_ES
                        and partes[1].isdigit()
                    ):
                        continue

                    # Es una hoja de cátedra universitaria
                    try:
                        filas_m = ws.get_all_values()
                    except Exception:
                        continue

                    if len(filas_m) > 1:
                        for r in filas_m[1:]:
                            if len(r) < 2:
                                continue
                            dia = r[0].strip()
                            fecha_raw = r[1].strip()
                            fecha_iso = self._normalizar_a_iso(fecha_raw)
                            if not fecha_iso:
                                continue

                            hora_teoria = r[2].strip() if len(r) > 2 else ""
                            asist_teoria = r[3].strip() if len(r) > 3 else ""
                            hora_practica = r[4].strip() if len(r) > 4 else ""
                            asist_practica = r[5].strip() if len(r) > 5 else ""

                            if hora_teoria and asist_teoria.lower() == "presente":
                                self.local_repo.registrar_asistencia_materia(
                                    fecha=fecha_iso,
                                    dia=dia,
                                    materia=titulo,
                                    tipo_turno="Teoria",
                                    hora_entrada=hora_teoria,
                                    presente=1,
                                    sincronizado_sheets=1,
                                )
                                total_importados += 1

                            if hora_practica and asist_practica.lower() == "presente":
                                self.local_repo.registrar_asistencia_materia(
                                    fecha=fecha_iso,
                                    dia=dia,
                                    materia=titulo,
                                    tipo_turno="Practica",
                                    hora_entrada=hora_practica,
                                    presente=1,
                                    sincronizado_sheets=1,
                                )
                                total_importados += 1

            return {
                "exito": True,
                "registros_sincronizados": total_importados,
                "detalles": (
                    f"Importación completada exitosamente: {total_importados} "
                    f"registros importados desde Google Sheets a base de datos local."
                ),
            }

        except Exception as e:
            logger.error(f"Error en volcar_sheets_a_local: {e}")
            return {
                "exito": False,
                "registros_sincronizados": 0,
                "detalles": f"Error importando desde Google Sheets: {str(e)}",
            }
