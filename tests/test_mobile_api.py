import os
import sys
import unittest
from unittest.mock import patch, MagicMock
import pytest

# Set required env vars BEFORE importing flask_app
os.environ["TOKEN"] = "test_token_123"
os.environ["CHAT_ID"] = "123456"
os.environ["SPREADSHEET_ID"] = "test_sheet_id"
os.environ["FLASK_ENV"] = "development"
os.environ["CRON_SECRET"] = "test_cron_secret"
os.environ["GITHUB_WEBHOOK_SECRET"] = "test_webhook_secret"
os.environ["X_API_KEY"] = "test-secret-key"

# Ensure src is on the path
sys.path.insert(
    0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "src"))
)

with patch("com.bot.GAMMA") as MockGamma, patch(
    "logic.cron_jobs.notificacion_clima"
), patch("logic.cron_jobs.resumen_semanal"), patch("logic.cron_jobs.rotar_logs"):
    mock_instance = MockGamma.return_value
    mock_instance.bot = MagicMock()
    mock_instance.token = "test_token_123"
    from flask_app import app  # noqa: E402


@pytest.fixture
def client():
    app.config["TESTING"] = True
    with app.test_client() as client:
        yield client


def test_unauthorized_access(client):
    res = client.get("/api/v1/health")
    assert res.status_code == 401
    data = res.get_json()
    assert data["error"]["code"] == "UNAUTHORIZED"


def test_health_with_key(client):
    res = client.get("/api/v1/health", headers={"X-API-KEY": "test-secret-key"})
    assert res.status_code == 200
    data = res.get_json()
    assert data["status"] == "ok"
    assert data["sheets_connected"] is True
    assert data["calendar_connected"] is True
    assert data["version"] == "1.18.5"
    assert data["mobile_version"] == "0.0.10"
    assert (
        data["download_url"]
        == "https://github.com/KEVIN11000/Gamma_Mobile/releases/latest"
    )
    assert data["version_api"] == "1.0.0"
    assert data["latest_app_version"] == "0.0.10"


def test_dashboard_summary(client):
    res = client.get(
        "/api/v1/dashboard/summary", headers={"X-API-KEY": "test-secret-key"}
    )
    assert res.status_code == 200
    assert "no-store" in res.headers.get("Cache-Control", "")
    data = res.get_json()
    assert "mes" in data
    assert "margen_libre" in data
    assert "posicion_iva" in data
    assert "es_debito_fiscal" in data


def test_movimientos_crud(client):
    headers = {"X-API-KEY": "test-secret-key"}
    # GET
    res = client.get("/api/v1/movimientos", headers=headers)
    assert res.status_code == 200

    # POST (IVA 10%)
    payload = {
        "proveedor_cliente": "Supermercado Test",
        "total": 110000,
        "categoria": "Supermercado",
        "tasa_iva": "10%",
        "movimiento": "Gasto",
        "comprobante": "Física Legal",
    }
    res_post = client.post("/api/v1/movimientos", headers=headers, json=payload)
    assert res_post.status_code == 200
    assert "no-store" in res_post.headers.get("Cache-Control", "")
    data = res_post.get_json()
    assert data["total"] == 110000
    assert data["iva"] == 10000
    assert data["neto"] == 100000
    assert data["clasificacion_iva"] == "IVA 10%"

    # POST (IVA 5%)
    payload_5 = {
        "proveedor_cliente": "Frutería Test",
        "total": 105000,
        "categoria": "Alimentación",
        "tasa_iva": "5%",
        "movimiento": "Gasto",
        "comprobante": "Física Legal",
    }
    res_5 = client.post("/api/v1/movimientos", headers=headers, json=payload_5)
    assert res_5.status_code == 200
    data_5 = res_5.get_json()
    assert data_5["total"] == 105000
    assert data_5["iva"] == 5000
    assert data_5["neto"] == 100000
    assert data_5["clasificacion_iva"] == "IVA 5%"

    # POST (Exento)
    payload_exento = {
        "proveedor_cliente": "Servicio Exento",
        "total": 50000,
        "categoria": "Varios",
        "tasa_iva": "Exento",
        "movimiento": "Gasto",
        "comprobante": "No Legal",
    }
    res_ex = client.post("/api/v1/movimientos", headers=headers, json=payload_exento)
    assert res_ex.status_code == 200
    data_ex = res_ex.get_json()
    assert data_ex["total"] == 50000
    assert data_ex["iva"] == 0
    assert data_ex["neto"] == 50000
    assert data_ex["clasificacion_iva"] == "Exento"

    # POST (Salario auto-sincronizado)
    with unittest.mock.patch(
        "repositories.sheets_repository.SheetsRepository.upsert_salario_presupuesto_base"
    ) as mock_upsert:
        payload_salario = {
            "proveedor_cliente": "Empresa Pagadora",
            "total": 6000000,
            "categoria": "Salario",
            "tasa_iva": "Exento",
            "movimiento": "Ingreso",
            "comprobante": "Virtual Legal",
        }
        res_sal = client.post(
            "/api/v1/movimientos", headers=headers, json=payload_salario
        )
        assert res_sal.status_code == 200
        mock_upsert.assert_called_once_with(6000000)


