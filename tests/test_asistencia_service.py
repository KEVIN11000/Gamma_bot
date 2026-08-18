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


def test_iniciar_flujo_reporte_horas_sin_nombres(mock_bot, mock_gamma_app, mock_message):
    mock_gamma_app.agente_excel.obtener_nombres_hojas.return_value = []
    
    # Not callback
    iniciar_flujo_reporte_horas(mock_message, mock_bot, mock_gamma_app, is_callback=False)
    mock_bot.reply_to.assert_called_with(mock_message, "❌ No hay períodos anteriores disponibles para generar un reporte.")
    
    # Is callback
    iniciar_flujo_reporte_horas(mock_message, mock_bot, mock_gamma_app, is_callback=True)
    mock_bot.edit_message_text.assert_called_with("❌ No hay períodos anteriores disponibles para generar un reporte.", mock_message.chat.id, mock_message.message_id)


def test_iniciar_flujo_reporte_horas_con_nombres(mock_bot, mock_gamma_app, mock_message):
    mock_gamma_app.agente_excel.obtener_nombres_hojas.return_value = ["Hoja1", "Hoja2_muylargaaaaaaaaaaaaaaaaaaaaaaa"]
    
    iniciar_flujo_reporte_horas(mock_message, mock_bot, mock_gamma_app, is_callback=False)
    mock_bot.reply_to.assert_called_once()
    args, kwargs = mock_bot.reply_to.call_args
    assert "¿De qué período querés el reporte" in args[1]
    assert isinstance(kwargs["reply_markup"], InlineKeyboardMarkup)

    mock_bot.reset_mock()
    iniciar_flujo_reporte_horas(mock_message, mock_bot, mock_gamma_app, is_callback=True)
    mock_bot.edit_message_text.assert_called_once()


@patch("services.asistencia_service.PDFService")
def test_generar_y_enviar_reporte_financiero_error(mock_pdf_service, mock_bot, mock_gamma_app, mock_message):
    mock_gamma_app.agente_financiero.preparar_datos_reporte.return_value = (None, "Error al preparar")
    
    # Not callback
    generar_y_enviar_reporte_financiero(mock_bot, mock_gamma_app, mock_message, is_callback=False)
    mock_bot.send_message.assert_any_call(mock_message.chat.id, "Error al preparar")
    
    mock_bot.reset_mock()
    # Callback
    generar_y_enviar_reporte_financiero(mock_bot, mock_gamma_app, mock_message, is_callback=True)
    mock_bot.edit_message_text.assert_called_with("📄 Procesando datos financieros y armando PDF...", mock_message.chat.id, mock_message.message_id)
    mock_bot.send_message.assert_called_with(mock_message.chat.id, "Error al preparar")


@patch("services.asistencia_service.PDFService")
def test_generar_y_enviar_reporte_financiero_exito_sin_pdf(mock_pdf_service, mock_bot, mock_gamma_app, mock_message):
    mock_gamma_app.agente_financiero.preparar_datos_reporte.return_value = ({"datos": 1}, None)
    mock_pdf_service.generar_reporte_generico.return_value = (None, "Mensaje de pdf error")
    
    generar_y_enviar_reporte_financiero(mock_bot, mock_gamma_app, mock_message, is_callback=False)
    mock_bot.send_message.assert_called_with(mock_message.chat.id, "Mensaje de pdf error")


@patch("services.asistencia_service.PDFService")
@patch("builtins.open", new_callable=mock_open, read_data=b"data")
def test_generar_y_enviar_reporte_financiero_exito_con_pdf(mock_file, mock_pdf_service, mock_bot, mock_gamma_app, mock_message):
    mock_gamma_app.agente_financiero.preparar_datos_reporte.return_value = ({"datos": 1}, None)
    mock_pdf_service.generar_reporte_generico.return_value = ("/ruta/archivo.pdf", "Reporte generado")
    
    generar_y_enviar_reporte_financiero(mock_bot, mock_gamma_app, mock_message, is_callback=False)
    mock_bot.send_document.assert_called_once()
    assert mock_bot.send_document.call_args[1]["caption"] == "📊 Reporte generado"


@patch("services.asistencia_service.verificar_usuario_manual")
@patch("services.asistencia_service.generar_y_enviar_reporte")
def test_capturar_monto_descuento_valido(mock_generar, mock_verificar, mock_bot, mock_gamma_app, mock_message):
    mock_verificar.return_value = True
    mock_message.text = "1.500,50"
    capturar_monto_descuento(mock_message, mock_bot, mock_gamma_app)
    mock_generar.assert_called_once_with(mock_bot, mock_gamma_app, mock_message, descuento=150050.0)


