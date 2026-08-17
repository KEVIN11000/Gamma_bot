from __future__ import annotations
from typing import Any
import os
import sys
import unittest
from unittest.mock import MagicMock, patch, mock_open
import json

# Ensure project root is in path
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)

from logic.pdf_service import PDFService, DatosReporte
from logic.ai_service import AIService
from logic.financiero import AgenteFinanciero
from logic.logic import AgenteAutonomoHoras, EstadoGestor
from com.core.security import get_authorized_users, auth_required, verificar_usuario_manual
from logic.cron_jobs import (
    alerta_asesor_financiero,
    informe_estadistico_mensual,
    rotar_logs,
    resumen_semanal
)
from flask_app import app


class TestPDFService(unittest.TestCase):
    def test_generar_reporte_generico_exito(self):
        datos = DatosReporte(
            titulo="TEST TITULO",
            subtitulo="Test Subtitulo",
            encabezados=["Fecha", "Tipo", "Monto"],
            filas=[["13/08/2026", "Gasto", "Gs. 50.000"]],
            lineas_resumen=[["Total Gastos", "Gs. 50.000"]],
            nombre_archivo="test_reporte.pdf"
        )
        ruta, msg = PDFService.generar_reporte_generico(datos)
        self.assertIsNotNone(ruta)
        self.assertTrue(os.path.exists(ruta))
        self.assertIn("✅ Reporte generado", msg)
        # Clean up
        if ruta and os.path.exists(ruta):
            os.remove(ruta)

    def test_generar_reporte_generico_sin_filas(self):
        datos = DatosReporte(
            titulo="TEST VACIO",
            subtitulo="Vacio",
            encabezados=[],
            filas=[],
            lineas_resumen=[],
            nombre_archivo="test_vacio.pdf"
        )
        ruta, msg = PDFService.generar_reporte_generico(datos)
        self.assertIsNotNone(ruta)
        self.assertTrue(os.path.exists(ruta))
        if ruta and os.path.exists(ruta):
            os.remove(ruta)


class TestAgenteFinanciero(unittest.TestCase):
    def setUp(self):
        self.agente = AgenteFinanciero(spreadsheet_id="test_sheet_id")

    def test_limpiar_monto(self):
        self.assertEqual(self.agente._limpiar_monto("Gs. 50.000"), 50000)
        self.assertEqual(self.agente._limpiar_monto("-15000"), -15000)
        self.assertEqual(self.agente._limpiar_monto(None), 0)
        self.assertEqual(self.agente._limpiar_monto(""), 0)
        self.assertEqual(self.agente._limpiar_monto("texto_sin_numeros"), 0)

    @patch.object(AgenteFinanciero, 'ws')
    def test_registrar_movimiento_duplicado(self, mock_ws):
        mock_ws.col_values.return_value = ["Nro Factura", "F-001", "F-002"]
        datos = {
            "fecha": "13/08",
            "tipo_movimiento": "Gasto",
            "proveedor_cliente": "Empresa X",
            "nro_factura": "F-001",
            "neto": 10000,
            "iva": 0,
            "total": 10000,
            "categoria": "Varios",
            "comprobante": "No Legal"
        }
        res = self.agente.registrar_movimiento(datos)
        self.assertIn("Factura Duplicada", res)

    @patch.object(AgenteFinanciero, 'ws')
    def test_registrar_movimiento_sanitizacion_formula(self, mock_ws):
        mock_ws.col_values.return_value = []
        datos = {
            "fecha": "=SUM(A1:A10)",
            "tipo_movimiento": "Ingreso",
            "proveedor_cliente": "+123456",
            "nro_factura": "@malicious",
            "neto": 50000,
            "iva": 0,
            "total": 50000,
            "categoria": "Sueldo",
            "comprobante": "Virtual Legal"
        }
        self.agente.registrar_movimiento(datos)
        mock_ws.update.assert_called_once()
        args, _ = mock_ws.update.call_args
        valores = args[1][0]
        # Check formulas were sanitized with leading single quote
        self.assertTrue(valores[0].startswith("'="))
        self.assertTrue(valores[2].startswith("'+"))
        self.assertTrue(valores[3].startswith("'@"))

    @patch.object(AgenteFinanciero, 'ws')
    def test_obtener_balance(self, mock_ws):
        mock_ws.get_all_values.return_value = [
            ["Fecha", "Movimiento", "Prov", "Nro", "Neto", "IVA", "Total"],
            ["10/08", "Ingreso", "Cliente A", "S/N", "100000", "0", "100000"],
            ["11/08", "Gasto", "Proveedor B", "S/N", "30000", "0", "30000"],
            ["12/08", "Gasto", "Proveedor C", "S/N", "20000", "0", "20000"],
        ]
        balance = self.agente.obtener_balance()
        self.assertIsNotNone(balance)
        self.assertEqual(balance["ingresos"], 100000)
        self.assertEqual(balance["gastos"], 50000)
        self.assertEqual(balance["flujo_neto"], 50000)


