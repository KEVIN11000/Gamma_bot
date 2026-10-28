import pytest
from unittest.mock import MagicMock, patch, mock_open
from telebot.types import Message, Chat, InlineKeyboardMarkup

from services.asistencia_service import (
    iniciar_flujo_reporte_horas,
    generar_y_enviar_reporte_financiero,
    capturar_monto_descuento,
    generar_y_enviar_reporte,
    capturar_descuento_reporte,
    generar_y_enviar_reporte_por_hoja,
)


@pytest.fixture
def mock_bot():
    return MagicMock()


@pytest.fixture
def mock_gamma_app():
    return MagicMock()


@pytest.fixture
def mock_message():
    message = MagicMock(spec=Message)
    message.chat = MagicMock(spec=Chat)
    message.chat.id = 123
    message.message_id = 456
    message.text = "1000"
    return message


def test_iniciar_flujo_reporte_horas_sin_nombres(
    mock_bot, mock_gamma_app, mock_message
):
    mock_gamma_app.agente_excel.obtener_nombres_hojas.return_value = []

    # Not callback
    iniciar_flujo_reporte_horas(
        mock_message, mock_bot, mock_gamma_app, is_callback=False
    )
    mock_bot.reply_to.assert_called_with(
        mock_message,
        "❌ No hay períodos anteriores disponibles para generar un reporte.",
    )

    # Is callback
    iniciar_flujo_reporte_horas(
        mock_message, mock_bot, mock_gamma_app, is_callback=True
    )
    mock_bot.edit_message_text.assert_called_with(
        "❌ No hay períodos anteriores disponibles para generar un reporte.",
        mock_message.chat.id,
        mock_message.message_id,
    )


def test_iniciar_flujo_reporte_horas_con_nombres(
    mock_bot, mock_gamma_app, mock_message
):
    mock_gamma_app.agente_excel.obtener_nombres_hojas.return_value = [
        "Hoja1",
        "Hoja2_muylargaaaaaaaaaaaaaaaaaaaaaaa",
    ]

    iniciar_flujo_reporte_horas(
        mock_message, mock_bot, mock_gamma_app, is_callback=False
    )
    mock_bot.reply_to.assert_called_once()
    args, kwargs = mock_bot.reply_to.call_args
    assert "¿De qué período querés el reporte" in args[1]
    assert isinstance(kwargs["reply_markup"], InlineKeyboardMarkup)

    mock_bot.reset_mock()
    iniciar_flujo_reporte_horas(
        mock_message, mock_bot, mock_gamma_app, is_callback=True
    )
    mock_bot.edit_message_text.assert_called_once()


@patch("services.asistencia_service.PDFService")
def test_generar_y_enviar_reporte_financiero_error(
    mock_pdf_service, mock_bot, mock_gamma_app, mock_message
):
    mock_gamma_app.agente_financiero.preparar_datos_reporte.return_value = (
        None,
        "Error al preparar",
    )

    # Not callback
    generar_y_enviar_reporte_financiero(
        mock_bot, mock_gamma_app, mock_message, is_callback=False
    )
    mock_bot.send_message.assert_any_call(mock_message.chat.id, "Error al preparar")

    mock_bot.reset_mock()
    # Callback
    generar_y_enviar_reporte_financiero(
        mock_bot, mock_gamma_app, mock_message, is_callback=True
    )
    mock_bot.edit_message_text.assert_called_with(
        "📄 Procesando datos financieros y armando PDF...",
        mock_message.chat.id,
        mock_message.message_id,
    )
    mock_bot.send_message.assert_called_with(mock_message.chat.id, "Error al preparar")


@patch("services.asistencia_service.PDFService")
def test_generar_y_enviar_reporte_financiero_exito_sin_pdf(
    mock_pdf_service, mock_bot, mock_gamma_app, mock_message
):
    mock_gamma_app.agente_financiero.preparar_datos_reporte.return_value = (
        {"datos": 1},
        None,
    )
    mock_pdf_service.generar_reporte_generico.return_value = (
        None,
        "Mensaje de pdf error",
    )

    generar_y_enviar_reporte_financiero(
        mock_bot, mock_gamma_app, mock_message, is_callback=False
    )
    mock_bot.send_message.assert_called_with(
        mock_message.chat.id, "Mensaje de pdf error"
    )


