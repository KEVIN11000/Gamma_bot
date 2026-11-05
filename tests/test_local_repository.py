from __future__ import annotations

import concurrent.futures
from pathlib import Path
import time

import pytest

from repositories.local_repository import LocalRepository, get_local_repository


@pytest.fixture
def repo(tmp_path: Path) -> LocalRepository:
    """Fixture que provee una instancia limpia de LocalRepository aislada en disco temporal."""
    db_file = tmp_path / "test_gamma_local.db"
    return LocalRepository(db_path=db_file)


def test_wal_mode_and_pragmas(tmp_path: Path) -> None:
    """Verifica que la base de datos se inicialice en modo WAL y con busy_timeout configurado."""
    db_file = tmp_path / "test_wal.db"
    repository = LocalRepository(db_path=db_file)

    with repository.get_connection() as conn:
        journal_mode = conn.execute("PRAGMA journal_mode;").fetchone()[0]
        busy_timeout = conn.execute("PRAGMA busy_timeout;").fetchone()[0]

    assert str(journal_mode).lower() == "wal"
    assert int(busy_timeout) == 15000


def test_default_configurations(repo: LocalRepository) -> None:
    """Verifica que las configuraciones por defecto del sistema se precarguen correctamente."""
    hora_salida = repo.obtener_configuracion("HORA_SALIDA_DEFECTO")
    alertas_activo = repo.obtener_configuracion("PRESUPUESTO_ALERTAS_ACTIVO")
    umbral_alerta = repo.obtener_configuracion("PRESUPUESTO_UMBRAL_ALERTA")
    valor_inexistente = repo.obtener_configuracion(
        "CLAVE_INEXISTENTE", default="default_test"
    )

    assert hora_salida == "17:00"
    assert alertas_activo is True
    assert umbral_alerta == 80
    assert valor_inexistente == "default_test"


def test_establecer_y_obtener_configuracion(repo: LocalRepository) -> None:
    """Verifica el guardado y tipado de configuraciones (bool, int, float, json, string)."""
    # Bool
    repo.establecer_configuracion("MODO_ESTRICTO", False)
    assert repo.obtener_configuracion("MODO_ESTRICTO") is False

    # Int
    repo.establecer_configuracion("REINTENTOS_MAX", 5)
    assert repo.obtener_configuracion("REINTENTOS_MAX") == 5

    # Float
    repo.establecer_configuracion("TASA_DESCUENTO", 0.15)
    assert repo.obtener_configuracion("TASA_DESCUENTO") == 0.15

    # JSON
    metadata = {"tema": "oscuro", "notificaciones": [1, 2, 3]}
    repo.establecer_configuracion("PREFERENCIAS", metadata)
    assert repo.obtener_configuracion("PREFERENCIAS") == metadata

    # String & Actualización
    repo.establecer_configuracion("HORA_SALIDA_DEFECTO", "18:00")
    assert repo.obtener_configuracion("HORA_SALIDA_DEFECTO") == "18:00"

    # Listar todas
    todas = repo.listar_configuraciones()
    assert todas["MODO_ESTRICTO"] is False
    assert todas["REINTENTOS_MAX"] == 5
    assert todas["HORA_SALIDA_DEFECTO"] == "18:00"


def test_obtener_o_crear_jornada_y_rendimiento(repo: LocalRepository) -> None:
    """Verifica la creación atómica de jornada y que la latencia de inserción sea menor a 25ms."""
    # Warmup de conexión si corresponde
    repo.obtener_o_crear_jornada("2026-11-01", "Domingo", "normal")

    # Medición de tiempo de inserción
    start = time.perf_counter()
    jornada = repo.obtener_o_crear_jornada("2026-11-02", "Lunes", "normal")
    duration_ms = (time.perf_counter() - start) * 1000.0

    assert (
        duration_ms < 25.0
    ), f"Inserción tardó {duration_ms:.2f}ms, superando el umbral de 25ms"
    assert jornada["fecha"] == "2026-11-02"
    assert jornada["dia"] == "Lunes"
    assert jornada["modo"] == "normal"
    assert jornada["horas_decimal"] == 0.0
    assert jornada["auto_cerrado"] == 0
    assert jornada["sincronizado_sheets"] == 0
    assert jornada["actualizado_at"] > 0

    # Segunda llamada: no duplica, retorna la existente
    segunda = repo.obtener_o_crear_jornada("2026-11-02", "Lunes", "directo")
    assert segunda["id"] == jornada["id"]
    assert segunda["modo"] == "normal"  # Se preservó el existente


