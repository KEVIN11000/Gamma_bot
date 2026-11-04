from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date, datetime, timedelta
from typing import Any, Dict, List, Optional

from logger_config import setup_logger
from logic.logic import get_now_py

logger = setup_logger("cashflow_service")


@dataclass
class ItemProyeccionDiaria:
    fecha: str
    saldo_inicial: float
    ingresos: float
    egresos_fijos: float
    egresos_variables: float
    saldo_final: float
    compromisos: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "fecha": self.fecha,
            "saldo_inicial": self.saldo_inicial,
            "ingresos": self.ingresos,
            "egresos_fijos": self.egresos_fijos,
            "egresos_variables": self.egresos_variables,
            "saldo_final": self.saldo_final,
            "compromisos": list(self.compromisos),
        }


@dataclass
class ResultadoFlujoCaja:
    saldo_actual: float
    saldo_proyectado_30d: float
    total_ingresos_proyectados: float
    total_gastos_fijos: float
    total_gastos_variables_estimados: float
    dias_criticos: List[Dict[str, Any]]
    dias: List[ItemProyeccionDiaria]

    def to_dict(self) -> Dict[str, Any]:
        return {
            "saldo_actual": self.saldo_actual,
            "saldo_proyectado_30d": self.saldo_proyectado_30d,
            "total_ingresos_proyectados": self.total_ingresos_proyectados,
            "total_gastos_fijos": self.total_gastos_fijos,
            "total_gastos_variables_estimados": self.total_gastos_variables_estimados,
            "dias_criticos": list(self.dias_criticos),
            "dias": [d.to_dict() for d in self.dias],
        }