@patch("services.asistencia_service.verificar_usuario_manual")
def test_capturar_monto_descuento_invalido(mock_verificar, mock_bot, mock_gamma_app, mock_message):
    mock_verificar.return_value = True
    
    # Texto vacio
    mock_message.text = None
    capturar_monto_descuento(mock_message, mock_bot, mock_gamma_app)
    mock_bot.reply_to.assert_called_with(mock_message, "❌ Por favor, enviá un texto con el número. (No se admiten stickers ni imágenes)")
    
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
def test_generar_y_enviar_reporte(mock_file, mock_pdf_service, mock_bot, mock_gamma_app, mock_message):
    mock_gamma_app.agente_excel.preparar_datos_reporte.return_value = ({"d": 1}, None)
    mock_pdf_service.generar_reporte_generico.return_value = ("/ruta/test.pdf", "PDF listo")
    
    generar_y_enviar_reporte(mock_bot, mock_gamma_app, mock_message, 100.0)
    mock_gamma_app.agente_excel.preparar_datos_reporte.assert_called_with(descuento=100.0)
    mock_bot.send_document.assert_called_once()
    
    # Con error
    mock_gamma_app.agente_excel.preparar_datos_reporte.return_value = (None, "Error excel")
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
def test_capturar_descuento_reporte_valido(mock_generar_hoja, mock_estado, mock_verificar, mock_bot, mock_gamma_app, mock_message):
    mock_verificar.return_value = True
    mock_estado.pop.return_value = "Hoja1"
    mock_message.text = "200"
    
    capturar_descuento_reporte(mock_message, mock_bot, mock_gamma_app)
    mock_generar_hoja.assert_called_once_with(mock_bot, mock_gamma_app, mock_message, "Hoja1", descuento=200.0)


@patch("services.asistencia_service.verificar_usuario_manual")
@patch("services.asistencia_service.EstadoGestor")
def test_capturar_descuento_reporte_errores(mock_estado, mock_verificar, mock_bot, mock_gamma_app, mock_message):
    mock_verificar.return_value = True
    
    # Texto vacio
    mock_message.text = None
    capturar_descuento_reporte(mock_message, mock_bot, mock_gamma_app)
    mock_bot.reply_to.assert_called_with(mock_message, "❌ Por favor, enviá un texto numérico. (No se admiten archivos)")
    
    # Estado vacio
    mock_message.text = "100"
    mock_estado.pop.return_value = None
    capturar_descuento_reporte(mock_message, mock_bot, mock_gamma_app)
    mock_bot.reply_to.assert_called_with(mock_message, "❌ Sesión expirada. Ejecutá /reporte de nuevo.")
    
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
def test_generar_y_enviar_reporte_por_hoja(mock_file, mock_pdf_service, mock_bot, mock_gamma_app, mock_message):
    # Exito
    mock_gamma_app.agente_excel.preparar_datos_reporte.return_value = ({"h": 1}, None)
    mock_pdf_service.generar_reporte_generico.return_value = ("/ruta/hoja.pdf", "PDF listo hoja")
    
    generar_y_enviar_reporte_por_hoja(mock_bot, mock_gamma_app, mock_message, "Hoja1", 50.0)
    mock_gamma_app.agente_excel.preparar_datos_reporte.assert_called_with(nombre_hoja="Hoja1", descuento=50.0)
    mock_bot.send_document.assert_called_once()
    
    # Error excel
    mock_bot.reset_mock()
    mock_gamma_app.agente_excel.preparar_datos_reporte.return_value = (None, "Error hoja excel")
    generar_y_enviar_reporte_por_hoja(mock_bot, mock_gamma_app, mock_message, "Hoja1", 50.0)
    mock_bot.send_message.assert_called_with(mock_message.chat.id, "Error hoja excel")

    # Sin archivo pdf
    mock_bot.reset_mock()
    mock_gamma_app.agente_excel.preparar_datos_reporte.return_value = ({"h": 1}, None)
    mock_pdf_service.generar_reporte_generico.return_value = (None, "Mensaje de pdf error")
    generar_y_enviar_reporte_por_hoja(mock_bot, mock_gamma_app, mock_message, "Hoja1", 50.0)
    mock_bot.send_message.assert_called_with(mock_message.chat.id, "Mensaje de pdf error")