@patch("services.asistencia_service.PDFService")
@patch("builtins.open", new_callable=mock_open, read_data=b"data")
def test_generar_y_enviar_reporte_financiero_exito_con_pdf(
    mock_file, mock_pdf_service, mock_bot, mock_gamma_app, mock_message
):
    mock_gamma_app.agente_financiero.preparar_datos_reporte.return_value = (
        {"datos": 1},
        None,
    )
    mock_pdf_service.generar_reporte_generico.return_value = (
        "/ruta/archivo.pdf",
        "Reporte generado",
    )

    generar_y_enviar_reporte_financiero(
        mock_bot, mock_gamma_app, mock_message, is_callback=False
    )
    mock_bot.send_document.assert_called_once()
    assert mock_bot.send_document.call_args[1]["caption"] == "📊 Reporte generado"


@patch("services.asistencia_service.verificar_usuario_manual")
@patch("services.asistencia_service.generar_y_enviar_reporte")
@patch("services.asistencia_service.EstadoGestor")
def test_capturar_monto_descuento_valido(
    mock_estado, mock_generar, mock_verificar, mock_bot, mock_gamma_app, mock_message
):
    mock_verificar.return_value = True
    mock_estado.pop.return_value = False
    mock_message.text = "1.500,50"
    capturar_monto_descuento(mock_message, mock_bot, mock_gamma_app)
    mock_generar.assert_called_once_with(
        mock_bot, mock_gamma_app, mock_message, descuento=150050.0, incluir_iva=False
    )


@patch("services.asistencia_service.verificar_usuario_manual")
def test_capturar_monto_descuento_invalido(
    mock_verificar, mock_bot, mock_gamma_app, mock_message
):
    mock_verificar.return_value = True

    # Texto vacio
    mock_message.text = None
    capturar_monto_descuento(mock_message, mock_bot, mock_gamma_app)
    mock_bot.reply_to.assert_called_with(
        mock_message,
        "❌ Por favor, enviá un texto con el número. (No se admiten stickers ni imágenes)",
    )

    # No numerico
    mock_message.text = "abc"
    capturar_monto_descuento(mock_message, mock_bot, mock_gamma_app)
    assert "El monto debe ser numérico" in mock_bot.reply_to.call_args[0][1]

    # No autorizado
    mock_verificar.return_value = False
    mock_bot.reset_mock()
    capturar_monto_descuento(mock_message, mock_bot, mock_gamma_app)
    mock_bot.reply_to.assert_not_called()


@patch("services.asistencia_service.PDFService")
@patch("builtins.open", new_callable=mock_open, read_data=b"data")
def test_generar_y_enviar_reporte(
    mock_file, mock_pdf_service, mock_bot, mock_gamma_app, mock_message
):
    mock_gamma_app.agente_excel.preparar_datos_reporte.return_value = ({"d": 1}, None)
    mock_pdf_service.generar_reporte_generico.return_value = (
        "/ruta/test.pdf",
        "PDF listo",
    )

    generar_y_enviar_reporte(mock_bot, mock_gamma_app, mock_message, 100.0)
    mock_gamma_app.agente_excel.preparar_datos_reporte.assert_called_with(
        descuento=100.0, incluir_iva=False
    )
    mock_bot.send_document.assert_called_once()

    # Con error
    mock_gamma_app.agente_excel.preparar_datos_reporte.return_value = (
        None,
        "Error excel",
    )
    mock_bot.reset_mock()
    generar_y_enviar_reporte(mock_bot, mock_gamma_app, mock_message, 100.0)
    mock_bot.send_message.assert_called_with(mock_message.chat.id, "Error excel")

    # Sin archivo pdf
    mock_gamma_app.agente_excel.preparar_datos_reporte.return_value = ({"d": 1}, None)
    mock_pdf_service.generar_reporte_generico.return_value = (None, "Fallo PDF")
    mock_bot.reset_mock()
    generar_y_enviar_reporte(mock_bot, mock_gamma_app, mock_message, 100.0)
    mock_bot.send_message.assert_called_with(mock_message.chat.id, "Fallo PDF")