def test_obligaciones_endpoints(client):
    headers = {"X-API-KEY": "test-secret-key"}
    # GET
    res = client.get("/api/v1/obligaciones", headers=headers)
    assert res.status_code == 200

    # POST create (Deuda Simulada con entidad y cuotas)
    res_create = client.post(
        "/api/v1/obligaciones",
        headers=headers,
        json={
            "entidad": "Banco Atlas",
            "nombre": "Préstamo Auto",
            "monto_inicial": 5000000,
            "cuotas_totales": 12,
            "cuota_referencia_gs": 450000,
            "estado": "Simulado",
            "tipo": "Préstamo",
        },
    )
    assert res_create.status_code == 201
    data_cr = res_create.get_json()
    ob_id = data_cr["ID_Obligacion"]
    assert data_cr["Estado"] == "Simulado"
    assert data_cr["Entidad"] == "Banco Atlas"
    assert data_cr["Cuotas_Totales"] == 12

    # Simular con cálculo de margen de ataque
    with unittest.mock.patch(
        "logic.financiero.calcular_margen_de_ataque", return_value=3500000
    ):
        res_sim = client.post(
            "/api/v1/obligaciones/simular",
            headers=headers,
            json={"monto": 12000000, "meses": 12},
        )
        assert res_sim.status_code == 200
        data_sim = res_sim.get_json()
        assert data_sim["cuota_mensual"] == 1000000
        assert data_sim["margen_actual"] == 3500000
        assert data_sim["nuevo_margen"] == 2500000
        assert data_sim["diagnostico"] == "Viable"

    # PUT (Aprobar simulación y actualizar saldo)
    mock_ob = {
        "ID_Obligacion": ob_id,
        "Nombre": "Préstamo Auto",
        "Monto_Inicial": 5000000,
        "Saldo_Actual": 5000000,
        "Estado": "Simulado",
    }
    with unittest.mock.patch(
        "repositories.sheets_repository.SheetsRepository.get_obligacion_by_id",
        side_effect=lambda oid: dict(mock_ob) if oid == ob_id else {},
    ), unittest.mock.patch(
        "repositories.sheets_repository.SheetsRepository.update_obligacion",
        return_value=True,
    ) as mock_upd, unittest.mock.patch(
        "repositories.sheets_repository.SheetsRepository.delete_obligacion",
        return_value=True,
    ) as mock_del:
        res_put = client.put(
            f"/api/v1/obligaciones/{ob_id}",
            headers=headers,
            json={"estado": "Activo", "saldo_actual": 4500000},
        )
        assert res_put.status_code == 200
        data_put = res_put.get_json()
        assert data_put["Estado"] == "Activo"
        assert data_put["Saldo_Actual"] == 4500000
        mock_upd.assert_called_once()

        # PUT inexistente -> 404
        res_put_404 = client.put(
            "/api/v1/obligaciones/inexistente-99",
            headers=headers,
            json={"estado": "Activo"},
        )
        assert res_put_404.status_code == 404

        # DELETE obligación
        res_del = client.delete(f"/api/v1/obligaciones/{ob_id}", headers=headers)
        assert res_del.status_code == 200
        assert res_del.get_json()["status"] == "deleted"
        mock_del.assert_called_once_with(ob_id)

        # DELETE inexistente -> 404
        res_del_404 = client.delete(
            "/api/v1/obligaciones/inexistente-99", headers=headers
        )
        assert res_del_404.status_code == 404

    # Abonar
    mock_ob_abono = {
        "ID_Obligacion": ob_id,
        "Nombre": "Préstamo Auto",
        "Entidad": "Banco Atlas",
        "Monto_Inicial": 5000000,
        "Saldo_Actual": 4500000,
        "Cuotas_Restantes": 10,
        "Estado": "Activo",
    }
    with unittest.mock.patch(
        "repositories.sheets_repository.SheetsRepository.get_obligacion_by_id",
        side_effect=lambda oid: dict(mock_ob_abono) if oid == ob_id else {},
    ), unittest.mock.patch(
        "repositories.sheets_repository.SheetsRepository.update_obligacion_saldo"
    ) as mock_upd_saldo, unittest.mock.patch(
        "repositories.sheets_repository.SheetsRepository.insert_movimiento_diario"
    ) as mock_ins_mov:
        res_abono = client.post(
            "/api/v1/obligaciones/abonar",
            headers=headers,
            json={"id_obligacion": ob_id, "monto": 1000000},
        )
        assert res_abono.status_code == 200
        data_abono = res_abono.get_json()
        assert data_abono["status"] == "ok"
        assert data_abono["saldo_actual"] == 3500000
        assert data_abono["cuotas_restantes"] == 9
        assert data_abono["egreso_registrado"] == 1000000
        mock_upd_saldo.assert_called_once_with(
            ob_id, 3500000, cuotas_restantes=9, nuevo_estado="Activo"
        )
        mock_ins_mov.assert_called_once()
        mov_called = mock_ins_mov.call_args[0][0]
        assert mov_called["Categoría"] == "Préstamos / Deudas"
        assert mov_called["Total"] == 1000000
        assert mov_called["Proveedor/Cliente"] == "Banco Atlas"
        assert mov_called["ID_Obligacion"] == ob_id

        # 404 si la obligación no existe
        res_abono_404 = client.post(
            "/api/v1/obligaciones/abonar",
            headers=headers,
            json={"id_obligacion": "INEXISTENTE-99", "monto": 500000},
        )
        assert res_abono_404.status_code == 404

        # 400 si monto <= 0
        res_abono_400 = client.post(
            "/api/v1/obligaciones/abonar",
            headers=headers,
            json={"id_obligacion": ob_id, "monto": 0},
        )
        assert res_abono_400.status_code == 400


