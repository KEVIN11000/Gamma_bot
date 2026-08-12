import os
import requests
from datetime import datetime, timedelta
import pytz
from logger_config import setup_logger

logger = setup_logger("cron_jobs")

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
tz_py = pytz.timezone('America/Asuncion')

# ─────────────────────────────────────────────────────────────────────────────
# PUNTO 2 — Resumen Semanal de Productividad
# ─────────────────────────────────────────────────────────────────────────────

def resumen_semanal(bot, chat_id, spreadsheet_id):
    """
    Lee la última hoja del Spreadsheet y calcula las horas y monto
    acumulados en la semana actual (lunes a viernes).
    Llamado por cron-job.org todos los viernes a las 18:00 hs (Asunción).
    """
    try:
        from logic.logic import ConexionSheets
        import gspread

        MONTO_POR_HORA = 14634  # Gs. por hora

        cliente = ConexionSheets.obtener_cliente()
        wb = cliente.open_by_key(spreadsheet_id)

        # Obtener la ÚLTIMA hoja del Spreadsheet (la más reciente)
        hojas = wb.worksheets()
        if not hojas:
            bot.send_message(chat_id, "⚠️ No se encontraron hojas en el Spreadsheet.")
            return False
        ws = hojas[-1]
        logger.info(f"Leyendo hoja activa para resumen semanal: '{ws.title}'")

        # Calcular rango de la semana actual (lunes → hoy viernes)
        hoy = datetime.now(tz_py)
        lunes = hoy - timedelta(days=hoy.weekday())  # weekday() 0=Lunes
        fechas_semana = set()
        for i in range(5):  # Lunes a Viernes
            dia = lunes + timedelta(days=i)
            fechas_semana.add(dia.strftime("%d/%m/%Y"))

        # Leer todas las filas de la hoja (columna B = fecha, columna G = horas)
        todos_datos = ws.get_all_values()
        total_horas = 0.0
        dias_trabajados = 0

        for fila in todos_datos[1:]:  # Saltar encabezado
            if len(fila) < 7:
                continue
            fecha_celda = fila[1].strip()  # Columna B
            horas_celda = fila[6].strip()  # Columna G

            if fecha_celda in fechas_semana and horas_celda:
                try:
                    horas_celda_float = float(horas_celda.replace(",", "."))
                    total_horas += horas_celda_float
                    dias_trabajados += 1
                except ValueError:
                    pass

        total_monto = int(total_horas * MONTO_POR_HORA)
        num_semana = hoy.isocalendar()[1]

        mensaje = (
            f"📊 *Resumen Semanal — Semana {num_semana}*\n"
            f"━━━━━━━━━━━━━━━━━━━━━\n"
            f"📅 Período: {lunes.strftime('%d/%m')} → {hoy.strftime('%d/%m/%Y')}\n"
            f"📋 Hoja activa: *{ws.title}*\n\n"
            f"⏱️ Horas trabajadas: *{total_horas:.1f} hs*\n"
            f"📆 Días registrados: *{dias_trabajados}*\n"
            f"💰 Monto estimado: *Gs. {total_monto:,}*\n"
            f"━━━━━━━━━━━━━━━━━━━━━\n"
            f"_¡Buen fin de semana!_ 🎉"
        )

        bot.send_message(chat_id, mensaje, parse_mode="Markdown")
        logger.info(f"Resumen semanal enviado. Horas: {total_horas:.1f} | Monto: Gs. {total_monto:,}")
        return True

    except Exception as e:
        logger.error(f"resumen_semanal: {e}")
        bot.send_message(chat_id, f"❌ Error al generar el resumen semanal: {e}")
        return False


# ─────────────────────────────────────────────────────────────────────────────
# PUNTO 3 — Asistente Climático (Open-Meteo, sin API key)
# ─────────────────────────────────────────────────────────────────────────────

# Coordenadas de Asunción, Paraguay
ASUNCION_LAT = -25.2867
ASUNCION_LON = -57.647