@patch("services.asistencia_service.verificar_usuario_manual")
@patch("services.asistencia_service.EstadoGestor")
@patch("services.asistencia_service.generar_y_enviar_reporte_por_hoja")
def test_capturar_descuento_reporte_valido(
    mock_generar_hoja,
    mock_estado,
    mock_verificar,
    mock_bot,
    mock_gamma_app,
    mock_message,
):
    mock_verificar.return_value = True
    # First pop: nombre_hoja; second pop: iva flag
    mock_estado.pop.side_effect = ["Hoja1", False]
    mock_message.text = "200"

    capturar_descuento_reporte(mock_message, mock_bot, mock_gamma_app)
    mock_generar_hoja.assert_called_once_with(
        mock_bot,
        mock_gamma_app,
        mock_message,
        "Hoja1",
        descuento=200.0,
        incluir_iva=False,
    )


@patch("services.asistencia_service.verificar_usuario_manual")
@patch("services.asistencia_service.EstadoGestor")
def test_capturar_descuento_reporte_errores(
    mock_estado, mock_verificar, mock_bot, mock_gamma_app, mock_message
):
    mock_verificar.return_value = True

    # Texto vacio
    mock_message.text = None
    capturar_descuento_reporte(mock_message, mock_bot, mock_gamma_app)
    mock_bot.reply_to.assert_called_with(
        mock_message, "❌ Por favor, enviá un texto numérico. (No se admiten archivos)"
    )

    # Estado vacio
    mock_message.text = "100"
    mock_estado.pop.return_value = None
    capturar_descuento_reporte(mock_message, mock_bot, mock_gamma_app)
    mock_bot.reply_to.assert_called_with(
        mock_message, "❌ Sesión expirada. Ejecutá /reporte de nuevo."
    )

    # Error de valor
    mock_estado.pop.return_value = "Hoja1"
    mock_message.text = "abc"
    capturar_descuento_reporte(mock_message, mock_bot, mock_gamma_app)
    assert "El monto debe ser numérico" in mock_bot.reply_to.call_args[0][1]

    # Usuario no verificado
    mock_verificar.return_value = False
    mock_bot.reset_mock()
    capturar_descuento_reporte(mock_message, mock_bot, mock_gamma_app)
    mock_bot.reply_to.assert_not_called()


@patch("services.asistencia_service.PDFService")
@patch("builtins.open", new_callable=mock_open, read_data=b"data")
def test_generar_y_enviar_reporte_por_hoja(
    mock_file, mock_pdf_service, mock_bot, mock_gamma_app, mock_message
):
    # Exito
    mock_gamma_app.agente_excel.preparar_datos_reporte.return_value = ({"h": 1}, None)
    mock_pdf_service.generar_reporte_generico.return_value = (
        "/ruta/hoja.pdf",
        "PDF listo hoja",
    )

    generar_y_enviar_reporte_por_hoja(
        mock_bot, mock_gamma_app, mock_message, "Hoja1", 50.0
    )
    mock_gamma_app.agente_excel.preparar_datos_reporte.assert_called_with(
        nombre_hoja="Hoja1", descuento=50.0, incluir_iva=False
    )
    mock_bot.send_document.assert_called_once()

    # Error excel
    mock_bot.reset_mock()
    mock_gamma_app.agente_excel.preparar_datos_reporte.return_value = (
        None,
        "Error hoja excel",
    )
    generar_y_enviar_reporte_por_hoja(
        mock_bot, mock_gamma_app, mock_message, "Hoja1", 50.0
    )
    mock_bot.send_message.assert_called_with(mock_message.chat.id, "Error hoja excel")

    # Sin archivo pdf
    mock_bot.reset_mock()
    mock_gamma_app.agente_excel.preparar_datos_reporte.return_value = ({"h": 1}, None)
    mock_pdf_service.generar_reporte_generico.return_value = (
        None,
        "Mensaje de pdf error",
    )
    generar_y_enviar_reporte_por_hoja(
        mock_bot, mock_gamma_app, mock_message, "Hoja1", 50.0
    )
    mock_bot.send_message.assert_called_with(
        mock_message.chat.id, "Mensaje de pdf error"
    )