def test_vencimientos_and_foco_endpoints(client):
    headers = {"X-API-KEY": "test-secret-key"}

    # 1. Sin auth -> 401
    assert client.get("/api/v1/obligaciones/vencimientos").status_code == 401
    assert client.get("/api/v1/obligaciones/foco").status_code == 401

    # 2. Vencimientos con datos mockeados
    mock_deudas = [
        {
            "ID_Obligacion": "DEU-01",
            "Nombre": "Tarjeta Sudameris",
            "Entidad": "Sudameris",
            "Dia_Vencimiento": 5,
            "Cuota_Referencia_Gs": 400000,
            "Saldo_Actual": 1200000,
            "Estado": "Activo",
        },
        {
            "ID_Obligacion": "DEU-02",
            "Nombre": "Préstamo Cooperativa",
            "Entidad": "Coop San Cristóbal",
            "Dia_Vencimiento": 25,
            "Cuota_Referencia_Gs": 850000,
            "Saldo_Actual": 5000000,
            "Estado": "Activo",
        },
        {
            "ID_Obligacion": "DEU-03",
            "Nombre": "Deuda Pausada",
            "Entidad": "Familiar",
            "Dia_Vencimiento": 15,
            "Cuota_Referencia_Gs": 300000,
            "Saldo_Actual": 600000,
            "Estado": "Pausado",
        },
    ]

    with unittest.mock.patch(
        "repositories.sheets_repository.SheetsRepository.get_todas_obligaciones",
        return_value=mock_deudas,
    ):
        res_venc = client.get("/api/v1/obligaciones/vencimientos", headers=headers)
        assert res_venc.status_code == 200
        data_venc = res_venc.get_json()
        assert "mes_actual" in data_venc
        assert "dia_actual" in data_venc
        assert "vencimientos" in data_venc
        vencs = data_venc["vencimientos"]
        # Debe excluir la deuda pausada DEU-03
        assert len(vencs) == 2
        assert vencs[0]["id"] == "DEU-01"
        assert vencs[0]["entidad"] == "Sudameris"
        assert vencs[0]["dia_vencimiento"] == 5
        assert vencs[1]["id"] == "DEU-02"
        assert vencs[1]["dia_vencimiento"] == 25
        assert isinstance(vencs[0]["vencida"], bool)

    # 3. Foco por defecto (prioridad) y por saldo
    mock_proyeccion = {
        "margen_ataque": 1500000,
        "proyeccion": [
            {
                "id": "DEU-01",
                "nombre": "Tarjeta Sudameris",
                "saldo": 1200000,
                "cuota": 400000,
                "meses_cancelacion": 1,
            },
            {
                "id": "DEU-02",
                "nombre": "Préstamo Cooperativa",
                "saldo": 5000000,
                "cuota": 850000,
                "meses_cancelacion": 5,
            },
        ],
    }
    with unittest.mock.patch(
        "logic.financiero.proyectar_cola_deudas",
        return_value=mock_proyeccion,
    ) as mock_proy:
        # Default -> criterio prioridad
        res_foco = client.get("/api/v1/obligaciones/foco", headers=headers)
        assert res_foco.status_code == 200
        d_foco = res_foco.get_json()
        assert d_foco["criterio"] == "prioridad"
        assert d_foco["margen_ataque"] == 1500000
        assert d_foco["deuda_foco"]["id"] == "DEU-01"
        mock_proy.assert_called_with(criterio="prioridad")

        # Criterio saldo
        res_foco_saldo = client.get(
            "/api/v1/obligaciones/foco?criterio=saldo", headers=headers
        )
        assert res_foco_saldo.status_code == 200
        assert res_foco_saldo.get_json()["criterio"] == "saldo"
        mock_proy.assert_called_with(criterio="saldo")

        # Criterio no válido cae a prioridad
        res_foco_invalid = client.get(
            "/api/v1/obligaciones/foco?criterio=otro", headers=headers
        )
        assert res_foco_invalid.status_code == 200
        assert res_foco_invalid.get_json()["criterio"] == "prioridad"
        mock_proy.assert_called_with(criterio="prioridad")


def test_proyectar_capacidad_endpoint(client):
    headers = {"X-API-KEY": "test-secret-key"}

    # 1. 401 sin API Key
    res_no_auth = client.post("/api/v1/obligaciones/proyectar-capacidad", json={})
    assert res_no_auth.status_code == 401

    # 2. 200 con payload vacío / default
    mock_res_default = {
        "compromiso_total_mes": 1200000,
        "fondo_disponible_mes": 5000000,
        "capacidad_neta": 3800000,
        "semaforo": "SUPERAVIT",
        "dti_proyectado": 0.2,
        "meses_ahorrados_por_abonos": {},
    }
    with unittest.mock.patch(
        "logic.financiero.proyectar_capacidad_pago",
        return_value=mock_res_default,
    ) as mock_proy:
        res_ok = client.post(
            "/api/v1/obligaciones/proyectar-capacidad",
            headers=headers,
            json={},
        )
        assert res_ok.status_code == 200
        data = res_ok.get_json()
        assert data["semaforo"] == "SUPERAVIT"
        assert data["compromiso_total_mes"] == 1200000
        assert data["fondo_disponible_mes"] == 5000000
        assert data["capacidad_neta"] == 3800000
        assert data["dti_proyectado"] == 0.2
        mock_proy.assert_called_once_with(
            deudas_pausadas_simuladas=[],
            abonos_extraordinarios={},
            ajuste_ingreso_extra=0,
        )

    # 3. 200 con simulación What-If
    mock_res_sim = {
        "compromiso_total_mes": 800000,
        "fondo_disponible_mes": 5500000,
        "capacidad_neta": 4700000,
        "semaforo": "SUPERAVIT",
        "dti_proyectado": 0.1333,
        "meses_ahorrados_por_abonos": {"DEU-01": 3},
    }
    with unittest.mock.patch(
        "logic.financiero.proyectar_capacidad_pago",
        return_value=mock_res_sim,
    ) as mock_proy_sim:
        payload = {
            "deudas_pausadas_simuladas": ["DEU-02"],
            "abonos_extraordinarios": {"DEU-01": 1500000},
            "ajuste_ingreso_extra": 500000,
        }
        res_sim = client.post(
            "/api/v1/obligaciones/proyectar-capacidad",
            headers=headers,
            json=payload,
        )
        assert res_sim.status_code == 200
        data_sim = res_sim.get_json()
        assert data_sim["compromiso_total_mes"] == 800000
        assert data_sim["fondo_disponible_mes"] == 5500000
        assert data_sim["meses_ahorrados_por_abonos"]["DEU-01"] == 3
        mock_proy_sim.assert_called_once_with(
            deudas_pausadas_simuladas=["DEU-02"],
            abonos_extraordinarios={"DEU-01": 1500000},
            ajuste_ingreso_extra=500000,
        )

    # 4. 400 en error de validación
    res_val_err = client.post(
        "/api/v1/obligaciones/proyectar-capacidad",
        headers=headers,
        json={"ajuste_ingreso_extra": "invalido_no_entero"},
    )
    assert res_val_err.status_code == 400
    assert res_val_err.get_json()["error"]["code"] == "VALIDATION_ERROR"

    # 5. 500 si falla el cálculo interno
    with unittest.mock.patch(
        "logic.financiero.proyectar_capacidad_pago",
        side_effect=RuntimeError("Fallo inesperado de cálculo"),
    ):
        res_err = client.post(
            "/api/v1/obligaciones/proyectar-capacidad",
            headers=headers,
            json={},
        )
        assert res_err.status_code == 500
        assert res_err.get_json()["error"]["code"] == "INTERNAL_ERROR"