# Códigos WMO → descripción + emoji
CODIGOS_CLIMA = {
    0: ("☀️", "Despejado"),
    1: ("🌤️", "Mayormente despejado"),
    2: ("⛅", "Parcialmente nublado"),
    3: ("☁️", "Nublado"),
    45: ("🌫️", "Neblina"),
    48: ("🌫️", "Neblina con escarcha"),
    51: ("🌦️", "Llovizna leve"),
    53: ("🌦️", "Llovizna moderada"),
    55: ("🌧️", "Llovizna intensa"),
    61: ("🌧️", "Lluvia leve"),
    63: ("🌧️", "Lluvia moderada"),
    65: ("🌧️", "Lluvia intensa"),
    80: ("🌦️", "Lluvia con chaparrones"),
    81: ("🌧️", "Chaparrones moderados"),
    82: ("⛈️", "Chaparrones fuertes"),
    95: ("⛈️", "Tormenta eléctrica"),
    96: ("⛈️", "Tormenta con granizo"),
    99: ("⛈️", "Tormenta fuerte con granizo"),
}


def notificacion_clima(bot, chat_id):
    """
    Consulta Open-Meteo (gratuito, sin API key) y envía el pronóstico
    del día para Asunción a las 07:00 AM.
    """
    try:

        url = (
            f"https://api.open-meteo.com/v1/forecast"
            f"?latitude={ASUNCION_LAT}&longitude={ASUNCION_LON}"
            f"&daily=weathercode,temperature_2m_max,temperature_2m_min,"
            f"precipitation_probability_max,windspeed_10m_max"
            f"&timezone=America%2FAsuncion&forecast_days=1"
        )

        resp = requests.get(url, timeout=10)
        resp.raise_for_status()
        data = resp.json()

        daily = data.get("daily", {})
        wmo_code   = daily.get("weathercode", [0])[0]
        temp_max   = daily.get("temperature_2m_max", [0])[0]
        temp_min   = daily.get("temperature_2m_min", [0])[0]
        precip_pct = daily.get("precipitation_probability_max", [0])[0]
        viento     = daily.get("windspeed_10m_max", [0])[0]

        emoji, descripcion = CODIGOS_CLIMA.get(wmo_code, ("🌡️", "Condición desconocida"))

        # Alerta contextual de lluvia
        alerta_lluvia = ""
        if precip_pct >= 60:
            alerta_lluvia = "\n☂️ _Alta probabilidad de lluvia. ¡No olvides el paraguas!_"
        elif precip_pct >= 35:
            alerta_lluvia = "\n🌂 _Posibles lluvias por la tarde. Lleva el paraguas por las dudas._"

        hoy = datetime.now(tz_py).strftime("%A %d de %B").capitalize()

        mensaje = (
            f"{emoji} *Buenos días — Pronóstico de hoy*\n"
            f"━━━━━━━━━━━━━━━━━━━━━\n"
            f"📍 Asunción, Paraguay — {hoy}\n\n"
            f"🌡️ Temperatura: *{temp_min:.0f}°C — {temp_max:.0f}°C*\n"
            f"🌤️ Condición: *{descripcion}*\n"
            f"🌧️ Prob. lluvia: *{precip_pct}%*\n"
            f"💨 Viento máx.: *{viento:.0f} km/h*"
            f"{alerta_lluvia}\n"
            f"━━━━━━━━━━━━━━━━━━━━━\n"
            f"_¡Que tengas un excelente día!_ 💪"
        )

        bot.send_message(chat_id, mensaje, parse_mode="Markdown")
        logger.info(f"Notificación climática enviada. {descripcion}, {temp_max}°C, {precip_pct}% lluvia.")
        return True

    except Exception as e:
        logger.error(f"notificacion_clima: {e}")
        return False


# ─────────────────────────────────────────────────────────────────────────────
# PUNTO 4 — Rotación Anual de Logs
# ─────────────────────────────────────────────────────────────────────────────

def rotar_logs():
    """
    Renombra gen_log.txt → gen_log_YYYY.txt y crea uno nuevo vacío.
    Llamado por cron-job.org el 1° de enero a las 00:01 AM.
    """
    try:

        path_actual = os.path.join(BASE_DIR, "gen_log.txt")
        anio_anterior = datetime.now(tz_py).year - 1
        path_backup = os.path.join(BASE_DIR, f"gen_log_{anio_anterior}.txt")

        if os.path.exists(path_actual):
            os.rename(path_actual, path_backup)

        # Crear un log nuevo y limpio
        with open(path_actual, "w", encoding="utf-8") as f:
            f.write(f"[LOG INICIADO] {datetime.now(tz_py).strftime('%Y-%m-%d %H:%M:%S')} — Rotación anual completada.\n")

        logger.info(f"Log rotado: gen_log_{anio_anterior}.txt guardado. Nuevo gen_log.txt creado.")
        return True

    except Exception as e:
        logger.error(f"rotar_logs: {e}")
        return False