class CashFlowProjector:
    """Motor de proyección de flujo de caja y compromisos financieros a 30 días."""

    def __init__(
        self,
        sheets_repo: Any = None,
        local_repo: Any = None,
    ) -> None:
        self.sheets_repo = sheets_repo
        self.local_repo = local_repo

    def proyectar_30_dias(
        self,
        saldo_inicial: float = 0.0,
        fecha_inicio: Optional[date] = None,
        ingresos_esperados: Optional[List[Dict[str, Any]]] = None,
        obligaciones_fijas: Optional[List[Dict[str, Any]]] = None,
        gasto_diario_estimado: float = 0.0,
        umbral_reserva_minima: float = 0.0,
    ) -> ResultadoFlujoCaja:
        """Calcula la serie temporal de flujo de caja para los próximos 30 días calendario.

        Args:
            saldo_inicial: Saldo real disponible al inicio del horizonte.
            fecha_inicio: Fecha inicial de la proyección (por defecto hoy en Asunción).
            ingresos_esperados: Lista de ingresos previstos (ej: [{'dia': 30, 'monto': 2500000}]).
            obligaciones_fijas: Lista de obligaciones fijas (ej: [{'concepto': 'Alquiler', 'monto': 1500000}]).
            gasto_diario_estimado: Monto estimado de egreso variable diario.
            umbral_reserva_minima: Saldo mínimo deseado; por debajo se cataloga como día crítico.

        Returns:
            Instancia de ResultadoFlujoCaja con el desglose de 30 días y análisis de liquidez.
        """
        if fecha_inicio is None:
            fecha_inicio = get_now_py().date()

        # 1. Obtener obligaciones fijas si no fueron provistas
        if obligaciones_fijas is None:
            obligaciones_fijas = self._obtener_obligaciones_activas()

        # 2. Obtener ingresos esperados si no fueron provistos
        if ingresos_esperados is None:
            ingresos_esperados = self._obtener_ingresos_programados(fecha_inicio)

        # 3. Mapear obligaciones por fecha de vencimiento
        obligaciones_por_fecha: Dict[date, List[Dict[str, Any]]] = {}
        for ob in obligaciones_fijas:
            if ob.get("pagado") is True or str(ob.get("estado", "")).lower() in (
                "pagado",
                "saldado",
                "cancelado",
            ):
                continue
            fecha_venc = self._normalizar_fecha_vencimiento(
                ob.get("vencimiento"), fecha_inicio
            )
            obligaciones_por_fecha.setdefault(fecha_venc, []).append(ob)

        # 4. Mapear ingresos por fecha
        ingresos_por_fecha: Dict[date, List[Dict[str, Any]]] = {}
        for ing in ingresos_esperados:
            f_ing = self._normalizar_fecha_ingreso(ing, fecha_inicio)
            ingresos_por_fecha.setdefault(f_ing, []).append(ing)

        # 5. Iteración temporal de 30 días
        saldo_actual_dia = float(saldo_inicial)
        total_ingresos = 0.0
        total_fijos = 0.0
        total_variables = 0.0
        dias_proyectados: List[ItemProyeccionDiaria] = []
        dias_criticos: List[Dict[str, Any]] = []

        for dia_idx in range(30):
            dia_actual = fecha_inicio + timedelta(days=dia_idx)

            # Sumar ingresos del día
            ings_del_dia = ingresos_por_fecha.get(dia_actual, [])
            monto_ingreso_dia = sum(float(i.get("monto", 0.0)) for i in ings_del_dia)
            total_ingresos += monto_ingreso_dia

            # Sumar egresos fijos del día
            obs_del_dia = obligaciones_por_fecha.get(dia_actual, [])
            monto_fijo_dia = sum(float(o.get("monto", 0.0)) for o in obs_del_dia)
            total_fijos += monto_fijo_dia

            # Egresos variables del día
            monto_var_dia = float(gasto_diario_estimado)
            total_variables += monto_var_dia

            # Balance del día
            saldo_final_dia = (
                saldo_actual_dia + monto_ingreso_dia - monto_fijo_dia - monto_var_dia
            )

            compromisos_dia = [
                f"{o.get('concepto', 'Obligación')} ({int(o.get('monto', 0)):,} Gs)"
                for o in obs_del_dia
            ]

            item = ItemProyeccionDiaria(
                fecha=dia_actual.isoformat(),
                saldo_inicial=round(saldo_actual_dia, 2),
                ingresos=round(monto_ingreso_dia, 2),
                egresos_fijos=round(monto_fijo_dia, 2),
                egresos_variables=round(monto_var_dia, 2),
                saldo_final=round(saldo_final_dia, 2),
                compromisos=compromisos_dia,
            )
            dias_proyectados.append(item)

            # Detección de días críticos
            if saldo_final_dia < umbral_reserva_minima:
                dias_criticos.append(
                    {
                        "fecha": dia_actual.isoformat(),
                        "saldo": round(saldo_final_dia, 2),
                        "deficit": round(umbral_reserva_minima - saldo_final_dia, 2),
                        "motivo": (
                            "Saldo negativo proyectado"
                            if saldo_final_dia < 0
                            else "Por debajo de la reserva mínima"
                        ),
                    }
                )

            # El saldo final de hoy es el inicial de mañana
            saldo_actual_dia = saldo_final_dia

        saldo_proyectado_30d = (
            dias_proyectados[-1].saldo_final if dias_proyectados else saldo_inicial
        )

        return ResultadoFlujoCaja(
            saldo_actual=round(saldo_inicial, 2),
            saldo_proyectado_30d=round(saldo_proyectado_30d, 2),
            total_ingresos_proyectados=round(total_ingresos, 2),
            total_gastos_fijos=round(total_fijos, 2),
            total_gastos_variables_estimados=round(total_variables, 2),
            dias_criticos=dias_criticos,
            dias=dias_proyectados,
        )

    def _normalizar_fecha_vencimiento(
        self,
        vencimiento_raw: Any,
        fecha_referencia: date,
    ) -> date:
        """Parsea fechas de vencimiento flexibles (ISO, dd/mm/yyyy, día de mes) o aplica fallback."""
        if isinstance(vencimiento_raw, date):
            return vencimiento_raw
        if isinstance(vencimiento_raw, datetime):
            return vencimiento_raw.date()

        if isinstance(vencimiento_raw, (int, float)):
            # Representa un día del mes
            dia_num = int(vencimiento_raw)
            return self._crear_fecha_en_horizonte(dia_num, fecha_referencia)

        if not vencimiento_raw or not str(vencimiento_raw).strip():
            # Fallback: último día del mes en curso
            return self._crear_fecha_en_horizonte(28, fecha_referencia)

        v_str = str(vencimiento_raw).strip()

        # Si es solo un número de día (ej: "5", "15")
        if v_str.isdigit():
            dia_num = int(v_str)
            return self._crear_fecha_en_horizonte(dia_num, fecha_referencia)

        # Formatos comunes: YYYY-MM-DD, DD/MM/YYYY, DD-MM-YYYY
        for fmt in ("%Y-%m-%d", "%d/%m/%Y", "%d-%m-%Y"):
            try:
                dt = datetime.strptime(v_str, fmt).date()
                # Si la fecha ya venció este mes, proyectar al siguiente mes
                if dt < fecha_referencia:
                    return self._crear_fecha_en_horizonte(dt.day, fecha_referencia)
                return dt
            except ValueError:
                pass

        # Fallback seguro
        return self._crear_fecha_en_horizonte(28, fecha_referencia)

    def _normalizar_fecha_ingreso(
        self,
        ingreso_item: Dict[str, Any],
        fecha_referencia: date,
    ) -> date:
        """Determina la fecha proyectada para un ingreso."""
        if "fecha" in ingreso_item:
            return self._normalizar_fecha_vencimiento(
                ingreso_item["fecha"], fecha_referencia
            )
        dia_num = ingreso_item.get("dia", 30)
        return self._crear_fecha_en_horizonte(int(dia_num), fecha_referencia)

    def _crear_fecha_en_horizonte(self, dia_num: int, fecha_ref: date) -> date:
        """Construye una fecha válida asegurando que caiga dentro del mes de referencia o el siguiente."""
        dia_clamped = max(1, min(28, dia_num))
        try:
            cand = date(fecha_ref.year, fecha_ref.month, dia_clamped)
            if cand < fecha_ref:
                # Proyectar al próximo mes
                if fecha_ref.month == 12:
                    return date(fecha_ref.year + 1, 1, dia_clamped)
                else:
                    return date(fecha_ref.year, fecha_ref.month + 1, dia_clamped)
            return cand
        except ValueError:
            return fecha_ref + timedelta(days=15)

    def _obtener_obligaciones_activas(self) -> List[Dict[str, Any]]:
        """Recupera obligaciones pendientes desde SheetsRepository o LocalRepository."""
        try:
            if self.sheets_repo is not None:
                repo = self.sheets_repo
            else:
                from repositories.sheets_repository import SheetsRepository

                repo = SheetsRepository()

            ws = repo._get_sheet("Obligaciones")
            if not ws:
                return []

            rows = ws.get_all_values()
            if len(rows) <= 1:
                return []

            headers = [h.strip().lower() for h in rows[0]]
            obligaciones: List[Dict[str, Any]] = []

            for r in rows[1:]:
                if not r or not any(r):
                    continue
                row_dict = {
                    headers[idx]: r[idx] if idx < len(r) else ""
                    for idx in range(len(headers))
                }
                monto_str = (
                    row_dict.get("monto")
                    or row_dict.get("cuota")
                    or row_dict.get("saldo", "0")
                )
                monto_clean = (
                    str(monto_str)
                    .replace(".", "")
                    .replace(",", ".")
                    .replace("Gs", "")
                    .strip()
                )
                try:
                    monto = float(monto_clean)
                except ValueError:
                    monto = 0.0

                if monto <= 0:
                    continue

                estado = str(row_dict.get("estado", "")).lower()
                if estado in ("pagado", "saldado", "cancelado"):
                    continue

                obligaciones.append(
                    {
                        "concepto": (
                            row_dict.get("concepto")
                            or row_dict.get("entidad")
                            or "Compromiso Fijo"
                        ),
                        "monto": monto,
                        "vencimiento": (
                            row_dict.get("vencimiento")
                            or row_dict.get("dia_vencimiento")
                            or ""
                        ),
                        "estado": estado,
                    }
                )
            return obligaciones
        except Exception as e:
            logger.warning(f"Error consultando obligaciones para flujo de caja: {e}")
            return []

    def _obtener_ingresos_programados(
        self, fecha_referencia: date
    ) -> List[Dict[str, Any]]:
        """Recupera ingresos regulares (salario base) desde LocalRepository o SheetsRepository."""
        try:
            if self.local_repo is not None:
                lrepo = self.local_repo
            else:
                from repositories.local_repository import get_local_repository

                lrepo = get_local_repository()

            salario = lrepo.obtener_configuracion("SALARIO_BASE", default=0.0)
            salario_monto = float(salario or 0.0)
            if salario_monto > 0:
                return [
                    {
                        "concepto": "Salario Base Mensual",
                        "monto": salario_monto,
                        "dia": 30,
                    }
                ]
        except Exception as e:
            logger.debug(f"No se pudo cargar salario programado: {e}")
        return []