def test_avisos_endpoints(client, tmp_path):
    headers = {"X-API-KEY": "test-secret-key"}
    fake_avisos = tmp_path / "avisos.json"
    with unittest.mock.patch(
        "api.blueprint.AVISOS_FILE", fake_avisos
    ), unittest.mock.patch(
        "logic.logic.AgenteAutonomoHoras.guardar_aviso_calendar",
        return_value="✅ *¡Aviso guardado en Google Calendar!*",
    ) as mock_guardar, unittest.mock.patch(
        "logic.logic.AgenteAutonomoHoras.eliminar_aviso_calendar",
        return_value=True,
    ) as mock_eliminar, unittest.mock.patch(
        "logic.logic.AgenteAutonomoHoras.obtener_lista_avisos_calendar",
        return_value=[
            {
                "id": "cal-999",
                "titulo": "Reunión Sync",
                "fecha_evento": "25/10/2026 10:00",
            }
        ],
    ):
        # 1. POST (Creación con repetición e hitos)
        res_post = client.post(
            "/api/v1/avisos",
            headers=headers,
            json={
                "titulo": "Test Aviso",
                "fecha_evento": "20/10/2026 14:00",
                "repeticion": "MENSUAL",
                "hitos_minutos": [1440, 180, 60],
                "dias_restantes": 7,
            },
        )
        assert res_post.status_code == 201
        data_post = res_post.get_json()
        aviso_id = data_post["id"]
        assert data_post["repeticion"] == "MENSUAL"
        assert data_post["hitos_minutos"] == [1440, 180, 60]
        assert data_post["event_id"] == f"gcal-{aviso_id}"
        mock_guardar.assert_called()

        # 2. GET (Lectura y sincronización de Calendar)
        res_get = client.get("/api/v1/avisos", headers=headers)
        assert res_get.status_code == 200
        titulos = [a["titulo"] for a in res_get.get_json()]
        assert "Test Aviso" in titulos
        assert "Reunión Sync" in titulos

        # 3. PUT (Actualización)
        res_put = client.put(
            f"/api/v1/avisos/{aviso_id}",
            headers=headers,
            json={
                "titulo": "Test Aviso Modificado",
                "repeticion": "ANUAL",
            },
        )
        assert res_put.status_code == 200
        data_put = res_put.get_json()
        assert data_put["titulo"] == "Test Aviso Modificado"
        assert data_put["repeticion"] == "ANUAL"

        # 4. PUT inexistente -> 404
        res_put_404 = client.put(
            "/api/v1/avisos/inexistente-123",
            headers=headers,
            json={"titulo": "Nada"},
        )
        assert res_put_404.status_code == 404

        # 5. DELETE
        res_del = client.delete(f"/api/v1/avisos/{aviso_id}", headers=headers)
        assert res_del.status_code == 200
        mock_eliminar.assert_called_with(f"gcal-{aviso_id}")