def test_actualizar_jornada_y_consultas(repo: LocalRepository) -> None:
    """Verifica la actualización atómica y consulta de jornada laboral."""
    repo.obtener_o_crear_jornada("2026-11-03", "Martes", "normal")

    actualizado = repo.actualizar_jornada(
        "2026-11-03",
        hora_entrada="08:00",
        hora_salida_almuerzo="12:00",
        hora_vuelta_almuerzo="13:00",
        hora_salida="17:00",
        horas_decimal=8.0,
        auto_cerrado=1,
    )
    assert actualizado is True

    jornada = repo.obtener_jornada_por_fecha("2026-11-03")
    assert jornada is not None
    assert jornada["hora_entrada"] == "08:00"
    assert jornada["hora_salida_almuerzo"] == "12:00"
    assert jornada["hora_vuelta_almuerzo"] == "13:00"
    assert jornada["hora_salida"] == "17:00"
    assert jornada["horas_decimal"] == 8.0
    assert jornada["auto_cerrado"] == 1
    assert jornada["sincronizado_sheets"] == 0

    # Actualizar fecha inexistente retorna False
    assert repo.actualizar_jornada("1999-01-01", hora_entrada="09:00") is False

    # Consultar fecha inexistente retorna None
    assert repo.obtener_jornada_por_fecha("1999-01-01") is None

    # Intentar actualizar campo inválido lanza ValueError
    with pytest.raises(ValueError):
        repo.actualizar_jornada("2026-11-03", campo_invalido="valor")


def test_listar_y_marcar_jornadas_sincronizadas(repo: LocalRepository) -> None:
    """Verifica el flujo de listar pendientes y marcarlas como sincronizadas."""
    repo.obtener_o_crear_jornada("2026-11-01", "Domingo")
    repo.obtener_o_crear_jornada("2026-11-02", "Lunes")
    repo.obtener_o_crear_jornada("2026-11-03", "Martes")

    pendientes = repo.listar_jornadas_pendientes_sincronizacion()
    assert len(pendientes) == 3

    # Limite opcional
    limitados = repo.listar_jornadas_pendientes_sincronizacion(limite=2)
    assert len(limitados) == 2

    # Marcar dos como sincronizadas
    afectados = repo.marcar_jornadas_sincronizadas(["2026-11-01", "2026-11-02"])
    assert afectados == 2

    # Ahora solo una queda pendiente
    restantes = repo.listar_jornadas_pendientes_sincronizacion()
    assert len(restantes) == 1
    assert restantes[0]["fecha"] == "2026-11-03"

    # Lista vacía retorna 0
    assert repo.marcar_jornadas_sincronizadas([]) == 0


def test_asistencia_materias_crud(repo: LocalRepository) -> None:
    """Verifica el registro, consulta y sincronización de asistencia a materias universitarias."""
    id1 = repo.registrar_asistencia_materia(
        fecha="2026-11-02",
        dia="Lunes",
        materia="Sistemas Distribuidos",
        tipo_turno="Teoria",
        hora_entrada="18:30",
        presente=1,
    )
    id2 = repo.registrar_asistencia_materia(
        fecha="2026-11-02",
        dia="Lunes",
        materia="Redes de Computadoras",
        tipo_turno="Practica",
        hora_entrada="20:00",
        presente=1,
    )

    assert id1 > 0
    assert id2 > id1

    materias_dia = repo.obtener_asistencias_materias_por_fecha("2026-11-02")
    assert len(materias_dia) == 2
    assert materias_dia[0]["materia"] == "Sistemas Distribuidos"
    assert materias_dia[1]["materia"] == "Redes de Computadoras"

    pendientes = repo.listar_materias_pendientes_sincronizacion()
    assert len(pendientes) == 2

    afectados = repo.marcar_materias_sincronizadas([id1])
    assert afectados == 1

    pendientes_despues = repo.listar_materias_pendientes_sincronizacion()
    assert len(pendientes_despues) == 1
    assert pendientes_despues[0]["id"] == id2

    assert repo.marcar_materias_sincronizadas([]) == 0


def test_recuperacion_concurrencia_y_colisiones(tmp_path: Path) -> None:
    """Verifica que el modo WAL y busy_timeout soporten múltiples accesos concurrentes sin bloqueos."""
    db_file = tmp_path / "test_concurrent.db"
    repository = LocalRepository(db_path=db_file)

    def worker_action(worker_id: int) -> bool:
        fecha = f"2026-11-{10 + (worker_id % 5):02d}"
        repository.obtener_o_crear_jornada(fecha, "DiaTest", "normal")
        repository.actualizar_jornada(fecha, hora_entrada=f"{worker_id % 24:02d}:00")
        repo_val = repository.obtener_jornada_por_fecha(fecha)
        return repo_val is not None

    with concurrent.futures.ThreadPoolExecutor(max_workers=10) as executor:
        futures = [executor.submit(worker_action, i) for i in range(30)]
        results = [f.result() for f in concurrent.futures.as_completed(futures)]

    assert all(results) is True


def test_singleton_get_local_repository() -> None:
    """Verifica que get_local_repository retorne y reutilice la misma instancia singleton."""
    r1 = get_local_repository()
    r2 = get_local_repository()
    assert r1 is r2
    assert isinstance(r1, LocalRepository)