def test_agente_horas_preparar_datos_reporte_y_cuadro_resumen():
    from logic.logic import AgenteAutonomoHoras

    agente = AgenteAutonomoHoras("test_spreadsheet_id")
    mock_wb = MagicMock()
    mock_hoja = MagicMock()
    mock_hoja.title = "Octubre 2026"
    mock_hoja.get_all_values.return_value = [
        [
            "Día",
            "Fecha",
            "Hora entrada",
            "Salgo almuerzo",
            "Vuelta almuerzo",
            "Hora salida",
            "Horas",
        ],
        ["Martes", "29/09/2026", "09:10", "12:47", "13:16", "17:05", "7.43"],
        ["Jueves", "01/10/2026", "08:30", "12:19", "12:59", "17:05", "7.92"],
        ["Lunes", "05/10/2026", "08:50", "12:19", "13:22", "17:05", "7.23"],
    ]
    mock_wb.worksheets.return_value = [mock_hoja]
    mock_wb.worksheet.return_value = mock_hoja
    agente._wb = mock_wb
    agente._ws = mock_hoja

    # Caso 1: Sin saldo anterior ni descuento
    reporte, error = agente.preparar_datos_reporte(
        descuento=0, saldo_anterior=0, incluir_iva=True
    )
    assert error is None
    conceptos = [c[0] for c in reporte.lineas_resumen]
    assert conceptos == [
        "mes",
        "hora",
        "por Horas",
        "IVA 10%",
        "INCLUIDO",
        "FACTURA",
    ]
    assert "SALDO ANTERIOR" not in conceptos
    assert "Descuento" not in conceptos
    assert reporte.resumen_calculado["mes"] == 22.6

    # Caso 2: Con SALDO ANTERIOR (> 0)
    rep_saldo, _ = agente.preparar_datos_reporte(
        descuento=0, saldo_anterior=177364, incluir_iva=True
    )
    conceptos_saldo = [c[0] for c in rep_saldo.lineas_resumen]
    assert "SALDO ANTERIOR" in conceptos_saldo
    assert rep_saldo.resumen_calculado["saldo_anterior"] == 177364
    assert (
        rep_saldo.resumen_calculado["factura"]
        == rep_saldo.resumen_calculado["incluido"] + 177364
    )

    # Caso 3: Con Descuento (> 0)
    rep_desc, _ = agente.preparar_datos_reporte(
        descuento=50000, saldo_anterior=0, incluir_iva=True
    )
    conceptos_desc = [c[0] for c in rep_desc.lineas_resumen]
    assert "Descuento" in conceptos_desc
    assert rep_desc.resumen_calculado["descuento"] == 50000
    assert (
        rep_desc.resumen_calculado["factura"]
        == rep_desc.resumen_calculado["incluido"] - 50000
    )

    # Caso 4: Escritura en Sheet
    ok, msg = agente.escribir_cuadro_resumen_en_sheet(saldo_anterior=177364)
    assert ok is True
    assert "Cuadro resumen escrito" in msg
    mock_hoja.update.assert_called_once()


def test_formatear_horas_decimal():
    from logic.logic import AgenteAutonomoHoras

    assert AgenteAutonomoHoras.formatear_horas_decimal(107.3) == "107h 18m"
    assert AgenteAutonomoHoras.formatear_horas_decimal(8.0) == "8h 00m"
    assert AgenteAutonomoHoras.formatear_horas_decimal(0.0) == "0h 00m"
    assert AgenteAutonomoHoras.formatear_horas_decimal(-1.42) == "-1h 25m"
    assert AgenteAutonomoHoras.formatear_horas_decimal(0.08) == "0h 05m"
    assert AgenteAutonomoHoras.formatear_horas_decimal(-0.001) == "0h 00m"
    assert AgenteAutonomoHoras.formatear_horas_decimal(1.9999) == "2h 00m"