def test_asistencia_endpoints(client):
    headers = {"X-API-KEY": "test-secret-key"}
    # Marcación laboral exitosa (Entrada)
    with unittest.mock.patch(
        "logic.logic.AgenteAutonomoHoras.ejecutar_marcado_para_bot",
        return_value="✅ *Entrada* registrado a las 08:30.",
    ):
        res_marcar = client.post(
            "/api/v1/asistencia/marcar",
            headers=headers,
            json={"modo": "normal"},
        )
        assert res_marcar.status_code == 200
        data_marcar = res_marcar.get_json()
        assert data_marcar["tipo"] == "entrada"
        assert data_marcar["hora"] == "08:30"
        assert "Entrada" in data_marcar["mensaje"]

    # Marcación laboral exitosa (Salida)
    with unittest.mock.patch(
        "logic.logic.AgenteAutonomoHoras.ejecutar_marcado_para_bot",
        return_value="✅ *Salida* registrado a las 17:00.",
    ):
        res_salida = client.post(
            "/api/v1/asistencia/marcar",
            headers=headers,
            json={"modo": "directo"},
        )
        assert res_salida.status_code == 200
        data_salida = res_salida.get_json()
        assert data_salida["tipo"] == "salida"
        assert data_salida["hora"] == "17:00"

    # Marcación rechazada con error (❌ Límite alcanzado) -> HTTP 400
    with unittest.mock.patch(
        "logic.logic.AgenteAutonomoHoras.ejecutar_marcado_para_bot",
        return_value="❌ Límite de filas alcanzado o error en fecha.",
    ):
        res_err = client.post(
            "/api/v1/asistencia/marcar",
            headers=headers,
            json={"modo": "normal"},
        )
        assert res_err.status_code == 400
        assert res_err.get_json()["tipo"] == "error"
        assert "❌" in res_err.get_json()["mensaje"]

    # Marcación con advertencia de almuerzo (⚠️ Ya hay registros) -> HTTP 409
    with unittest.mock.patch(
        "logic.logic.AgenteAutonomoHoras.ejecutar_marcado_para_bot",
        return_value="⚠️ Ya hay registros de almuerzo en la planilla.\nUsá el marcado normal.",
    ):
        res_warn = client.post(
            "/api/v1/asistencia/marcar",
            headers=headers,
            json={"modo": "directo"},
        )
        assert res_warn.status_code == 409
        assert res_warn.get_json()["tipo"] == "error"
        assert "⚠️" in res_warn.get_json()["mensaje"]

    # Marcación informativa/bloqueada (ℹ️ Ya completaste todos los registros) -> HTTP 200 informativo
    with unittest.mock.patch(
        "logic.logic.AgenteAutonomoHoras.ejecutar_marcado_para_bot",
        return_value="ℹ️ Ya completaste todos los registros of hoy.",
    ):
        res_info = client.post(
            "/api/v1/asistencia/marcar",
            headers=headers,
            json={"modo": "normal"},
        )
        assert res_info.status_code == 200
        assert res_info.get_json()["tipo"] == "info"
        assert res_info.get_json()["confirmado_en_planilla"] is True

    # Fallo en conexión a Google Sheets -> HTTP 502
    with unittest.mock.patch(
        "logic.logic.AgenteAutonomoHoras.ejecutar_marcado_para_bot",
        side_effect=RuntimeError("Google Sheets Timeout"),
    ):
        res_502 = client.post(
            "/api/v1/asistencia/marcar",
            headers=headers,
            json={"modo": "normal"},
        )
        assert res_502.status_code == 502
        assert res_502.get_json()["error"]["code"] == "SERVICE_ERROR"

    # Rate limiting 429 en marcar_asistencia
    import gspread

    mock_resp_429 = unittest.mock.MagicMock()
    mock_resp_429.status_code = 429
    mock_resp_429.json.return_value = {
        "error": {
            "code": 429,
            "status": "RESOURCE_EXHAUSTED",
            "message": "Quota exceeded",
        }
    }
    api_error_429 = gspread.exceptions.APIError(mock_resp_429)

    with unittest.mock.patch(
        "logic.logic.AgenteAutonomoHoras.ejecutar_marcado_para_bot",
        side_effect=api_error_429,
    ):
        res_429 = client.post(
            "/api/v1/asistencia/marcar",
            headers=headers,
            json={"modo": "normal"},
        )
        assert res_429.status_code == 429
        assert res_429.get_json()["error"]["code"] == "RATE_LIMIT_EXCEEDED"
        assert "60 segundos" in res_429.get_json()["error"]["message"]

    # 1. Sin clase en curso: Debe rebotar con 400 Bad Request y mensaje explicativo (Fix TCK-004)
    with unittest.mock.patch(
        "logic.logic.AgenteAsistenciaMaterias.HORARIOS_MATERIAS", {"Base de Datos": {}}
    ), unittest.mock.patch(
        "logic.logic.AgenteAsistenciaMaterias.obtener_materia_actual",
        return_value=(None, None),
    ):
        res_materia_no_clase = client.post(
            "/api/v1/asistencia/materia",
            headers=headers,
            json={"materia": "Mecatrónica"},
        )
        assert res_materia_no_clase.status_code == 400
        data_no_clase = res_materia_no_clase.get_json()
        assert data_no_clase["error"]["code"] == "NO_CLASE_EN_CURSO"
        assert "No hay clase en curso" in data_no_clase["mensaje"]

    # 2. Con clase en curso pero materia distinta (Mismatch): Debe rebotar con 400
    with unittest.mock.patch(
        "logic.logic.AgenteAsistenciaMaterias.HORARIOS_MATERIAS", {"Base de Datos": {}}
    ), unittest.mock.patch(
        "logic.logic.AgenteAsistenciaMaterias.obtener_materia_actual",
        return_value=("Base de Datos", "teoria"),
    ):
        res_materia_mismatch = client.post(
            "/api/v1/asistencia/materia", headers=headers, json={"materia": "Física"}
        )
        assert res_materia_mismatch.status_code == 400
        data_mismatch = res_materia_mismatch.get_json()
        assert data_mismatch["error"]["code"] == "MATERIA_MISMATCH"
        assert "Base de Datos" in data_mismatch["mensaje"]

    # 3. Con clase en curso y coincidencia exitosa: Debe registrar asistencia real (200 OK)
    with unittest.mock.patch(
        "logic.logic.AgenteAsistenciaMaterias.HORARIOS_MATERIAS", {"Base de Datos": {}}
    ), unittest.mock.patch(
        "logic.logic.AgenteAsistenciaMaterias.obtener_materia_actual",
        return_value=("Base de Datos", "teoria"),
    ), unittest.mock.patch(
        "logic.logic.AgenteAsistenciaMaterias.marcar_asistencia",
        return_value="✅ Asistencia de *Base de Datos* (teoria) registrada exitosamente a las 18:00.",
    ):
        res_materia_ok = client.post(
            "/api/v1/asistencia/materia",
            headers=headers,
            json={"materia": "Base de Datos"},
        )
        assert res_materia_ok.status_code == 200
        data_ok = res_materia_ok.get_json()
        assert data_ok["materia"] == "Base de Datos"
        assert "registrada exitosamente" in data_ok["mensaje"]

    # Rate limiting 429 en marcar_materia
    with unittest.mock.patch(
        "logic.logic.AgenteAsistenciaMaterias.HORARIOS_MATERIAS", {"Base de Datos": {}}
    ), unittest.mock.patch(
        "logic.logic.AgenteAsistenciaMaterias.obtener_materia_actual",
        return_value=("Base de Datos", "teoria"),
    ), unittest.mock.patch(
        "logic.logic.AgenteAsistenciaMaterias.marcar_asistencia",
        side_effect=api_error_429,
    ):
        res_materia_429 = client.post(
            "/api/v1/asistencia/materia",
            headers=headers,
            json={"materia": "Base de Datos"},
        )
        assert res_materia_429.status_code == 429
        assert res_materia_429.get_json()["error"]["code"] == "RATE_LIMIT_EXCEEDED"
        assert "60 segundos" in res_materia_429.get_json()["error"]["message"]


def test_autodeteccion_periodo_agente_horas(tmp_path):
    from logic.logic import AgenteAutonomoHoras, get_now_py
    import unittest.mock

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
    nombre_esperado = f"{meses_es[ahora.month - 1]} {ahora.year}"

    fake_base = tmp_path / "app_root"
    fake_base.mkdir()

    agente = AgenteAutonomoHoras(spreadsheet_id="dummy_id")
    mock_wb = unittest.mock.MagicMock()
    mock_ws = unittest.mock.MagicMock()
    mock_wb.worksheet.return_value = mock_ws
    agente._wb = mock_wb

    with unittest.mock.patch("logic.logic.BASE_DIR", fake_base):
        _ = agente.ws
        # Verifica que intentó abrir la hoja del período actual dinámico, no 'Mayo 2026'
        mock_wb.worksheet.assert_called_once_with(nombre_esperado)
        # Verifica que periodo_actual.txt fue creado con el mes actual
        txt_path = fake_base / "periodo_actual.txt"
        assert txt_path.exists()
        assert txt_path.read_text(encoding="utf-8") == nombre_esperado


