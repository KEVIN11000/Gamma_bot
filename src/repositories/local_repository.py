from __future__ import annotations

import json
from contextlib import contextmanager
from pathlib import Path
import sqlite3
import time
from typing import Any, Iterator

from logger_config import setup_logger

logger = setup_logger("local_repository")

# Default database path inside the project's data directory
BASE_DIR = Path(__file__).resolve().parent.parent.parent
DEFAULT_DB_PATH = BASE_DIR / "data" / "gamma_local.db"

ALLOWED_JORNADA_FIELDS = {
    "dia",
    "hora_entrada",
    "hora_salida_almuerzo",
    "hora_vuelta_almuerzo",
    "hora_salida",
    "modo",
    "horas_decimal",
    "auto_cerrado",
    "sincronizado_sheets",
    "actualizado_at",
}


class LocalRepository:
    """Repositorio SQLite local (Local-First) con WAL mode y timeout para alta concurrencia."""

    def __init__(
        self, db_path: Path | str | None = None, timeout: float = 15.0
    ) -> None:
        if db_path is None:
            self.db_path = DEFAULT_DB_PATH
        else:
            self.db_path = Path(db_path)

        # Ensure directory exists if not an in-memory database
        if str(self.db_path) != ":memory:":
            self.db_path.parent.mkdir(parents=True, exist_ok=True)

        self.timeout = timeout
        self._init_db()

    def _connect(self) -> sqlite3.Connection:
        conn = sqlite3.connect(str(self.db_path), timeout=self.timeout)
        conn.row_factory = sqlite3.Row
        try:
            conn.execute("PRAGMA journal_mode=WAL;")
            conn.execute("PRAGMA busy_timeout=15000;")
            conn.execute("PRAGMA synchronous=NORMAL;")
        except Exception as e:
            logger.debug(f"Error executing SQLite pragmas: {e}")
        return conn

    @contextmanager
    def get_connection(self) -> Iterator[sqlite3.Connection]:
        """Provee una conexión de solo lectura o consulta con cierre garantizado."""
        conn = self._connect()
        try:
            yield conn
        finally:
            conn.close()

    @contextmanager
    def transaction(self) -> Iterator[sqlite3.Connection]:
        """Provee un bloque transaccional ACID con commit/rollback y cierre garantizado."""
        conn = self._connect()
        try:
            with conn:
                yield conn
        finally:
            conn.close()

    def _init_db(self) -> None:
        """Inicializa las tablas base y precarga las configuraciones del sistema."""
        conn = self._connect()
        try:
            conn.executescript("""
                CREATE TABLE IF NOT EXISTS asistencia_laboral (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    fecha TEXT NOT NULL,
                    dia TEXT NOT NULL,
                    hora_entrada TEXT,
                    hora_salida_almuerzo TEXT,
                    hora_vuelta_almuerzo TEXT,
                    hora_salida TEXT,
                    modo TEXT NOT NULL DEFAULT 'normal',
                    horas_decimal REAL DEFAULT 0.0,
                    auto_cerrado INTEGER DEFAULT 0,
                    sincronizado_sheets INTEGER DEFAULT 0,
                    actualizado_at INTEGER NOT NULL,
                    UNIQUE(fecha)
                );

                CREATE TABLE IF NOT EXISTS asistencia_materias (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    fecha TEXT NOT NULL,
                    dia TEXT NOT NULL,
                    materia TEXT NOT NULL,
                    tipo_turno TEXT NOT NULL,
                    hora_entrada TEXT NOT NULL,
                    presente INTEGER DEFAULT 1,
                    sincronizado_sheets INTEGER DEFAULT 0,
                    actualizado_at INTEGER NOT NULL
                );

                CREATE TABLE IF NOT EXISTS configuraciones_sistema (
                    clave TEXT PRIMARY KEY,
                    valor TEXT NOT NULL,
                    tipo TEXT NOT NULL DEFAULT 'string',
                    descripcion TEXT
                );

                INSERT INTO configuraciones_sistema (clave, valor, tipo, descripcion)
                VALUES
                    ('HORA_SALIDA_DEFECTO', '17:00', 'string', 'Hora de corte automático de jornada laboral'),
                    ('PRESUPUESTO_ALERTAS_ACTIVO', 'true', 'bool', 'Activar alertas tempranas de gasto variable'),
                    ('PRESUPUESTO_UMBRAL_ALERTA', '80', 'int', 'Porcentaje de gasto para disparar alerta preventiva')
                ON CONFLICT(clave) DO NOTHING;
                """)
        except Exception as e:
            logger.error(f"Error inicializando SQLite local: {e}")
            raise
        finally:
            conn.close()

    # --- ASISTENCIA LABORAL ---

    def obtener_o_crear_jornada(
        self, fecha: str, dia: str, modo: str = "normal"
    ) -> dict[str, Any]:
        """Obtiene una jornada laboral por fecha, o la crea si no existe con valores iniciales."""
        now = int(time.time())
        with self.transaction() as conn:
            conn.execute(
                """
                INSERT INTO asistencia_laboral (
                    fecha, dia, modo, horas_decimal, auto_cerrado, sincronizado_sheets, actualizado_at
                ) VALUES (?, ?, ?, 0.0, 0, 0, ?)
                ON CONFLICT(fecha) DO NOTHING;
                """,
                (fecha, dia, modo, now),
            )
            cur = conn.execute(
                "SELECT * FROM asistencia_laboral WHERE fecha = ?", (fecha,)
            )
            row = cur.fetchone()
            return dict(row) if row else {}

    def actualizar_jornada(self, fecha: str, **campos: Any) -> bool:
        """Actualiza campos de la jornada para la fecha dada. Marca pendiente de sync si no se especifica."""
        if not campos:
            return False

        invalid_fields = set(campos.keys()) - ALLOWED_JORNADA_FIELDS
        if invalid_fields:
            raise ValueError(
                f"Campos inválidos para asistencia_laboral: {invalid_fields}"
            )

        payload = dict(campos)
        if "actualizado_at" not in payload:
            payload["actualizado_at"] = int(time.time())
        if "sincronizado_sheets" not in payload:
            payload["sincronizado_sheets"] = 0

        set_clause = ", ".join(f"{col} = ?" for col in payload.keys())
        params = list(payload.values()) + [fecha]

        with self.transaction() as conn:
            cur = conn.execute(
                f"UPDATE asistencia_laboral SET {set_clause} WHERE fecha = ?",
                params,
            )
            return cur.rowcount > 0

    def obtener_jornada_por_fecha(self, fecha: str) -> dict[str, Any] | None:
        """Retorna la jornada laboral de una fecha o None si no existe."""
        with self.get_connection() as conn:
            cur = conn.execute(
                "SELECT * FROM asistencia_laboral WHERE fecha = ?", (fecha,)
            )
            row = cur.fetchone()
            return dict(row) if row else None

    def listar_jornadas_pendientes_sincronizacion(
        self, limite: int | None = None
    ) -> list[dict[str, Any]]:
        """Lista las jornadas laborales pendientes de reflejar en Google Sheets (sincronizado_sheets = 0)."""
        query = "SELECT * FROM asistencia_laboral WHERE sincronizado_sheets = 0 ORDER BY fecha ASC"
        params: list[Any] = []
        if limite is not None:
            query += " LIMIT ?"
            params.append(limite)

        with self.get_connection() as conn:
            cur = conn.execute(query, params)
            return [dict(r) for r in cur.fetchall()]

    def marcar_jornadas_sincronizadas(self, fechas: list[str]) -> int:
        """Marca una lista de fechas como sincronizadas con Google Sheets."""
        if not fechas:
            return 0
        now = int(time.time())
        placeholders = ", ".join("?" for _ in fechas)
        query = (
            f"UPDATE asistencia_laboral SET sincronizado_sheets = 1, actualizado_at = ? "
            f"WHERE fecha IN ({placeholders})"
        )
        params = [now] + list(fechas)

        with self.transaction() as conn:
            cur = conn.execute(query, params)
            return cur.rowcount

    # --- ASISTENCIA MATERIAS ---

    def registrar_asistencia_materia(
        self,
        fecha: str,
        dia: str,
        materia: str,
        tipo_turno: str,
        hora_entrada: str,
        presente: int = 1,
        sincronizado_sheets: int = 0,
    ) -> int:
        """Registra la asistencia a una materia universitaria."""
        now = int(time.time())
        with self.transaction() as conn:
            cur = conn.execute(
                """
                INSERT INTO asistencia_materias (
                    fecha, dia, materia, tipo_turno, hora_entrada, presente, sincronizado_sheets, actualizado_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    fecha,
                    dia,
                    materia,
                    tipo_turno,
                    hora_entrada,
                    presente,
                    sincronizado_sheets,
                    now,
                ),
            )
            return cur.lastrowid or 0

    def obtener_asistencias_materias_por_fecha(
        self, fecha: str
    ) -> list[dict[str, Any]]:
        """Retorna todas las asistencias a cátedra registradas en una fecha dada."""
        with self.get_connection() as conn:
            cur = conn.execute(
                "SELECT * FROM asistencia_materias WHERE fecha = ? ORDER BY id ASC",
                (fecha,),
            )
            return [dict(r) for r in cur.fetchall()]

    def listar_materias_pendientes_sincronizacion(
        self, limite: int | None = None
    ) -> list[dict[str, Any]]:
        """Lista asistencias a cátedras pendientes de sincronización hacia Google Sheets."""
        query = "SELECT * FROM asistencia_materias WHERE sincronizado_sheets = 0 ORDER BY id ASC"
        params: list[Any] = []
        if limite is not None:
            query += " LIMIT ?"
            params.append(limite)

        with self.get_connection() as conn:
            cur = conn.execute(query, params)
            return [dict(r) for r in cur.fetchall()]

    def marcar_materias_sincronizadas(self, ids: list[int]) -> int:
        """Marca una lista de IDs de materias como sincronizadas."""
        if not ids:
            return 0
        now = int(time.time())
        placeholders = ", ".join("?" for _ in ids)
        query = (
            f"UPDATE asistencia_materias SET sincronizado_sheets = 1, actualizado_at = ? "
            f"WHERE id IN ({placeholders})"
        )
        params = [now] + list(ids)

        with self.transaction() as conn:
            cur = conn.execute(query, params)
            return cur.rowcount

    # --- CONFIGURACIONES DEL SISTEMA ---

    @staticmethod
    def _castear_valor(valor: str, tipo: str) -> Any:
        tipo_norm = tipo.strip().lower()
        if tipo_norm == "bool":
            return str(valor).strip().lower() in ("true", "1", "t", "yes", "si")
        elif tipo_norm == "int":
            try:
                return int(valor)
            except (ValueError, TypeError):
                return valor
        elif tipo_norm == "float":
            try:
                return float(valor)
            except (ValueError, TypeError):
                return valor
        elif tipo_norm == "json":
            try:
                return json.loads(valor)
            except (json.JSONDecodeError, TypeError):
                return valor
        return valor

    def obtener_configuracion(self, clave: str, default: Any = None) -> Any:
        """Obtiene un valor de configuración tipado o el default si no existe."""
        with self.get_connection() as conn:
            cur = conn.execute(
                "SELECT valor, tipo FROM configuraciones_sistema WHERE clave = ?",
                (clave,),
            )
            row = cur.fetchone()
            if not row:
                return default
            return self._castear_valor(row["valor"], row["tipo"])

    def establecer_configuracion(
        self,
        clave: str,
        valor: Any,
        tipo: str | None = None,
        descripcion: str | None = None,
    ) -> None:
        """Guarda o actualiza una configuración en la base de datos."""
        if tipo is None:
            if isinstance(valor, bool):
                tipo = "bool"
                val_str = "true" if valor else "false"
            elif isinstance(valor, int):
                tipo = "int"
                val_str = str(valor)
            elif isinstance(valor, float):
                tipo = "float"
                val_str = str(valor)
            elif isinstance(valor, (dict, list)):
                tipo = "json"
                val_str = json.dumps(valor)
            else:
                tipo = "string"
                val_str = str(valor)
        else:
            tipo = tipo.lower()
            if tipo == "bool":
                if isinstance(valor, bool):
                    val_str = "true" if valor else "false"
                else:
                    val_str = (
                        "true"
                        if str(valor).strip().lower() in ("true", "1", "t", "yes", "si")
                        else "false"
                    )
            elif tipo == "json" and not isinstance(valor, str):
                val_str = json.dumps(valor)
            else:
                val_str = str(valor)

        with self.transaction() as conn:
            conn.execute(
                """
                INSERT INTO configuraciones_sistema (clave, valor, tipo, descripcion)
                VALUES (?, ?, ?, ?)
                ON CONFLICT(clave) DO UPDATE SET
                    valor = excluded.valor,
                    tipo = COALESCE(excluded.tipo, configuraciones_sistema.tipo),
                    descripcion = COALESCE(excluded.descripcion, configuraciones_sistema.descripcion);
                """,
                (clave, val_str, tipo, descripcion),
            )

    def listar_configuraciones(self) -> dict[str, Any]:
        """Retorna todas las configuraciones del sistema como diccionario."""
        with self.get_connection() as conn:
            cur = conn.execute("SELECT clave, valor, tipo FROM configuraciones_sistema")
            return {
                r["clave"]: self._castear_valor(r["valor"], r["tipo"])
                for r in cur.fetchall()
            }


_local_repo: LocalRepository | None = None


def get_local_repository() -> LocalRepository:
    """Retorna la instancia singleton del repositorio local."""
    global _local_repo
    if _local_repo is None:
        _local_repo = LocalRepository()
    return _local_repo
