from logic.logic import AgenteAutonomoHoras

agente = AgenteAutonomoHoras(spreadsheet_id="1hIDfS4Kfc-T9F-51LBBF5N0YqLaN2hibjxXyctiI-aA")
resultado = agente.interpretar_frase_con_ia("tengo que entregar el laboratorio de mecatrónica mañana a las 4 y media de la tarde")

print(resultado)