def test_cierres_and_pdf(client):
    headers = {"X-API-KEY": "test-secret-key"}

    # 1. GET /cierres sin auth -> 401
    res_no_auth = client.get("/api/v1/cierres")
    assert res_no_auth.status_code == 401

    # 2. GET /cierres con datos de Cierres_Historicos
    mock_cierre_db = [
        {
            "ID_Cierre": "cierre_contable_octubre_2026",
            "Mes": "Octubre",
            "Anio": "2026",
            "Total_Ingresos": 12000000,
            "Total_Gastos": 7500000,
            "Fecha_Cierre": "16/10/2026 11:10",
        }
    ]
    with unittest.mock.patch(
        "repositories.sheets_repository.SheetsRepository.get_todos_cierres_historicos",
        return_value=mock_cierre_db,
    ):
        res_list = client.get("/api/v1/cierres", headers=headers)
        assert res_list.status_code == 200
        items = res_list.get_json()
        assert len(items) >= 1
        c = next(i for i in items if i["id"] == "cierre_contable_octubre_2026")
        assert c["tipo"] == "contable"
        assert c["periodo"] == "Octubre 2026"
        assert c["total_monto"] == 12000000
        assert "12.000.000" in c["resumen"]
        assert "7.500.000" in c["resumen"]
        assert (
            c["pdf_url"] == "/api/v1/cierres/reportes/cierre_contable_octubre_2026.pdf"
        )
        assert isinstance(c["pdf_disponible"], bool)

    res_cierre = client.post(
        "/api/v1/cierres/ejecutar", headers=headers, json={"hoja": "Octubre 2026"}
    )
    assert res_cierre.status_code == 200
    pdf_url = res_cierre.get_json()["pdf_url"]

    # Descarga estática y verificación de integridad PDF binaria (Fix TCK-004)
    filename = pdf_url.split("/")[-1]
    res_pdf = client.get(f"/api/v1/cierres/reportes/{filename}")
    assert res_pdf.status_code == 200
    assert res_pdf.content_type == "application/pdf"
    assert res_pdf.data.startswith(b"%PDF-1.")
    assert (
        len(res_pdf.data) > 1000
    )  # Documento ReportLab completo con fuentes y tabla, no stub de 65 bytes


def test_soporte_tickets_and_logs(client, monkeypatch, tmp_path):
    headers = {"X-API-KEY": "test-secret-key"}
    fake_tickets = tmp_path / "tickets.json"
    fake_tickets.write_text("[]", encoding="utf-8")
    monkeypatch.setattr("api.blueprint.TICKETS_FILE", fake_tickets)

    # Ticket POST
    res_post = client.post(
        "/api/v1/soporte/tickets",
        headers=headers,
        json={
            "asunto": "Fallo sincronización",
            "descripcion": "Prueba unitaria",
            "origen": "telegram",
        },
    )
    assert res_post.status_code == 201
    post_data = res_post.get_json()
    assert post_data["origen"] == "telegram"
    assert post_data["estado"] == "Abierto"
    ticket_id = post_data["id"]

    # Ticket GET
    res_get = client.get("/api/v1/soporte/tickets", headers=headers)
    assert res_get.status_code == 200
    tickets = res_get.get_json()
    assert len(tickets) == 1
    assert tickets[0]["origen"] == "telegram"

    # Ticket PATCH - Éxito
    res_patch = client.patch(
        f"/api/v1/soporte/tickets/{ticket_id}",
        headers=headers,
        json={"estado": "Cerrado", "resolucion": "Resuelto en testing"},
    )
    assert res_patch.status_code == 200
    patch_data = res_patch.get_json()
    assert patch_data["estado"] == "Cerrado"
    assert patch_data["resolucion"] == "Resuelto en testing"

    # Ticket PATCH - Estado inválido
    res_patch_invalid = client.patch(
        f"/api/v1/soporte/tickets/{ticket_id}",
        headers=headers,
        json={"estado": "Invalido"},
    )
    assert res_patch_invalid.status_code == 400

    # Ticket PATCH - 404 No encontrado
    res_patch_404 = client.patch(
        "/api/v1/soporte/tickets/TCK-999",
        headers=headers,
        json={"estado": "Cerrado"},
    )
    assert res_patch_404.status_code == 404

    # Logs
    res_logs = client.get("/api/v1/sistema/logs?limit=5", headers=headers)
    assert res_logs.status_code == 200
    assert "no-store" in res_logs.headers.get("Cache-Control", "")
    logs_data = res_logs.get_json()
    assert isinstance(logs_data, list)
    assert len(logs_data) <= 5
    if logs_data:
        entry = logs_data[0]
        assert "timestamp" in entry
        assert "nivel" in entry
        assert "mensaje" in entry
        assert entry["nivel"] in ("INFO", "WARN", "ERROR")


def test_contracts_parity_and_remediation(client):
    headers = {"X-API-KEY": "test-secret-key"}

    # 1. Movimientos contrato con tipo y movimiento
    res_post_mov = client.post(
        "/api/v1/movimientos",
        headers=headers,
        json={
            "proveedor_cliente": "Farmacia Test",
            "total": 55000,
            "categoria": "Salud",
            "tasa_iva": "10%",
            "movimiento": "Gasto",
            "comprobante": "Física Legal",
        },
    )
    assert res_post_mov.status_code == 200
    data_mov = res_post_mov.get_json()
    assert "tipo" in data_mov
    assert "movimiento" in data_mov
    assert data_mov["categoria"] == "Salud"

    # 2. Obligaciones snake_case
    res_ob = client.get("/api/v1/obligaciones", headers=headers)
    assert res_ob.status_code == 200
    obs = res_ob.get_json()
    if len(obs) > 0:
        primera = obs[0]
        assert "id" in primera
        assert "nombre" in primera
        assert "monto_inicial" in primera
        assert "saldo_actual" in primera
        assert "entidad" in primera
        assert "cuotas_totales" in primera
        assert "cuotas_restantes" in primera
        assert "dia_vencimiento" in primera

    # 3. Interpretación de aviso con fecha futura
    res_aviso = client.post(
        "/api/v1/ia/interpretar/aviso",
        headers=headers,
        json={"texto": "Reunión de balance el 25/11/2026 a las 15:00"},
    )
    assert res_aviso.status_code == 200
    aviso_data = res_aviso.get_json()
    assert "25/11/2026" in aviso_data["fecha_evento"]
    assert "15:00" in aviso_data["fecha_evento"]
    assert aviso_data["dias_restantes"] >= 1


