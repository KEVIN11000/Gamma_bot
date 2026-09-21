import threading
from dotenv import load_dotenv
from com.bot import GAMMA
from logger_config import setup_logger
from app_queue.worker import procesar_trabajos_pendientes

logger = setup_logger("run_bot")


def _worker_loop(bot: object, stop_event: threading.Event) -> None:
    logger.info("Worker local de cola iniciado (polling cada 3s).")
    while not stop_event.is_set():
        try:
            procesar_trabajos_pendientes(bot)
        except Exception as e:
            logger.error(f"Error en worker local de cola: {e}")
        stop_event.wait(3.0)


def main() -> None:
    # Cargar variables del .env de pruebas
    load_dotenv()

    logger.info("Iniciando Gamma Bot en modo Polling Local (Pruebas)...")

    stop_worker = threading.Event()
    worker_thread = None

    try:
        # Instanciar el bot
        gamma = GAMMA()

        # Iniciar worker local de cola para procesar jobs SQLite en pruebas locales
        worker_thread = threading.Thread(
            target=_worker_loop, args=(gamma.bot, stop_worker), daemon=True
        )
        worker_thread.start()

        # Es crucial eliminar el webhook para que Telegram permita el polling local
        logger.info("Limpiando webhooks activos...")
        gamma.bot.remove_webhook()

        logger.info("✅ Bot listo y escuchando comandos. Presiona Ctrl+C para detener.")
        # none_stop=True asegura que el bot no se detenga por errores de red
        gamma.bot.infinity_polling(timeout=10, long_polling_timeout=5)

    except KeyboardInterrupt:
        logger.info("Apagando el bot de pruebas...")
    except Exception as e:
        logger.error(f"Error fatal en el polling: {e}")
    finally:
        stop_worker.set()
        if worker_thread and worker_thread.is_alive():
            worker_thread.join(timeout=2.0)


if __name__ == "__main__":
    main()
