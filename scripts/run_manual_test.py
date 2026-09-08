import os
import sys
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BASE_DIR / "src"))

from logic.logic import AgenteAutonomoHoras
from com.core.utils import reply_with_expiration

class FakeBot:
    def __init__(self):
        self.sent_messages = []
        
    def send_message(self, chat_id, text, **kwargs):
        print(f"BOT [to {chat_id}]: {text}")
        class MockMsg:
            def __init__(self, c_id, m_id):
                class MockChat:
                    def __init__(self, id):
                        self.id = id
                self.chat = MockChat(c_id)
                self.message_id = m_id
        msg = MockMsg(chat_id, 123)
        self.sent_messages.append(msg)
        return msg

    def delete_message(self, chat_id, message_id):
        print(f"BOT: Deleting message {message_id} from {chat_id}")

def test_telegram_fallback():
    print("=== Testing Telegram Fallback ===")
    bot = FakeBot()
    # Para simular error en send_message, monkeypatch
    def fail_send(*args, **kwargs):
        raise Exception("Simulated ProxyError")
    bot.send_message = fail_send
    
    msg = reply_with_expiration(bot, 1393634075, "Hola de prueba")
    if getattr(msg, "message_id", None) == -1:
        print("Fallback funcionando correctamente. Se devolvió mock con message_id = -1")
    else:
        print("Fallback falló")

def test_sheets_auto_creation():
    print("\n=== Testing Google Sheets Auto-Creation ===")
    # Este test intentará autenticar con la credencial local y crear una hoja de prueba
    spreadsheet_id = os.getenv("SPREADSHEET_ID")
    if not spreadsheet_id:
        print("Error: SPREADSHEET_ID no está definido en .env o entorno")
        return
        
    agente = AgenteAutonomoHoras(spreadsheet_id, mes="TEST_SHEET_TEMP")
    try:
        ws = agente.ws
        print(f"Hoja '{ws.title}' obtenida o creada exitosamente.")
        # Limpiar: borrar la hoja de prueba
        agente.wb.del_worksheet(ws)
        print("Hoja de prueba eliminada.")
    except Exception as e:
        print(f"Error al probar auto-creación: {e}")

if __name__ == "__main__":
    from dotenv import load_dotenv
    load_dotenv(BASE_DIR / ".env")
    test_telegram_fallback()
    test_sheets_auto_creation()