def test_asistencia_materias_and_dual_cierre(client):
    headers = {"X-API-KEY": "test-secret-key"}
    # 1. GET /asistencia/materias
    res_mat = client.get("/api/v1/asistencia/materias", headers=headers)
    assert res_mat.status_code == 200
    materias = res_mat.get_json()
    assert isinstance(materias, list)
    assert len(materias) > 0

    # 2. Cierre Contable
    res_cierre_contable = client.post(
        "/api/v1/cierres/ejecutar",
        headers=headers,
        json={"hoja": "Octubre 2026", "tipo": "contable"},
    )
    assert res_cierre_contable.status_code == 200
    data_cierre = res_cierre_contable.get_json()
    assert "pdf_url" in data_cierre
    assert "cierre_contable" in data_cierre["pdf_url"]
    assert data_cierre["tipo"] == "contable"


def test_soporte_tickets_github_sync_dispatch(client, monkeypatch, tmp_path):
    headers = {"X-API-KEY": "test-secret-key"}
    fake_tickets = tmp_path / "tickets.json"
    fake_tickets.write_text("[]", encoding="utf-8")
    monkeypatch.setattr("api.blueprint.TICKETS_FILE", fake_tickets)

    with unittest.mock.patch(
        "services.github_service.GitHubIssueSyncService.create_github_issue"
    ) as mock_create_gh, unittest.mock.patch(
        "services.github_service.GitHubIssueSyncService.sync_ticket_status"
    ) as mock_sync_gh:
        # 1. Crear ticket y verificar dispatch hacia GitHub
        res_post = client.post(
            "/api/v1/soporte/tickets",
            headers=headers,
            json={
                "asunto": "Fallo sincronización",
                "descripcion": "Error al conectar con servidor",
                "origen": "app",
            },
        )
        assert res_post.status_code == 201
        ticket_id = res_post.get_json()["id"]
        mock_create_gh.assert_called_once()

        # 2. Cerrar ticket y verificar sync hacia GitHub
        res_patch = client.patch(
            f"/api/v1/soporte/tickets/{ticket_id}",
            headers=headers,
            json={"estado": "Cerrado", "resolucion": "Corregido en release"},
        )
        assert res_patch.status_code == 200
        mock_sync_gh.assert_called_once_with(
            ticket_id=ticket_id,
            nuevo_estado="Cerrado",
            resolucion="Corregido en release",
        )

        # 3. Resiliencia: Si GitHub falla por timeout, la API no se cae
        mock_sync_gh.side_effect = Exception("GitHub API Timeout")
        res_patch_error = client.patch(
            f"/api/v1/soporte/tickets/{ticket_id}",
            headers=headers,
            json={"estado": "Abierto"},
        )
        assert res_patch_error.status_code == 200
        assert res_patch_error.get_json()["estado"] == "Abierto"


def test_github_service_direct_unit_tests():
    from services.github_service import GitHubIssueSyncService

    # 1. Sin GITHUB_TOKEN configurado -> Retorna None/False sin hacer requests
    with unittest.mock.patch.dict(os.environ, {}, clear=True):
        assert GitHubIssueSyncService.is_configured() is False
        assert GitHubIssueSyncService.create_github_issue({"id": "TCK-1"}) is None
        assert (
            GitHubIssueSyncService.sync_ticket_status(
                "TCK-1", "Cerrado", "Fix", issue_number=10
            )
            is False
        )

    # 2. Con GITHUB_TOKEN -> Despacha requests correctamente
    with unittest.mock.patch.dict(
        os.environ, {"GITHUB_TOKEN": "mock-token", "GITHUB_REPO": "test/repo"}
    ), unittest.mock.patch("requests.post") as mock_post, unittest.mock.patch(
        "requests.patch"
    ) as mock_patch:
        # Mock de creación exitosa (201)
        mock_post.return_value.status_code = 201
        mock_post.return_value.json.return_value = {"number": 42}

        issue_num = GitHubIssueSyncService.create_github_issue(
            {"id": "TCK-10", "asunto": "Problema", "origen": "app"}
        )
        assert issue_num == 42
        mock_post.assert_called_once()

        # Mock de cierre exitoso (200)
        mock_patch.return_value.status_code = 200
        synced = GitHubIssueSyncService.sync_ticket_status(
            "TCK-10", "Cerrado", resolucion="Listo", issue_number=42
        )
        assert synced is True
        mock_patch.assert_called_once()


def test_telemetria_vigia_cooldown_and_resilience():
    from com.core.telemetry import (
        reportar_incidente_vigia,
        sanitizar_texto,
        _COOLDOWN_REGISTRY,
    )

    # 1. Sanitización de credenciales
    with unittest.mock.patch.dict(os.environ, {"TOKEN": "super_secret_telegram_token"}):
        sanitized = sanitizar_texto(
            "Error con token super_secret_telegram_token en ejecucion"
        )
        assert "[TOKEN_REDACTED]" in sanitized
        assert "super_secret_telegram_token" not in sanitized

    # 2. Sin token retorna False
    with unittest.mock.patch.dict(os.environ, {}, clear=True):
        assert (
            reportar_incidente_vigia("Error Test", "Detalle", origen="servidor")
            is False
        )

    # 3. Envío exitoso y registro en cooldown
    _COOLDOWN_REGISTRY.clear()
    with unittest.mock.patch.dict(
        os.environ, {"GITHUB_TOKEN": "mock-token"}
    ), unittest.mock.patch("requests.post") as mock_post:
        mock_post.return_value.status_code = 201
        res1 = reportar_incidente_vigia("Error Test", "Detalle", origen="servidor")
        assert res1 is True
        assert mock_post.call_count == 1

        # Segundo llamado idéntico dentro de los 30 min (1800s) debe ser bloqueado por cooldown
        res2 = reportar_incidente_vigia("Error Test", "Detalle", origen="servidor")
        assert res2 is False
        assert mock_post.call_count == 1  # No se disparó un nuevo request

    # 4. Degradación resiliente ante excepción de red (fail-safe, no propaga)
    _COOLDOWN_REGISTRY.clear()
    with unittest.mock.patch.dict(
        os.environ, {"GITHUB_TOKEN": "mock-token"}
    ), unittest.mock.patch(
        "requests.post", side_effect=Exception("Connection reset by peer")
    ):
        res_fail = reportar_incidente_vigia(
            "Fallo de red", "Detalle", origen="servidor"
        )
        assert res_fail is False