class TestAgenteAutonomoHoras(unittest.TestCase):
    def test_parsear_horas_a_decimal(self):
        self.assertEqual(AgenteAutonomoHoras._parsear_horas_a_decimal("8:30"), 8.5)
        self.assertEqual(AgenteAutonomoHoras._parsear_horas_a_decimal("8.5"), 8.5)
        self.assertEqual(AgenteAutonomoHoras._parsear_horas_a_decimal("8,5"), 8.5)
        self.assertEqual(AgenteAutonomoHoras._parsear_horas_a_decimal(""), 0.0)
        self.assertEqual(AgenteAutonomoHoras._parsear_horas_a_decimal("inválido"), 0.0)

    @patch.object(AgenteAutonomoHoras, 'wb')
    def test_preparar_datos_reporte_descuento(self, mock_wb):
        mock_ws = MagicMock()
        mock_ws.title = "Agosto 2026"
        mock_ws.get_all_values.return_value = [
            ["Dia", "Fecha", "Entrada", "Salida Almuerzo", "Entrada Almuerzo", "Salida", "Horas"],
            ["Lunes", "10/08/2026", "08:00", "12:00", "13:00", "17:00", "8:00"],
            ["Martes", "11/08/2026", "08:00", "12:00", "13:00", "17:00", "8:00"],
        ]
        mock_wb.worksheets.return_value = [mock_ws]
        
        agente = AgenteAutonomoHoras("test_id")
        datos, err = agente.preparar_datos_reporte(descuento=50000)
        self.assertIsNone(err)
        self.assertIsNotNone(datos)
        self.assertEqual(datos.subtitulo, "Agosto 2026")
        
        # Check discount is reflected in summary
        resumen = datos.lineas_resumen
        conceptos = [r[0] for r in resumen]
        self.assertIn("Descuentos aplicados", conceptos)
        self.assertIn("Salario neto a cobrar", conceptos)