def test_calcular_analiticas_asistencia_metrica_exacta(monkeypatch):
    from logic.logic import AgenteAutonomoHoras

    monkeypatch.setenv("MONTO_POR_HORA", "14634")
    agente = AgenteAutonomoHoras("test_spreadsheet_id")
    mock_hoja = MagicMock()
    mock_hoja.title = "Octubre 2026"

    # Filas con:
    # - Día 1: 7.5h (déficit 0.5h)
    # - Día 2: 9.0h (superávit 1.0h)
    # - Día 3: 8.0h (exacto, 0 déficit, 0 superávit)
    # - Día 4: 6.0h (déficit 2.0h)
    # - Día 5: 0.0h / libre (no cuenta como trabajado, no genera déficit)
    # - Fila resumen residual previa (debe ser ignorada)
    mock_hoja.get_all_values.return_value = [
        [
            "Día",
            "Fecha",
            "Hora entrada",
            "Salgo almuerzo",
            "Vuelta almuerzo",
            "Hora salida",
            "Horas",
        ],
        ["Lunes", "01/10/2026", "08:30", "12:00", "13:00", "17:00", "7.50"],
        ["Martes", "02/10/2026", "08:00", "12:00", "13:00", "18:00", "9.00"],
        ["Miércoles", "03/10/2026", "08:00", "12:00", "13:00", "17:00", "8.00"],
        ["Jueves", "04/10/2026", "09:00", "12:00", "13:00", "16:00", "6.00"],
        ["Viernes", "05/10/2026", "", "", "", "", "0"],
        ["Resumen", "Cantidades", "", "", "", "", ""],
        ["mes", "30.5", "", "", "", "", ""],
        ["FACTURA", "$446,337", "", "", "", "", ""],
    ]

    mock_wb = MagicMock()
    mock_wb.worksheet.return_value = mock_hoja
    agente._wb = mock_wb
    agente._ws = mock_hoja

    analiticas, error = agente.calcular_analiticas_asistencia()
    assert error is None
    assert analiticas is not None

    # Verificaciones matemáticas exactas:
    # Total horas: 7.5 + 9.0 + 8.0 + 6.0 = 30.5
    # Días trabajados: 4 (el día 5 con 0 horas se ignora)
    assert analiticas["periodo"] == "Octubre 2026"
    assert analiticas["dias_trabajados"] == 4
    assert analiticas["total_horas_decimal"] == 30.5
    assert analiticas["total_horas_formato"] == "30h 30m"

    # Déficit esperado:
    # Día 1: 8.0 - 7.5 = 0.5
    # Día 4: 8.0 - 6.0 = 2.0
    # Total perdidas = 2.5
    assert analiticas["horas_perdidas_decimal"] == 2.5
    assert analiticas["horas_perdidas_formato"] == "2h 30m"

    # Superávit esperado:
    # Día 2: 9.0 - 8.0 = 1.0
    # Total extras = 1.0
    assert analiticas["horas_extras_decimal"] == 1.0
    assert analiticas["horas_extras_formato"] == "1h 00m"

    # Balance neto: 30.5 - (4 * 8.0) = 30.5 - 32.0 = -1.5h
    assert analiticas["balance_neto_decimal"] == -1.5
    assert analiticas["balance_neto_formato"] == "-1h 30m"

    # Promedio por día: 30.5 / 4 = 7.625 -> 7.62
    assert analiticas["promedio_horas_por_dia"] == 7.62

    # Salario acumulado: round(30.5 * 14634) = 446337
    assert analiticas["salario_acumulado_gs"] == 446337