def test_asistencia_periodos_y_analiticas_endpoints(client):
    headers = {"X-API-KEY": "test-secret-key"}

    # 1. GET /asistencia/periodos
    with unittest.mock.patch("logic.logic.obtener_estado_periodos") as mock_periodos:
        mock_periodos.return_value = {
            "periodo_laboral": "Octubre 2026",
            "periodo_contable": "Octubre 2026",
            "sincronizados": True,
        }
        res_periodos = client.get("/api/v1/asistencia/periodos", headers=headers)
        assert res_periodos.status_code == 200
        data_periodos = res_periodos.get_json()
        assert data_periodos["periodo_laboral"] == "Octubre 2026"
        assert data_periodos["periodo_contable"] == "Octubre 2026"
        assert data_periodos["sincronizados"] is True

    # 2. GET /asistencia/analiticas
    with unittest.mock.patch(
        "logic.logic.AgenteAutonomoHoras.calcular_analiticas_asistencia"
    ) as mock_analiticas:
        mock_analiticas.return_value = (
            {
                "periodo": "Octubre 2026",
                "monto_por_hora": 14634,
                "dias_trabajados": 20,
                "total_horas_decimal": 160.0,
                "total_horas_formato": "160h 00m",
                "salario_acumulado_gs": 2341440,
                "horas_perdidas_decimal": 2.5,
                "horas_extras_decimal": 1.0,
                "balance_neto_decimal": -1.5,
                "horas_perdidas_formato": "2h 30m",
                "horas_extras_formato": "1h 00m",
                "balance_neto_formato": "-1h 30m",
                "promedio_horas_por_dia": 8.0,
            },
            None,
        )
        res_analiticas = client.get(
            "/api/v1/asistencia/analiticas?hoja=Octubre%202026", headers=headers
        )
        assert res_analiticas.status_code == 200
        data_analiticas = res_analiticas.get_json()
        assert data_analiticas["periodo"] == "Octubre 2026"
        assert data_analiticas["dias_trabajados"] == 20
        assert data_analiticas["total_horas_decimal"] == 160.0
        assert data_analiticas["horas_perdidas_formato"] == "2h 30m"
        assert data_analiticas["balance_neto_formato"] == "-1h 30m"


def test_asistencia_descarga_reportes_excel_y_pdf(client, tmp_path):
    headers = {"X-API-KEY": "test-secret-key"}

    fake_excel = tmp_path / "reporte_horas_test.xlsx"
    fake_excel.write_bytes(b"fake_xlsx_binary_content")

    fake_pdf = tmp_path / "reporte_horas_test.pdf"
    fake_pdf.write_bytes(b"%PDF-1.4 fake_pdf_binary_content")

    mock_datos_reporte = unittest.mock.MagicMock()

    with unittest.mock.patch(
        "logic.logic.AgenteAutonomoHoras.preparar_datos_reporte",
        return_value=(mock_datos_reporte, None),
    ):
        # 1. GET /asistencia/reporte/excel
        with unittest.mock.patch(
            "services.excel_service.ExcelReportService.generar_reporte_horas",
            return_value=str(fake_excel),
        ):
            res_excel = client.get(
                "/api/v1/asistencia/reporte/excel?saldo_anterior=100000",
                headers=headers,
            )
            assert res_excel.status_code == 200
            assert (
                res_excel.content_type
                == "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
            )
            assert res_excel.data == b"fake_xlsx_binary_content"

        # 2. GET /asistencia/reporte/pdf
        with unittest.mock.patch(
            "logic.pdf_service.PDFService.generar_reporte_generico",
            return_value=str(fake_pdf),
        ):
            res_pdf = client.get(
                "/api/v1/asistencia/reporte/pdf?descuento=50000", headers=headers
            )
            assert res_pdf.status_code == 200
            assert "application/pdf" in res_pdf.content_type


def test_paridad_gammamobile_nuevos_contratos(client):
    headers = {"X-API-KEY": "test-secret-key"}

    # 1. Alias "tipo": "Ingreso" y "monto" / "concepto" en POST /movimientos
    res_ingreso = client.post(
        "/api/v1/movimientos",
        headers=headers,
        json={
            "tipo": "Ingreso",
            "concepto": "Honorarios Consultoría",
            "monto": 2500000,
            "categoria": "Servicios",
        },
    )
    assert res_ingreso.status_code == 200
    data_ingreso = res_ingreso.get_json()
    assert data_ingreso["tipo"] == "Ingreso"
    assert data_ingreso["movimiento"] == "Ingreso"
    assert data_ingreso["total"] == 2500000

    # 2. Idempotencia y deduplicación por client_id
    res_dup1 = client.post(
        "/api/v1/movimientos",
        headers=headers,
        json={
            "tipo": "Gasto",
            "concepto": "Combustible",
            "monto": 100000,
            "clientId": "unique-mobile-uuid-1234",
        },
    )
    assert res_dup1.status_code == 200

    res_dup2 = client.post(
        "/api/v1/movimientos",
        headers=headers,
        json={
            "tipo": "Gasto",
            "concepto": "Combustible",
            "monto": 100000,
            "clientId": "unique-mobile-uuid-1234",
        },
    )
    assert res_dup2.status_code == 200
    assert res_dup2.get_json().get("duplicado_evitado") is True

    # 3. GET /asistencia/cierres
    res_cierres = client.get("/api/v1/asistencia/cierres", headers=headers)
    assert res_cierres.status_code == 200
    data_cierres = res_cierres.get_json()
    assert data_cierres["status"] == "ok"
    assert isinstance(data_cierres["cierres"], list)