class TestCronJobs(unittest.TestCase):
    @patch('logic.ai_service.AIService.generar_insights_financieros')
    def test_alerta_asesor_financiero(self, mock_gen_insights):
        mock_gen_insights.return_value = "💡 Tip: Reducir gastos en comida fuera de casa."
        
        mock_gamma = MagicMock()
        mock_gamma.bot = MagicMock()
        mock_gamma.agente_financiero = MagicMock()
        
        # Mock preparar_datos_reporte
        reporte_mock = DatosReporte(
            titulo="T", subtitulo="S", encabezados=[],
            filas=[["13/08", "Gasto", "McDonalds", "S/N", "Gs. 50.000", "Comida"]],
            lineas_resumen=[], nombre_archivo="f.pdf"
        )
        mock_gamma.agente_financiero.preparar_datos_reporte.return_value = (reporte_mock, None)
        mock_gamma.agente_financiero.obtener_balance.return_value = {"ingresos": 1000000, "gastos": 50000, "flujo_neto": 950000}
        
        exito = alerta_asesor_financiero(mock_gamma, "123456")
        self.assertTrue(exito)
        mock_gamma.bot.send_message.assert_called_once()
        args, kwargs = mock_gamma.bot.send_message.call_args
        self.assertEqual(args[0], "123456")
        self.assertIn("GAMMA Asesor IA", args[1])
        self.assertIn("💡 Tip", args[1])

    @patch('logic.pdf_service.PDFService.generar_reporte_generico')
    def test_informe_estadistico_mensual(self, mock_gen_pdf):
        def side_effect_pdf(datos):
            path = os.path.join(BASE_DIR, f"test_temp_{datos.nombre_archivo}")
            with open(path, "w") as f:
                f.write("fake pdf")
            return (path, "OK")

        mock_gen_pdf.side_effect = side_effect_pdf
        
        mock_gamma = MagicMock()
        mock_gamma.bot = MagicMock()
        
        reporte_h = DatosReporte("H", "S", [], [], [], "h.pdf")
        reporte_f = DatosReporte("F", "S", [], [], [], "f.pdf")
        
        mock_gamma.agente_excel.preparar_datos_reporte.return_value = (reporte_h, None)
        mock_gamma.agente_financiero.preparar_datos_reporte.return_value = (reporte_f, None)
        
        exito = informe_estadistico_mensual(mock_gamma, "123456")
        self.assertTrue(exito)
        self.assertEqual(mock_gamma.bot.send_document.call_count, 2)


class TestSecurity(unittest.TestCase):
    @patch.dict(os.environ, {"CHAT_ID": "123456, -987654"})
    def test_get_authorized_users(self):
        users = get_authorized_users()
        self.assertIn(123456, users)
        self.assertIn(-987654, users)
        self.assertNotIn(999999, users)

    @patch.dict(os.environ, {"CHAT_ID": "100"})
    def test_auth_required_decorator(self):
        mock_bot = MagicMock()
        
        @auth_required(mock_bot)
        def dummy_handler(msg):
            return "SUCCESS"

        # Authorized user
        msg_auth = MagicMock()
        del msg_auth.data
        msg_auth.from_user.id = 100
        res = dummy_handler(msg_auth)
        self.assertEqual(res, "SUCCESS")

        # Unauthorized user
        msg_unauth = MagicMock(spec=['from_user'])
        msg_unauth.from_user.id = 999
        msg_unauth.from_user.username = "intruder"
        res_unauth = dummy_handler(msg_unauth)
        self.assertIsNone(res_unauth)
        mock_bot.reply_to.assert_called_once()


class TestFlaskEndpoints(unittest.TestCase):
    def setUp(self):
        self.app = app.test_client()
        self.app.testing = True

    def test_home_endpoint(self):
        resp = self.app.get('/')
        self.assertEqual(resp.status_code, 200)
        self.assertIn(b"Bot de Marcaci\xc3\xb3n Activo", resp.data)

    @patch('logic.cron_jobs.informe_estadistico_mensual')
    def test_cron_cierre_mensual_endpoint(self, mock_informe):
        mock_informe.return_value = True
        with patch.dict(os.environ, {"CHAT_ID": "123456", "CRON_SECRET": ""}):
            resp = self.app.get('/cron/cierre-mensual')
            self.assertEqual(resp.status_code, 200)
            self.assertIn(b"Informe estad\xc3\xadstico ejecutado", resp.data)

    @patch('logic.cron_jobs.alerta_asesor_financiero')
    def test_cron_asesor_ia_endpoint(self, mock_asesor):
        mock_asesor.return_value = True
        with patch.dict(os.environ, {"CHAT_ID": "123456", "CRON_SECRET": "secret123"}):
            # Without secret header -> 403 Forbidden
            resp_no_secret = self.app.get('/cron/asesor-ia')
            self.assertEqual(resp_no_secret.status_code, 403)
            
            # With secret header -> 200 OK
            resp_with_secret = self.app.get('/cron/asesor-ia', headers={"X-Cron-Secret": "secret123"})
            self.assertEqual(resp_with_secret.status_code, 200)
            self.assertIn(b"Insights del Asesor IA enviados", resp_with_secret.data)


if __name__ == '__main__':
    unittest.main()
