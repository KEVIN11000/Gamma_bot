import unittest
from unittest.mock import patch, MagicMock

from logic.cron_jobs import sincronizar_avisos_vencimientos


class TestCronJobs(unittest.TestCase):

    @patch("repositories.sheets_repository.SheetsRepository")
    @patch("logic.logic.AgenteAutonomoHoras")
    @patch("logic.logic.get_now_py")
    def test_sincronizar_avisos_vencimientos(self, mock_get_now, MockAgente, MockRepo):
        import datetime
        from dateutil.tz import tzutc

        mock_get_now.return_value = datetime.datetime(2026, 9, 15, tzinfo=tzutc())

        repo_instance = MockRepo.return_value
        repo_instance.get_todas_obligaciones.return_value = [
            {
                "Estado": "Activo",
                "Dia_Vencimiento": 20,
                "Nombre": "Prestamo",
                "Cuota_Referencia_Gs": 1000,
            }
        ]

        agente_instance = MockAgente.return_value
        agente_instance.guardar_aviso_calendar.return_value = "Evento creado"

        res = sincronizar_avisos_vencimientos()

        self.assertEqual(res["synced"], 1)
        self.assertEqual(res["errors"], 0)

        agente_instance.guardar_aviso_calendar.assert_called_once()
        args, kwargs = agente_instance.guardar_aviso_calendar.call_args
        datos_evento = args[0]

        self.assertEqual(datos_evento["hora"], "08:00")
        self.assertEqual(len(datos_evento["reminders"]), 4)
        reminders = [r["minutes"] for r in datos_evento["reminders"]]
        self.assertIn(7 * 24 * 60, reminders)
        self.assertIn(5 * 24 * 60, reminders)
        self.assertIn(3 * 24 * 60, reminders)
        self.assertIn(1 * 24 * 60, reminders)


if __name__ == "__main__":
    unittest.main()