def test_calcular_analiticas_asistencia_errores_y_vacio():
    from logic.logic import AgenteAutonomoHoras

    agente = AgenteAutonomoHoras("test_spreadsheet_id")
    mock_hoja = MagicMock()
    mock_hoja.title = "Noviembre 2026"

    # Hoja vacía
    mock_hoja.get_all_values.return_value = []
    mock_wb = MagicMock()
    mock_wb.worksheet.return_value = mock_hoja
    agente._wb = mock_wb
    agente._ws = mock_hoja

    res, err = agente.calcular_analiticas_asistencia("Noviembre 2026")
    assert res is None
    assert "vacía" in err

    # Hoja sin columna horas
    mock_hoja.get_all_values.return_value = [["Col1", "Col2"]]
    res, err = agente.calcular_analiticas_asistencia("Noviembre 2026")
    assert res is None
    assert "columna de horas" in err


def test_obtener_estado_periodos_sincronizados(tmp_path):
    from logic.logic import obtener_estado_periodos

    txt_file = tmp_path / "periodo_actual.txt"
    txt_file.write_text("Octubre 2026", encoding="utf-8")

    mock_repo = MagicMock()
    mock_repo.get_last_cierre_mensual.return_value = {
        "Mes": "09",
        "Anio": "2026",
    }

    res = obtener_estado_periodos(repo=mock_repo, base_path=tmp_path)
    assert res["periodo_laboral"] == "Octubre 2026"
    assert res["periodo_contable"] == "Octubre 2026"
    assert res["sincronizados"] is True


def test_obtener_estado_periodos_desincronizados(tmp_path):
    from logic.logic import obtener_estado_periodos

    txt_file = tmp_path / "periodo_actual.txt"
    txt_file.write_text("Noviembre 2026", encoding="utf-8")

    mock_repo = MagicMock()
    mock_repo.get_last_cierre_mensual.return_value = {
        "Mes": "09",
        "Anio": "2026",
    }

    res = obtener_estado_periodos(repo=mock_repo, base_path=tmp_path)
    assert res["periodo_laboral"] == "Noviembre 2026"
    assert res["periodo_contable"] == "Octubre 2026"
    assert res["sincronizados"] is False


def test_obtener_estado_periodos_normalizacion_septiembre(tmp_path):
    from logic.logic import obtener_estado_periodos

    txt_file = tmp_path / "periodo_actual.txt"
    txt_file.write_text("Septiembre 2026", encoding="utf-8")

    mock_repo = MagicMock()
    mock_repo.get_last_cierre_mensual.return_value = {
        "Mes": "08",
        "Anio": "2026",
    }

    res = obtener_estado_periodos(repo=mock_repo, base_path=tmp_path)
    assert res["periodo_laboral"] == "Septiembre 2026"
    assert res["periodo_contable"] == "Setiembre 2026"
    assert res["sincronizados"] is True


def test_obtener_estado_periodos_desde_movimientos_y_agentes(tmp_path):
    from logic.logic import AgenteAutonomoHoras
    from logic.financiero import AgenteFinanciero

    txt_file = tmp_path / "periodo_actual.txt"
    txt_file.write_text("Octubre 2026", encoding="utf-8")

    mock_repo = MagicMock()
    mock_repo.get_last_cierre_mensual.return_value = {}
    mock_repo.get_all_movimientos.return_value = [
        {"Fecha": "15/10/2026", "Mes": "10/2026"}
    ]

    agente_horas = AgenteAutonomoHoras("test_spreadsheet_id")
    res_horas = agente_horas.obtener_estado_periodos(repo=mock_repo, base_path=tmp_path)
    assert res_horas["periodo_laboral"] == "Octubre 2026"
    assert res_horas["periodo_contable"] == "Octubre 2026"
    assert res_horas["sincronizados"] is True

    agente_fin = AgenteFinanciero("test_spreadsheet_id")
    res_fin = agente_fin.obtener_estado_periodos(repo=mock_repo, base_path=tmp_path)
    assert res_fin["periodo_laboral"] == "Octubre 2026"
    assert res_fin["periodo_contable"] == "Octubre 2026"
    assert res_fin["sincronizados"] is True
