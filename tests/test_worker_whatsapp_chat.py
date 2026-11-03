from __future__ import annotations

from unittest.mock import MagicMock, patch

from adapters.notifications.mock_adapter import MockNotificationAdapter
from app_queue.worker import despachar_trabajo


class TestWorkerWhatsAppChat:
    """Verifica el procesamiento conversacional de mensajes de WhatsApp en el worker."""

    @patch("repositories.sheets_repository.SheetsRepository")
    def test_process_whatsapp_valid_gasto(self, mock_sheets_cls):
        """Verifica que un gasto en lenguaje natural se registre y envíe confirmación con emojis."""
        mock_repo = MagicMock()
        mock_ws = MagicMock()
        mock_repo._get_sheet.return_value = mock_ws
        mock_sheets_cls.return_value = mock_repo

        mock_notifier = MockNotificationAdapter()
        payload = {
            "remote_jid": "595981123456@s.whatsapp.net",
            "text": "Gasto 45.000 almuerzo en Don Vito",
            "push_name": "Carlos",
            "instance": "gamma",
        }

        despachar_trabajo(
            mock_notifier,
            "procesar_mensaje_whatsapp",
            payload,
            "595981123456@s.whatsapp.net",
        )

        # 1. Verificación de mensaje enviado
        assert len(mock_notifier.sent_messages) == 1
        sent = mock_notifier.sent_messages[0]
        assert sent.recipient_id == "595981123456@s.whatsapp.net"
        msg = sent.message
        assert "✅ *Gasto Registrado*" in msg
        assert "45.000 Gs" in msg
        assert "Don Vito" in msg
        assert "Comida" in msg

        # 2. Verificación de persistencia contable
        mock_ws.append_row.assert_called_once()
        row = mock_ws.append_row.call_args[0][0]
        assert row[1] == "Gasto"
        assert row[2] == "Don Vito"
        assert row[6] == "45000"
        assert row[7] == "Comida"

    @patch("repositories.sheets_repository.SheetsRepository")
    def test_process_whatsapp_valid_ingreso(self, mock_sheets_cls):
        """Verifica que un ingreso se registre y envíe confirmación apropiada."""
        mock_repo = MagicMock()
        mock_ws = MagicMock()
        mock_repo._get_sheet.return_value = mock_ws
        mock_sheets_cls.return_value = mock_repo

        mock_notifier = MockNotificationAdapter()
        payload = {
            "remote_jid": "595981123456@s.whatsapp.net",
            "text": "Ingreso 2.000.000 sueldo",
            "push_name": "Ana",
        }

        despachar_trabajo(
            mock_notifier,
            "procesar_mensaje_whatsapp",
            payload,
            "595981123456@s.whatsapp.net",
        )

        assert len(mock_notifier.sent_messages) == 1
        msg = mock_notifier.sent_messages[0].message
        assert "✅ *Ingreso Registrado*" in msg
        assert "2.000.000 Gs" in msg
        assert "Sueldo" in msg

    def test_process_whatsapp_greeting(self):
        """Verifica que un saludo responda con guía de uso e instrucciones."""
        mock_notifier = MockNotificationAdapter()
        payload = {
            "remote_jid": "595981123456@s.whatsapp.net",
            "text": "Hola",
            "push_name": "Marcos",
        }

        despachar_trabajo(
            mock_notifier,
            "procesar_mensaje_whatsapp",
            payload,
            "595981123456@s.whatsapp.net",
        )

        assert len(mock_notifier.sent_messages) == 1
        msg = mock_notifier.sent_messages[0].message
        assert "Soy Gamma Bot" in msg
        assert "Gastos:" in msg
        assert "Ingresos:" in msg

    def test_process_whatsapp_ambiguous_text(self):
        """Verifica que un texto con números ambiguos solicite aclaración."""
        mock_notifier = MockNotificationAdapter()
        payload = {
            "remote_jid": "595981123456@s.whatsapp.net",
            "text": "el día 15 nos vemos",
            "push_name": "Marcos",
        }

        despachar_trabajo(
            mock_notifier,
            "procesar_mensaje_whatsapp",
            payload,
            "595981123456@s.whatsapp.net",
        )

        assert len(mock_notifier.sent_messages) == 1
        msg = mock_notifier.sent_messages[0].message
        assert "No pude interpretar el movimiento con certeza" in msg

    def test_process_whatsapp_general_chat(self):
        """Verifica que un mensaje de conversación general dé ayuda orientadora."""
        mock_notifier = MockNotificationAdapter()
        payload = {
            "remote_jid": "595981123456@s.whatsapp.net",
            "text": "¿Cómo estás?",
            "push_name": "Carlos",
        }

        despachar_trabajo(
            mock_notifier,
            "procesar_mensaje_whatsapp",
            payload,
            "595981123456@s.whatsapp.net",
        )

        assert len(mock_notifier.sent_messages) == 1
        msg = mock_notifier.sent_messages[0].message
        assert "recibí tu mensaje" in msg
        assert "Para registrar un gasto o ingreso" in msg
