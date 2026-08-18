# Code Review Report (v1.0.0)

## TODO entries found
- code_review.py:4: • A recursive search for "TODO"/comments that may indicate unfinished work.
- code_review.py:15: if 'TODO' in line:
- code_review.py:33: out.write('## TODO entries found\n')

## flake8 report
```
E:\PG\vcp-s\Gamma_bot\code_review.py:8:1: F401 'sys' imported but unused
E:\PG\vcp-s\Gamma_bot\code_review.py:8:15: E401 multiple imports on one line
E:\PG\vcp-s\Gamma_bot\code_review.py:10:1: E302 expected 2 blank lines, found 1
E:\PG\vcp-s\Gamma_bot\code_review.py:16:80: E501 line too long (86 > 79 characters)
E:\PG\vcp-s\Gamma_bot\code_review.py:19:1: E302 expected 2 blank lines, found 1
E:\PG\vcp-s\Gamma_bot\code_review.py:21:80: E501 line too long (99 > 79 characters)
E:\PG\vcp-s\Gamma_bot\code_review.py:26:1: E302 expected 2 blank lines, found 1
E:\PG\vcp-s\Gamma_bot\code_review.py:42:1: E305 expected 2 blank lines after class or function definition, found 1
E:\PG\vcp-s\Gamma_bot\com\bot.py:2:1: F401 'typing.Any' imported but unused
E:\PG\vcp-s\Gamma_bot\com\bot.py:10:1: E402 module level import not at top of file
E:\PG\vcp-s\Gamma_bot\com\bot.py:11:1: F401 'logic.logic.EstadoGestor' imported but unused
E:\PG\vcp-s\Gamma_bot\com\bot.py:11:1: E402 module level import not at top of file
E:\PG\vcp-s\Gamma_bot\com\bot.py:11:80: E501 line too long (83 > 79 characters)
E:\PG\vcp-s\Gamma_bot\com\bot.py:12:1: E402 module level import not at top of file
E:\PG\vcp-s\Gamma_bot\com\bot.py:13:1: F401 'telebot.types.BotCommand' imported but unused
E:\PG\vcp-s\Gamma_bot\com\bot.py:13:1: E402 module level import not at top of file
E:\PG\vcp-s\Gamma_bot\com\bot.py:14:1: F401 'datetime.datetime' imported but unused
E:\PG\vcp-s\Gamma_bot\com\bot.py:14:1: E402 module level import not at top of file
E:\PG\vcp-s\Gamma_bot\com\bot.py:20:1: E302 expected 2 blank lines, found 1
E:\PG\vcp-s\Gamma_bot\com\bot.py:26:80: E501 line too long (101 > 79 characters)
E:\PG\vcp-s\Gamma_bot\com\bot.py:32:9: E303 too many blank lines (3)
E:\PG\vcp-s\Gamma_bot\com\bot.py:35:1: W293 blank line contains whitespace
E:\PG\vcp-s\Gamma_bot\com\bot.py:41:1: W293 blank line contains whitespace
E:\PG\vcp-s\Gamma_bot\com\core\errors.py:8:1: E302 expected 2 blank lines, found 1
E:\PG\vcp-s\Gamma_bot\com\core\errors.py:10:80: E501 line too long (92 > 79 characters)
E:\PG\vcp-s\Gamma_bot\com\core\errors.py:11:80: E501 line too long (87 > 79 characters)
E:\PG\vcp-s\Gamma_bot\com\core\errors.py:20:80: E501 line too long (89 > 79 characters)
E:\PG\vcp-s\Gamma_bot\com\core\errors.py:21:1: W293 blank line contains whitespace
E:\PG\vcp-s\Gamma_bot\com\core\errors.py:25:80: E501 line too long (121 > 79 characters)
E:\PG\vcp-s\Gamma_bot\com\core\errors.py:29:80: E501 line too long (101 > 79 characters)
E:\PG\vcp-s\Gamma_bot\com\core\errors.py:31:80: E501 line too long (90 > 79 characters)
E:\PG\vcp-s\Gamma_bot\com\core\security.py:11:1: E302 expected 2 blank lines, found 1
E:\PG\vcp-s\Gamma_bot\com\core\security.py:21:1: E302 expected 2 blank lines, found 1
E:\PG\vcp-s\Gamma_bot\com\core\security.py:31:80: E501 line too long (94 > 79 characters)
E:\PG\vcp-s\Gamma_bot\com\core\security.py:46:1: E302 expected 2 blank lines, found 1
E:\PG\vcp-s\Gamma_bot\com\core\security.py:48:68: W291 trailing whitespace
E:\PG\vcp-s\Gamma_bot\com\handlers\asistencia.py:3:1: F401 'os' imported but unused
E:\PG\vcp-s\Gamma_bot\com\handlers\asistencia.py:12:1: F401 'logic.pdf_service.PDFService' imported but unused
E:\PG\vcp-s\Gamma_bot\com\handlers\asistencia.py:16:1: E302 expected 2 blank lines, found 1
E:\PG\vcp-s\Gamma_bot\com\handlers\asistencia.py:17:1: W293 blank line contains whitespace
E:\PG\vcp-s\Gamma_bot\com\handlers\asistencia.py:24:80: E501 line too long (85 > 79 characters)
E:\PG\vcp-s\Gamma_bot\com\handlers\asistencia.py:25:80: E501 line too long (85 > 79 characters)
E:\PG\vcp-s\Gamma_bot\com\handlers\asistencia.py:27:80: E501 line too long (106 > 79 characters)
E:\PG\vcp-s\Gamma_bot\com\handlers\asistencia.py:29:80: E501 line too long (82 > 79 characters)
E:\PG\vcp-s\Gamma_bot\com\handlers\asistencia.py:34:52: E261 at least two spaces before inline comment
E:\PG\vcp-s\Gamma_bot\com\handlers\asistencia.py:35:80: E501 line too long (92 > 79 characters)
E:\PG\vcp-s\Gamma_bot\com\handlers\asistencia.py:36:80: E501 line too long (107 > 79 characters)
E:\PG\vcp-s\Gamma_bot\com\handlers\asistencia.py:41:80: E501 line too long (126 > 79 characters)
E:\PG\vcp-s\Gamma_bot\com\handlers\asistencia.py:44:80: E501 line too long (110 > 79 characters)
E:\PG\vcp-s\Gamma_bot\com\handlers\asistencia.py:50:80: E501 line too long (88 > 79 characters)
E:\PG\vcp-s\Gamma_bot\com\handlers\asistencia.py:52:80: E501 line too long (96 > 79 characters)
E:\PG\vcp-s\Gamma_bot\com\handlers\asistencia.py:60:80: E501 line too long (82 > 79 characters)
E:\PG\vcp-s\Gamma_bot\com\handlers\asistencia.py:61:80: E501 line too long (81 > 79 characters)
E:\PG\vcp-s\Gamma_bot\com\handlers\asistencia.py:63:80: E501 line too long (165 > 79 characters)
E:\PG\vcp-s\Gamma_bot\com\handlers\asistencia.py:65:80: E501 line too long (82 > 79 characters)
E:\PG\vcp-s\Gamma_bot\com\handlers\asistencia.py:71:80: E501 line too long (92 > 79 characters)
E:\PG\vcp-s\Gamma_bot\com\handlers\asistencia.py:72:80: E501 line too long (107 > 79 characters)
E:\PG\vcp-s\Gamma_bot\com\handlers\asistencia.py:84:80: E501 line too long (105 > 79 characters)
E:\PG\vcp-s\Gamma_bot\com\handlers\asistencia.py:90:80: E501 line too long (101 > 79 characters)
E:\PG\vcp-s\Gamma_bot\com\handlers\asistencia.py:91:80: E501 line too long (107 > 79 characters)
E:\PG\vcp-s\Gamma_bot\com\handlers\asistencia.py:95:80: E501 line too long (88 > 79 characters)
E:\PG\vcp-s\Gamma_bot\com\handlers\asistencia.py:102:80: E501 line too long (91 > 79 characters)
E:\PG\vcp-s\Gamma_bot\com\handlers\asistencia.py:103:80: E501 line too long (80 > 79 characters)
E:\PG\vcp-s\Gamma_bot\com\handlers\asistencia.py:114:80: E501 line too long (103 > 79 characters)
E:\PG\vcp-s\Gamma_bot\com\handlers\asistencia.py:129:80: E501 line too long (85 > 79 characters)
E:\PG\vcp-s\Gamma_bot\com\handlers\asistencia.py:130:80: E501 line too long (93 > 79 characters)
E:\PG\vcp-s\Gamma_bot\com\handlers\asistencia.py:139:80: E501 line too long (83 > 79 characters)
E:\PG\vcp-s\Gamma_bot\com\handlers\asistencia.py:144:16: E221 multiple spaces before operator
E:\PG\vcp-s\Gamma_bot\com\handlers\asistencia.py:145:15: E221 multiple spaces before operator
E:\PG\vcp-s\Gamma_bot\com\handlers\asistencia.py:146:13: E221 multiple spaces before operator
E:\PG\vcp-s\Gamma_bot\com\handlers\asistencia.py:151:1: W293 blank line contains whitespace
E:\PG\vcp-s\Gamma_bot\com\handlers\asistencia.py:153:80: E501 line too long (88 > 79 characters)
E:\PG\vcp-s\Gamma_bot\com\handlers\asistencia.py:157:80: E501 line too long (96 > 79 characters)
E:\PG\vcp-s\Gamma_bot\com\handlers\asistencia.py:166:80: E501 line too long (100 > 79 characters)
E:\PG\vcp-s\Gamma_bot\com\handlers\asistencia.py:167:80: E501 line too long (101 > 79 characters)
E:\PG\vcp-s\Gamma_bot\com\handlers\asistencia.py:181:80: E501 line too long (103 > 79 characters)
E:\PG\vcp-s\Gamma_bot\com\handlers\asistencia.py:183:80: E501 line too long (91 > 79 characters)
E:\PG\vcp-s\Gamma_bot\com\handlers\asistencia.py:184:80: E501 line too long (102 > 79 characters)
E:\PG\vcp-s\Gamma_bot\com\handlers\asistencia.py:194:80: E501 line too long (105 > 79 characters)
E:\PG\vcp-s\Gamma_bot\com\handlers\asistencia.py:199:80: E501 line too long (99 > 79 characters)
E:\PG\vcp-s\Gamma_bot\com\handlers\asistencia.py:203:80: E501 line too long (81 > 79 characters)
E:\PG\vcp-s\Gamma_bot\com\handlers\asistencia.py:213:80: E501 line too long (94 > 79 characters)
E:\PG\vcp-s\Gamma_bot\com\handlers\asistencia.py:214:80: E501 line too long (85 > 79 characters)
E:\PG\vcp-s\Gamma_bot\com\handlers\asistencia.py:216:80: E501 line too long (107 > 79 characters)
E:\PG\vcp-s\Gamma_bot\com\handlers\asistencia.py:218:80: E501 line too long (118 > 79 characters)
E:\PG\vcp-s\Gamma_bot\com\handlers\asistencia.py:220:80: E501 line too long (81 > 79 characters)
E:\PG\vcp-s\Gamma_bot\com\handlers\asistencia.py:223:80: E501 line too long (111 > 79 characters)
E:\PG\vcp-s\Gamma_bot\com\handlers\asistencia.py:226:1: W293 blank line contains whitespace
E:\PG\vcp-s\Gamma_bot\com\handlers\asistencia.py:228:80: E501 line too long (97 > 79 characters)
E:\PG\vcp-s\Gamma_bot\com\handlers\asistencia.py:230:80: E501 line too long (84 > 79 characters)
E:\PG\vcp-s\Gamma_bot\com\handlers\asistencia.py:231:1: W293 blank line contains whitespace
E:\PG\vcp-s\Gamma_bot\com\handlers\asistencia.py:233:1: W293 blank line contains whitespace
E:\PG\vcp-s\Gamma_bot\com\handlers\asistencia.py:237:1: W293 blank line contains whitespace
E:\PG\vcp-s\Gamma_bot\com\handlers\asistencia.py:238:5: F811 redefinition of unused 'PDFService' from line 12
E:\PG\vcp-s\Gamma_bot\com\handlers\asistencia.py:254:50: E701 multiple statements on one line (colon)
E:\PG\vcp-s\Gamma_bot\com\handlers\asistencia.py:256:80: E501 line too long (112 > 79 characters)
E:\PG\vcp-s\Gamma_bot\com\handlers\asistencia.py:258:1: W293 blank line contains whitespace
E:\PG\vcp-s\Gamma_bot\com\handlers\asistencia.py:260:80: E501 line too long (80 > 79 characters)
E:\PG\vcp-s\Gamma_bot\com\handlers\asistencia.py:262:80: E501 line too long (85 > 79 characters)
E:\PG\vcp-s\Gamma_bot\com\handlers\asistencia.py:267:80: E501 line too long (108 > 79 characters)
E:\PG\vcp-s\Gamma_bot\com\handlers\asistencia.py:271:1: E302 expected 2 blank lines, found 1
E:\PG\vcp-s\Gamma_bot\com\handlers\asistencia.py:271:80: E501 line too long (97 > 79 characters)
E:\PG\vcp-s\Gamma_bot\com\handlers\asistencia.py:272:80: E501 line too long (89 > 79 characters)
E:\PG\vcp-s\Gamma_bot\com\handlers\asistencia.py:273:1: W293 blank line contains whitespace
E:\PG\vcp-s\Gamma_bot\com\handlers\asistencia.py:274:80: E501 line too long (85 > 79 characters)
E:\PG\vcp-s\Gamma_bot\com\handlers\asistencia.py:278:1: W293 blank line contains whitespace
E:\PG\vcp-s\Gamma_bot\com\handlers\asistencia.py:279:5: F811 redefinition of unused 'PDFService' from line 12
E:\PG\vcp-s\Gamma_bot\com\handlers\asistencia.py:293:1: E302 expected 2 blank lines, found 1
E:\PG\vcp-s\Gamma_bot\com\handlers\asistencia.py:294:50: E701 multiple statements on one line (colon)
E:\PG\vcp-s\Gamma_bot\com\handlers\asistencia.py:296:80: E501 line too long (95 > 79 characters)
E:\PG\vcp-s\Gamma_bot\com\handlers\asistencia.py:298:1: W293 blank line contains whitespace
E:\PG\vcp-s\Gamma_bot\com\handlers\asistencia.py:303:80: E501 line too long (82 > 79 characters)
E:\PG\vcp-s\Gamma_bot\com\handlers\asistencia.py:306:80: E501 line too long (97 > 79 characters)
E:\PG\vcp-s\Gamma_bot\com\handlers\asistencia.py:314:1: E302 expected 2 blank lines, found 1
E:\PG\vcp-s\Gamma_bot\com\handlers\asistencia.py:314:80: E501 line too long (126 > 79 characters)
E:\PG\vcp-s\Gamma_bot\com\handlers\asistencia.py:315:80: E501 line too long (89 > 79 characters)
E:\PG\vcp-s\Gamma_bot\com\handlers\asistencia.py:316:1: W293 blank line contains whitespace
E:\PG\vcp-s\Gamma_bot\com\handlers\asistencia.py:317:80: E501 line too long (110 > 79 characters)
E:\PG\vcp-s\Gamma_bot\com\handlers\asistencia.py:321:1: W293 blank line contains whitespace
E:\PG\vcp-s\Gamma_bot\com\handlers\asistencia.py:322:5: F811 redefinition of unused 'PDFService' from line 12
E:\PG\vcp-s\Gamma_bot\com\handlers\asistencia.py:324:1: W293 blank line contains whitespace
E:\PG\vcp-s\Gamma_bot\com\handlers\avisos.py:3:1: F401 'os' imported but unused
E:\PG\vcp-s\Gamma_bot\com\handlers\avisos.py:16:1: E302 expected 2 blank lines, found 1
E:\PG\vcp-s\Gamma_bot\com\handlers\avisos.py:29:80: E501 line too long (91 > 79 characters)
E:\PG\vcp-s\Gamma_bot\com\handlers\avisos.py:32:80: E501 line too long (110 > 79 characters)
E:\PG\vcp-s\Gamma_bot\com\handlers\avisos.py:34:80: E501 line too long (81 > 79 characters)
E:\PG\vcp-s\Gamma_bot\com\handlers\avisos.py:44:80: E501 line too long (105 > 79 characters)
E:\PG\vcp-s\Gamma_bot\com\handlers\avisos.py:50:80: E501 line too long (140 > 79 characters)
E:\PG\vcp-s\Gamma_bot\com\handlers\avisos.py:53:80: E501 line too long (124 > 79 characters)
E:\PG\vcp-s\Gamma_bot\com\handlers\avisos.py:54:80: E501 line too long (93 > 79 characters)
E:\PG\vcp-s\Gamma_bot\com\handlers\avisos.py:56:80: E501 line too long (111 > 79 characters)
E:\PG\vcp-s\Gamma_bot\com\handlers\avisos.py:59:80: E501 line too long (97 > 79 characters)
E:\PG\vcp-s\Gamma_bot\com\handlers\avisos.py:68:80: E501 line too long (81 > 79 characters)
E:\PG\vcp-s\Gamma_bot\com\handlers\avisos.py:71:80: E501 line too long (92 > 79 characters)
E:\PG\vcp-s\Gamma_bot\com\handlers\avisos.py:79:80: E501 line too long (101 > 79 characters)
E:\PG\vcp-s\Gamma_bot\com\handlers\avisos.py:81:80: E501 line too long (96 > 79 characters)
E:\PG\vcp-s\Gamma_bot\com\handlers\avisos.py:91:80: E501 line too long (103 > 79 characters)
E:\PG\vcp-s\Gamma_bot\com\handlers\avisos.py:92:80: E501 line too long (85 > 79 characters)
E:\PG\vcp-s\Gamma_bot\com\handlers\avisos.py:96:80: E501 line too long (104 > 79 characters)
E:\PG\vcp-s\Gamma_bot\com\handlers\avisos.py:99:80: E501 line too long (84 > 79 characters)
E:\PG\vcp-s\Gamma_bot\com\handlers\avisos.py:101:80: E501 line too long (82 > 79 characters)
E:\PG\vcp-s\Gamma_bot\com\handlers\avisos.py:111:80: E501 line too long (88 > 79 characters)
E:\PG\vcp-s\Gamma_bot\com\handlers\avisos.py:112:1: W293 blank line contains whitespace
E:\PG\vcp-s\Gamma_bot\com\handlers\avisos.py:115:80: E501 line too long (93 > 79 characters)
E:\PG\vcp-s\Gamma_bot\com\handlers\avisos.py:116:1: W293 blank line contains whitespace
E:\PG\vcp-s\Gamma_bot\com\handlers\avisos.py:118:80: E501 line too long (145 > 79 characters)
E:\PG\vcp-s\Gamma_bot\com\handlers\avisos.py:120:80: E501 line too long (99 > 79 characters)
E:\PG\vcp-s\Gamma_bot\com\handlers\avisos.py:122:80: E501 line too long (82 > 79 characters)
E:\PG\vcp-s\Gamma_bot\com\handlers\avisos.py:124:80: E501 line too long (81 > 79 characters)
E:\PG\vcp-s\Gamma_bot\com\handlers\avisos.py:126:80: E501 line too long (96 > 79 characters)
E:\PG\vcp-s\Gamma_bot\com\handlers\avisos.py:134:80: E501 line too long (101 > 79 characters)
E:\PG\vcp-s\Gamma_bot\com\handlers\avisos.py:135:80: E501 line too long (96 > 79 characters)
E:\PG\vcp-s\Gamma_bot\com\handlers\avisos.py:143:80: E501 line too long (103 > 79 characters)
E:\PG\vcp-s\Gamma_bot\com\handlers\avisos.py:144:80: E501 line too long (102 > 79 characters)
E:\PG\vcp-s\Gamma_bot\com\handlers\avisos.py:147:80: E501 line too long (102 > 79 characters)
E:\PG\vcp-s\Gamma_bot\com\handlers\avisos.py:150:80: E501 line too long (84 > 79 characters)
E:\PG\vcp-s\Gamma_bot\com\handlers\avisos.py:151:50: E701 multiple statements on one line (colon)
E:\PG\vcp-s\Gamma_bot\com\handlers\avisos.py:154:80: E501 line too long (85 > 79 characters)
E:\PG\vcp-s\Gamma_bot\com\handlers\avisos.py:158:1: E302 expected 2 blank lines, found 1
E:\PG\vcp-s\Gamma_bot\com\handlers\avisos.py:158:80: E501 line too long (85 > 79 characters)
E:\PG\vcp-s\Gamma_bot\com\handlers\avisos.py:159:80: E501 line too long (86 > 79 characters)
E:\PG\vcp-s\Gamma_bot\com\handlers\avisos.py:163:80: E501 line too long (95 > 79 characters)
E:\PG\vcp-s\Gamma_bot\com\handlers\avisos.py:170:80: E501 line too long (81 > 79 characters)
E:\PG\vcp-s\Gamma_bot\com\handlers\avisos.py:171:80: E501 line too long (80 > 79 characters)
E:\PG\vcp-s\Gamma_bot\com\handlers\base.py:13:1: E302 expected 2 blank lines, found 1
E:\PG\vcp-s\Gamma_bot\com\handlers\base.py:15:80: E501 line too long (86 > 79 characters)
E:\PG\vcp-s\Gamma_bot\com\handlers\base.py:26:1: W293 blank line contains whitespace
E:\PG\vcp-s\Gamma_bot\com\handlers\base.py:29:1: W293 blank line contains whitespace
E:\PG\vcp-s\Gamma_bot\com\handlers\base.py:31:1: E305 expected 2 blank lines after class or function definition, found 0
E:\PG\vcp-s\Gamma_bot\com\handlers\base.py:33:1: E302 expected 2 blank lines, found 1
E:\PG\vcp-s\Gamma_bot\com\handlers\base.py:38:80: E501 line too long (82 > 79 characters)
E:\PG\vcp-s\Gamma_bot\com\handlers\base.py:40:80: E501 line too long (111 > 79 characters)
E:\PG\vcp-s\Gamma_bot\com\handlers\base.py:42:1: W293 blank line contains whitespace
E:\PG\vcp-s\Gamma_bot\com\handlers\base.py:45:1: W293 blank line contains whitespace
E:\PG\vcp-s\Gamma_bot\com\handlers\base.py:52:1: W293 blank line contains whitespace
E:\PG\vcp-s\Gamma_bot\com\handlers\base.py:54:80: E501 line too long (168 > 79 characters)
E:\PG\vcp-s\Gamma_bot\com\handlers\base.py:57:1: W293 blank line contains whitespace
E:\PG\vcp-s\Gamma_bot\com\handlers\base.py:59:1: W293 blank line contains whitespace
E:\PG\vcp-s\Gamma_bot\com\handlers\base.py:61:80: E501 line too long (82 > 79 characters)
E:\PG\vcp-s\Gamma_bot\com\handlers\base.py:66:80: E501 line too long (133 > 79 characters)
E:\PG\vcp-s\Gamma_bot\com\handlers\base.py:68:80: E501 line too long (161 > 79 characters)
E:\PG\vcp-s\Gamma_bot\com\handlers\base.py:75:1: W293 blank line contains whitespace
E:\PG\vcp-s\Gamma_bot\com\handlers\base.py:76:80: E501 line too long (82 > 79 characters)
E:\PG\vcp-s\Gamma_bot\com\handlers\base.py:77:80: E501 line too long (88 > 79 characters)
E:\PG\vcp-s\Gamma_bot\com\handlers\base.py:78:1: W293 blank line contains whitespace
E:\PG\vcp-s\Gamma_bot\com\handlers\base.py:86:1: W293 blank line contains whitespace
E:\PG\vcp-s\Gamma_bot\com\handlers\finanzas.py:3:1: F401 'os' imported but unused
E:\PG\vcp-s\Gamma_bot\com\handlers\finanzas.py:14:1: E302 expected 2 blank lines, found 1
E:\PG\vcp-s\Gamma_bot\com\handlers\finanzas.py:22:1: W293 blank line contains whitespace
E:\PG\vcp-s\Gamma_bot\com\handlers\finanzas.py:25:80: E501 line too long (122 > 79 characters)
E:\PG\vcp-s\Gamma_bot\com\handlers\finanzas.py:27:1: W293 blank line contains whitespace
E:\PG\vcp-s\Gamma_bot\com\handlers\finanzas.py:29:80: E501 line too long (87 > 79 characters)
E:\PG\vcp-s\Gamma_bot\com\handlers\finanzas.py:30:1: W293 blank line contains whitespace
E:\PG\vcp-s\Gamma_bot\com\handlers\finanzas.py:31:80: E501 line too long (93 > 79 characters)
E:\PG\vcp-s\Gamma_bot\com\handlers\finanzas.py:33:80: E501 line too long (102 > 79 characters)
E:\PG\vcp-s\Gamma_bot\com\handlers\finanzas.py:35:1: W293 blank line contains whitespace
E:\PG\vcp-s\Gamma_bot\com\handlers\finanzas.py:47:1: W293 blank line contains whitespace
E:\PG\vcp-s\Gamma_bot\com\handlers\finanzas.py:51:1: W293 blank line contains whitespace
E:\PG\vcp-s\Gamma_bot\com\handlers\finanzas.py:53:1: W293 blank line contains whitespace
E:\PG\vcp-s\Gamma_bot\com\handlers\finanzas.py:68:80: E501 line too long (102 > 79 characters)
E:\PG\vcp-s\Gamma_bot\com\handlers\finanzas.py:69:1: W293 blank line contains whitespace
E:\PG\vcp-s\Gamma_bot\com\handlers\finanzas.py:73:1: W293 blank line contains whitespace
E:\PG\vcp-s\Gamma_bot\com\handlers\finanzas.py:74:80: E501 line too long (93 > 79 characters)
E:\PG\vcp-s\Gamma_bot\com\handlers\finanzas.py:75:1: W293 blank line contains whitespace
E:\PG\vcp-s\Gamma_bot\com\handlers\finanzas.py:77:80: E501 line too long (106 > 79 characters)
E:\PG\vcp-s\Gamma_bot\com\handlers\finanzas.py:79:1: W293 blank line contains whitespace
E:\PG\vcp-s\Gamma_bot\com\handlers\finanzas.py:81:1: W293 blank line contains whitespace
E:\PG\vcp-s\Gamma_bot\com\handlers\finanzas.py:84:1: W293 blank line contains whitespace
E:\PG\vcp-s\Gamma_bot\com\handlers\finanzas.py:85:80: E501 line too long (116 > 79 characters)
E:\PG\vcp-s\Gamma_bot\com\handlers\finanzas.py:86:80: E501 line too long (114 > 79 characters)
E:\PG\vcp-s\Gamma_bot\com\handlers\finanzas.py:87:80: E501 line too long (118 > 79 characters)
E:\PG\vcp-s\Gamma_bot\com\handlers\finanzas.py:88:1: W293 blank line contains whitespace
E:\PG\vcp-s\Gamma_bot\com\handlers\finanzas.py:102:1: W293 blank line contains whitespace
E:\PG\vcp-s\Gamma_bot\com\handlers\finanzas.py:105:80: E501 line too long (100 > 79 characters)
E:\PG\vcp-s\Gamma_bot\com\handlers\finanzas.py:106:80: E501 line too long (98 > 79 characters)
E:\PG\vcp-s\Gamma_bot\com\handlers\finanzas.py:108:1: W293 blank line contains whitespace
E:\PG\vcp-s\Gamma_bot\com\handlers\finanzas.py:109:80: E501 line too long (137 > 79 characters)
E:\PG\vcp-s\Gamma_bot\com\handlers\finanzas.py:110:1: W293 blank line contains whitespace
E:\PG\vcp-s\Gamma_bot\com\handlers\finanzas.py:113:80: E501 line too long (122 > 79 characters)
E:\PG\vcp-s\Gamma_bot\com\handlers\finanzas.py:123:1: W293 blank line contains whitespace
E:\PG\vcp-s\Gamma_bot\com\handlers\finanzas.py:126:80: E501 line too long (107 > 79 characters)
E:\PG\vcp-s\Gamma_bot\com\handlers\finanzas.py:128:1: W293 blank line contains whitespace
E:\PG\vcp-s\Gamma_bot\com\handlers\finanzas.py:132:80: E501 line too long (120 > 79 characters)
E:\PG\vcp-s\Gamma_bot\com\handlers\finanzas.py:133:80: E501 line too long (115 > 79 characters)
E:\PG\vcp-s\Gamma_bot\com\handlers\finanzas.py:135:1: W293 blank line contains whitespace
E:\PG\vcp-s\Gamma_bot\com\handlers\finanzas.py:136:80: E501 line too long (118 > 79 characters)
E:\PG\vcp-s\Gamma_bot\com\handlers\finanzas.py:137:80: E501 line too long (83 > 79 characters)
E:\PG\vcp-s\Gamma_bot\com\handlers\finanzas.py:138:80: E501 line too long (95 > 79 characters)
E:\PG\vcp-s\Gamma_bot\com\handlers\finanzas.py:139:1: W293 blank line contains whitespace
E:\PG\vcp-s\Gamma_bot\com\handlers\finanzas.py:142:80: E501 line too long (84 > 79 characters)
E:\PG\vcp-s\Gamma_bot\config.py:10:80: E501 line too long (85 > 79 characters)
E:\PG\vcp-s\Gamma_bot\config.py:12:80: E501 line too long (90 > 79 characters)
E:\PG\vcp-s\Gamma_bot\config.py:22:1: E302 expected 2 blank lines, found 1
E:\PG\vcp-s\Gamma_bot\config.py:26:1: E302 expected 2 blank lines, found 1
E:\PG\vcp-s\Gamma_bot\config.py:27:80: E501 line too long (86 > 79 characters)
E:\PG\vcp-s\Gamma_bot\flask_app.py:20:80: E501 line too long (80 > 79 characters)
E:\PG\vcp-s\Gamma_bot\flask_app.py:23:1: E402 module level import not at top of file
E:\PG\vcp-s\Gamma_bot\flask_app.py:26:1: E302 expected 2 blank lines, found 1
E:\PG\vcp-s\Gamma_bot\flask_app.py:41:80: E501 line too long (80 > 79 characters)
E:\PG\vcp-s\Gamma_bot\flask_app.py:45:16: E701 multiple statements on one line (colon)
E:\PG\vcp-s\Gamma_bot\flask_app.py:45:40: W291 trailing whitespace
E:\PG\vcp-s\Gamma_bot\flask_app.py:46:13: E722 do not use bare 'except'
E:\PG\vcp-s\Gamma_bot\flask_app.py:46:19: E701 multiple statements on one line (colon)
E:\PG\vcp-s\Gamma_bot\flask_app.py:52:80: E501 line too long (84 > 79 characters)
E:\PG\vcp-s\Gamma_bot\flask_app.py:53:80: E501 line too long (82 > 79 characters)
E:\PG\vcp-s\Gamma_bot\flask_app.py:61:1: E302 expected 2 blank lines, found 1
E:\PG\vcp-s\Gamma_bot\flask_app.py:64:80: E501 line too long (81 > 79 characters)
E:\PG\vcp-s\Gamma_bot\flask_app.py:69:1: E302 expected 2 blank lines, found 1
E:\PG\vcp-s\Gamma_bot\flask_app.py:73:80: E501 line too long (80 > 79 characters)
E:\PG\vcp-s\Gamma_bot\flask_app.py:74:1: E302 expected 2 blank lines, found 1
E:\PG\vcp-s\Gamma_bot\flask_app.py:83:80: E501 line too long (82 > 79 characters)
E:\PG\vcp-s\Gamma_bot\flask_app.py:88:80: E501 line too long (81 > 79 characters)
E:\PG\vcp-s\Gamma_bot\flask_app.py:93:80: E501 line too long (85 > 79 characters)
E:\PG\vcp-s\Gamma_bot\flask_app.py:129:80: E501 line too long (82 > 79 characters)
E:\PG\vcp-s\Gamma_bot\flask_app.py:142:80: E501 line too long (199 > 79 characters)
E:\PG\vcp-s\Gamma_bot\flask_app.py:147:80: E501 line too long (98 > 79 characters)
E:\PG\vcp-s\Gamma_bot\flask_app.py:156:80: E501 line too long (89 > 79 characters)
E:\PG\vcp-s\Gamma_bot\flask_app.py:194:80: E501 line too long (94 > 79 characters)
E:\PG\vcp-s\Gamma_bot\flask_app.py:208:80: E501 line too long (97 > 79 characters)
E:\PG\vcp-s\Gamma_bot\flask_app.py:220:80: E501 line too long (94 > 79 characters)
E:\PG\vcp-s\Gamma_bot\flask_app.py:229:80: E501 line too long (95 > 79 characters)
E:\PG\vcp-s\Gamma_bot\flask_app.py:242:80: E501 line too long (115 > 79 characters)
E:\PG\vcp-s\Gamma_bot\flask_app.py:255:80: E501 line too long (99 > 79 characters)
E:\PG\vcp-s\Gamma_bot\logger_config.py:12:1: E302 expected 2 blank lines, found 1
E:\PG\vcp-s\Gamma_bot\logger_config.py:16:1: W293 blank line contains whitespace
E:\PG\vcp-s\Gamma_bot\logger_config.py:23:1: E302 expected 2 blank lines, found 1
E:\PG\vcp-s\Gamma_bot\logger_config.py:28:1: W293 blank line contains whitespace
E:\PG\vcp-s\Gamma_bot\logger_config.py:34:13: F821 undefined name 'os'
E:\PG\vcp-s\Gamma_bot\logger_config.py:37:1: W293 blank line contains whitespace
E:\PG\vcp-s\Gamma_bot\logic\ai_service.py:2:1: F401 'typing.Any' imported but unused
E:\PG\vcp-s\Gamma_bot\logic\ai_service.py:16:1: E302 expected 2 blank lines, found 1
E:\PG\vcp-s\Gamma_bot\logic\ai_service.py:18:80: E501 line too long (85 > 79 characters)
E:\PG\vcp-s\Gamma_bot\logic\ai_service.py:27:80: E501 line too long (103 > 79 characters)
E:\PG\vcp-s\Gamma_bot\logic\ai_service.py:29:80: E501 line too long (106 > 79 characters)
E:\PG\vcp-s\Gamma_bot\logic\ai_service.py:30:80: E501 line too long (84 > 79 characters)
E:\PG\vcp-s\Gamma_bot\logic\ai_service.py:32:80: E501 line too long (127 > 79 characters)
E:\PG\vcp-s\Gamma_bot\logic\ai_service.py:34:80: E501 line too long (92 > 79 characters)
E:\PG\vcp-s\Gamma_bot\logic\ai_service.py:35:80: E501 line too long (118 > 79 characters)
E:\PG\vcp-s\Gamma_bot\logic\ai_service.py:36:80: E501 line too long (142 > 79 characters)
E:\PG\vcp-s\Gamma_bot\logic\ai_service.py:37:80: E501 line too long (80 > 79 characters)
E:\PG\vcp-s\Gamma_bot\logic\ai_service.py:43:80: E501 line too long (108 > 79 characters)
E:\PG\vcp-s\Gamma_bot\logic\ai_service.py:44:80: E501 line too long (89 > 79 characters)
E:\PG\vcp-s\Gamma_bot\logic\ai_service.py:64:1: W293 blank line contains whitespace
E:\PG\vcp-s\Gamma_bot\logic\ai_service.py:66:80: E501 line too long (97 > 79 characters)
E:\PG\vcp-s\Gamma_bot\logic\ai_service.py:67:80: E501 line too long (128 > 79 characters)
E:\PG\vcp-s\Gamma_bot\logic\ai_service.py:70:80: E501 line too long (84 > 79 characters)
E:\PG\vcp-s\Gamma_bot\logic\ai_service.py:71:80: E501 line too long (99 > 79 characters)
E:\PG\vcp-s\Gamma_bot\logic\ai_service.py:72:80: E501 line too long (95 > 79 characters)
E:\PG\vcp-s\Gamma_bot\logic\ai_service.py:73:80: E501 line too long (122 > 79 characters)
E:\PG\vcp-s\Gamma_bot\logic\ai_service.py:76:1: W293 blank line contains whitespace
E:\PG\vcp-s\Gamma_bot\logic\ai_service.py:77:80: E501 line too long (129 > 79 characters)
E:\PG\vcp-s\Gamma_bot\logic\ai_service.py:78:1: W293 blank line contains whitespace
E:\PG\vcp-s\Gamma_bot\logic\ai_service.py:83:80: E501 line too long (101 > 79 characters)
E:\PG\vcp-s\Gamma_bot\logic\ai_service.py:92:80: E501 line too long (91 > 79 characters)
E:\PG\vcp-s\Gamma_bot\logic\ai_service.py:96:23: E701 multiple statements on one line (colon)
E:\PG\vcp-s\Gamma_bot\logic\ai_service.py:96:80: E501 line too long (90 > 79 characters)
E:\PG\vcp-s\Gamma_bot\logic\ai_service.py:101:80: E501 line too long (84 > 79 characters)
E:\PG\vcp-s\Gamma_bot\logic\ai_service.py:102:80: E501 line too long (110 > 79 characters)
E:\PG\vcp-s\Gamma_bot\logic\ai_service.py:104:80: E501 line too long (145 > 79 characters)
E:\PG\vcp-s\Gamma_bot\logic\ai_service.py:105:80: E501 line too long (125 > 79 characters)
E:\PG\vcp-s\Gamma_bot\logic\ai_service.py:106:80: E501 line too long (146 > 79 characters)
E:\PG\vcp-s\Gamma_bot\logic\ai_service.py:107:80: E501 line too long (100 > 79 characters)
E:\PG\vcp-s\Gamma_bot\logic\ai_service.py:108:80: E501 line too long (93 > 79 characters)
E:\PG\vcp-s\Gamma_bot\logic\ai_service.py:110:80: E501 line too long (114 > 79 characters)
E:\PG\vcp-s\Gamma_bot\logic\ai_service.py:111:80: E501 line too long (109 > 79 characters)
E:\PG\vcp-s\Gamma_bot\logic\ai_service.py:112:80: E501 line too long (85 > 79 characters)
E:\PG\vcp-s\Gamma_bot\logic\ai_service.py:113:80: E501 line too long (117 > 79 characters)
E:\PG\vcp-s\Gamma_bot\logic\ai_service.py:114:80: E501 line too long (120 > 79 characters)
E:\PG\vcp-s\Gamma_bot\logic\ai_service.py:115:80: E501 line too long (80 > 79 characters)
E:\PG\vcp-s\Gamma_bot\logic\ai_service.py:119:80: E501 line too long (87 > 79 characters)
E:\PG\vcp-s\Gamma_bot\logic\ai_service.py:123:80: E501 line too long (89 > 79 characters)
E:\PG\vcp-s\Gamma_bot\logic\ai_service.py:141:23: E701 multiple statements on one line (colon)
E:\PG\vcp-s\Gamma_bot\logic\ai_service.py:141:80: E501 line too long (90 > 79 characters)
E:\PG\vcp-s\Gamma_bot\logic\ai_service.py:143:80: E501 line too long (96 > 79 characters)
E:\PG\vcp-s\Gamma_bot\logic\ai_service.py:148:80: E501 line too long (116 > 79 characters)
E:\PG\vcp-s\Gamma_bot\logic\ai_service.py:149:80: E501 line too long (126 > 79 characters)
E:\PG\vcp-s\Gamma_bot\logic\ai_service.py:150:80: E501 line too long (105 > 79 characters)
E:\PG\vcp-s\Gamma_bot\logic\ai_service.py:151:80: E501 line too long (118 > 79 characters)
E:\PG\vcp-s\Gamma_bot\logic\ai_service.py:152:80: E501 line too long (142 > 79 characters)
E:\PG\vcp-s\Gamma_bot\logic\ai_service.py:153:80: E501 line too long (236 > 79 characters)
E:\PG\vcp-s\Gamma_bot\logic\ai_service.py:154:80: E501 line too long (200 > 79 characters)
E:\PG\vcp-s\Gamma_bot\logic\ai_service.py:155:80: E501 line too long (135 > 79 characters)
E:\PG\vcp-s\Gamma_bot\logic\ai_service.py:161:80: E501 line too long (108 > 79 characters)
E:\PG\vcp-s\Gamma_bot\logic\ai_service.py:162:80: E501 line too long (89 > 79 characters)
E:\PG\vcp-s\Gamma_bot\logic\ai_service.py:168:80: E501 line too long (110 > 79 characters)
E:\PG\vcp-s\Gamma_bot\logic\ai_service.py:169:80: E501 line too long (86 > 79 characters)
E:\PG\vcp-s\Gamma_bot\logic\ai_service.py:172:80: E501 line too long (81 > 79 characters)
E:\PG\vcp-s\Gamma_bot\logic\constants.py:2:1: F401 'typing.Any' imported but unused
E:\PG\vcp-s\Gamma_bot\logic\constants.py:15:80: E501 line too long (89 > 79 characters)
E:\PG\vcp-s\Gamma_bot\logic\constants.py:23:80: E501 line too long (88 > 79 characters)
E:\PG\vcp-s\Gamma_bot\logic\constants.py:27:80: E501 line too long (113 > 79 characters)
E:\PG\vcp-s\Gamma_bot\logic\constants.py:28:80: E501 line too long (160 > 79 characters)
E:\PG\vcp-s\Gamma_bot\logic\constants.py:29:80: E501 line too long (117 > 79 characters)
E:\PG\vcp-s\Gamma_bot\logic\cron_jobs.py:19:1: E302 expected 2 blank lines, found 1
E:\PG\vcp-s\Gamma_bot\logic\cron_jobs.py:27:9: F401 'gspread' imported but unused
E:\PG\vcp-s\Gamma_bot\logic\cron_jobs.py:37:80: E501 line too long (86 > 79 characters)
E:\PG\vcp-s\Gamma_bot\logic\cron_jobs.py:50:80: E501 line too long (80 > 79 characters)
E:\PG\vcp-s\Gamma_bot\logic\cron_jobs.py:75:80: E501 line too long (82 > 79 characters)
E:\PG\vcp-s\Gamma_bot\logic\cron_jobs.py:85:80: E501 line too long (102 > 79 characters)
E:\PG\vcp-s\Gamma_bot\logic\cron_jobs.py:90:80: E501 line too long (80 > 79 characters)
E:\PG\vcp-s\Gamma_bot\logic\cron_jobs.py:145:17: E221 multiple spaces before operator
E:\PG\vcp-s\Gamma_bot\logic\cron_jobs.py:146:17: E221 multiple spaces before operator
E:\PG\vcp-s\Gamma_bot\logic\cron_jobs.py:147:17: E221 multiple spaces before operator
E:\PG\vcp-s\Gamma_bot\logic\cron_jobs.py:149:15: E221 multiple spaces before operator
E:\PG\vcp-s\Gamma_bot\logic\cron_jobs.py:151:80: E501 line too long (89 > 79 characters)
E:\PG\vcp-s\Gamma_bot\logic\cron_jobs.py:156:80: E501 line too long (90 > 79 characters)
E:\PG\vcp-s\Gamma_bot\logic\cron_jobs.py:158:80: E501 line too long (99 > 79 characters)
E:\PG\vcp-s\Gamma_bot\logic\cron_jobs.py:176:80: E501 line too long (106 > 79 characters)
E:\PG\vcp-s\Gamma_bot\logic\cron_jobs.py:204:80: E501 line too long (121 > 79 characters)
E:\PG\vcp-s\Gamma_bot\logic\cron_jobs.py:206:80: E501 line too long (99 > 79 characters)
E:\PG\vcp-s\Gamma_bot\logic\cron_jobs.py:217:1: E302 expected 2 blank lines, found 1
E:\PG\vcp-s\Gamma_bot\logic\cron_jobs.py:226:1: W293 blank line contains whitespace
E:\PG\vcp-s\Gamma_bot\logic\cron_jobs.py:227:80: E501 line too long (88 > 79 characters)
E:\PG\vcp-s\Gamma_bot\logic\cron_jobs.py:228:1: W293 blank line contains whitespace
E:\PG\vcp-s\Gamma_bot\logic\cron_jobs.py:230:80: E501 line too long (89 > 79 characters)
E:\PG\vcp-s\Gamma_bot\logic\cron_jobs.py:234:80: E501 line too long (80 > 79 characters)
E:\PG\vcp-s\Gamma_bot\logic\cron_jobs.py:243:80: E501 line too long (84 > 79 characters)
E:\PG\vcp-s\Gamma_bot\logic\cron_jobs.py:245:80: E501 line too long (81 > 79 characters)
E:\PG\vcp-s\Gamma_bot\logic\cron_jobs.py:247:80: E501 line too long (83 > 79 characters)
E:\PG\vcp-s\Gamma_bot\logic\cron_jobs.py:257:1: W293 blank line contains whitespace
E:\PG\vcp-s\Gamma_bot\logic\cron_jobs.py:267:1: E302 expected 2 blank lines, found 1
E:\PG\vcp-s\Gamma_bot\logic\cron_jobs.py:269:80: E501 line too long (80 > 79 characters)
E:\PG\vcp-s\Gamma_bot\logic\cron_jobs.py:276:1: W293 blank line contains whitespace
E:\PG\vcp-s\Gamma_bot\logic\cron_jobs.py:281:1: W293 blank line contains whitespace
E:\PG\vcp-s\Gamma_bot\logic\cron_jobs.py:284:1: W293 blank line contains whitespace
E:\PG\vcp-s\Gamma_bot\logic\cron_jobs.py:285:80: E501 line too long (80 > 79 characters)
E:\PG\vcp-s\Gamma_bot\logic\cron_jobs.py:288:80: E501 line too long (83 > 79 characters)
E:\PG\vcp-s\Gamma_bot\logic\cron_jobs.py:291:80: E501 line too long (82 > 79 characters)
E:\PG\vcp-s\Gamma_bot\logic\cron_jobs.py:292:1: W293 blank line contains whitespace
E:\PG\vcp-s\Gamma_bot\logic\cron_jobs.py:295:1: W293 blank line contains whitespace
E:\PG\vcp-s\Gamma_bot\logic\cron_jobs.py:296:80: E501 line too long (81 > 79 characters)
E:\PG\vcp-s\Gamma_bot\logic\cron_jobs.py:297:1: W293 blank line contains whitespace
E:\PG\vcp-s\Gamma_bot\logic\cron_jobs.py:303:1: W293 blank line contains whitespace
E:\PG\vcp-s\Gamma_bot\logic\cron_jobs.py:307:1: W293 blank line contains whitespace
E:\PG\vcp-s\Gamma_bot\logic\financiero.py:2:1: F401 'typing.Any' imported but unused
E:\PG\vcp-s\Gamma_bot\logic\financiero.py:4:1: F401 'json' imported but unused
E:\PG\vcp-s\Gamma_bot\logic\financiero.py:10:1: F401 'datetime.datetime' imported but unused
E:\PG\vcp-s\Gamma_bot\logic\financiero.py:10:1: E402 module level import not at top of file
E:\PG\vcp-s\Gamma_bot\logic\financiero.py:11:1: E402 module level import not at top of file
E:\PG\vcp-s\Gamma_bot\logic\financiero.py:12:1: F401 'google.genai' imported but unused
E:\PG\vcp-s\Gamma_bot\logic\financiero.py:12:1: E402 module level import not at top of file
E:\PG\vcp-s\Gamma_bot\logic\financiero.py:13:1: F401 'google.genai.types' imported but unused
E:\PG\vcp-s\Gamma_bot\logic\financiero.py:13:1: E402 module level import not at top of file
E:\PG\vcp-s\Gamma_bot\logic\financiero.py:15:1: E402 module level import not at top of file
E:\PG\vcp-s\Gamma_bot\logic\financiero.py:19:1: E302 expected 2 blank lines, found 1
E:\PG\vcp-s\Gamma_bot\logic\financiero.py:22:80: E501 line too long (96 > 79 characters)
E:\PG\vcp-s\Gamma_bot\logic\financiero.py:23:80: E501 line too long (81 > 79 characters)
E:\PG\vcp-s\Gamma_bot\logic\financiero.py:26:80: E501 line too long (141 > 79 characters)
E:\PG\vcp-s\Gamma_bot\logic\financiero.py:48:80: E501 line too long (106 > 79 characters)
E:\PG\vcp-s\Gamma_bot\logic\financiero.py:56:80: E501 line too long (98 > 79 characters)
E:\PG\vcp-s\Gamma_bot\logic\financiero.py:57:80: E501 line too long (88 > 79 characters)
E:\PG\vcp-s\Gamma_bot\logic\financiero.py:59:80: E501 line too long (105 > 79 characters)
E:\PG\vcp-s\Gamma_bot\logic\financiero.py:61:80: E501 line too long (100 > 79 characters)
E:\PG\vcp-s\Gamma_bot\logic\financiero.py:64:80: E501 line too long (98 > 79 characters)
E:\PG\vcp-s\Gamma_bot\logic\financiero.py:66:80: E501 line too long (86 > 79 characters)
E:\PG\vcp-s\Gamma_bot\logic\financiero.py:68:1: W293 blank line contains whitespace
E:\PG\vcp-s\Gamma_bot\logic\financiero.py:70:80: E501 line too long (82 > 79 characters)
E:\PG\vcp-s\Gamma_bot\logic\financiero.py:71:80: E501 line too long (163 > 79 characters)
E:\PG\vcp-s\Gamma_bot\logic\financiero.py:73:80: E501 line too long (84 > 79 characters)
E:\PG\vcp-s\Gamma_bot\logic\financiero.py:84:21: E701 multiple statements on one line (colon)
E:\PG\vcp-s\Gamma_bot\logic\financiero.py:87:12: E701 multiple statements on one line (colon)
E:\PG\vcp-s\Gamma_bot\logic\financiero.py:88:26: E701 multiple statements on one line (colon)
E:\PG\vcp-s\Gamma_bot\logic\financiero.py:97:80: E501 line too long (85 > 79 characters)
E:\PG\vcp-s\Gamma_bot\logic\financiero.py:98:1: W293 blank line contains whitespace
E:\PG\vcp-s\Gamma_bot\logic\financiero.py:101:1: W293 blank line contains whitespace
E:\PG\vcp-s\Gamma_bot\logic\financiero.py:103:80: E501 line too long (113 > 79 characters)
E:\PG\vcp-s\Gamma_bot\logic\financiero.py:104:61: E261 at least two spaces before inline comment
E:\PG\vcp-s\Gamma_bot\logic\financiero.py:106:80: E501 line too long (129 > 79 characters)
E:\PG\vcp-s\Gamma_bot\logic\financiero.py:111:1: W293 blank line contains whitespace
E:\PG\vcp-s\Gamma_bot\logic\financiero.py:132:1: W293 blank line contains whitespace
E:\PG\vcp-s\Gamma_bot\logic\financiero.py:133:80: E501 line too long (80 > 79 characters)
E:\PG\vcp-s\Gamma_bot\logic\financiero.py:134:1: W293 blank line contains whitespace
E:\PG\vcp-s\Gamma_bot\logic\financiero.py:136:80: E501 line too long (83 > 79 characters)
E:\PG\vcp-s\Gamma_bot\logic\financiero.py:137:80: E501 line too long (157 > 79 characters)
E:\PG\vcp-s\Gamma_bot\logic\financiero.py:144:80: E501 line too long (84 > 79 characters)
E:\PG\vcp-s\Gamma_bot\logic\financiero.py:147:53: E261 at least two spaces before inline comment
E:\PG\vcp-s\Gamma_bot\logic\financiero.py:148:1: W293 blank line contains whitespace
E:\PG\vcp-s\Gamma_bot\logic\financiero.py:151:1: W293 blank line contains whitespace
E:\PG\vcp-s\Gamma_bot\logic\financiero.py:153:33: E701 multiple statements on one line (colon)
E:\PG\vcp-s\Gamma_bot\logic\financiero.py:164:1: W293 blank line contains whitespace
E:\PG\vcp-s\Gamma_bot\logic\financiero.py:166:1: W293 blank line contains whitespace
E:\PG\vcp-s\Gamma_bot\logic\financiero.py:178:1: W293 blank line contains whitespace
E:\PG\vcp-s\Gamma_bot\logic\financiero.py:182:1: W293 blank line contains whitespace
E:\PG\vcp-s\Gamma_bot\logic\financiero.py:183:9: F841 local variable 'headers' is assigned to but never used
E:\PG\vcp-s\Gamma_bot\logic\financiero.py:185:1: W293 blank line contains whitespace
E:\PG\vcp-s\Gamma_bot\logic\financiero.py:188:80: E501 line too long (104 > 79 characters)
E:\PG\vcp-s\Gamma_bot\logic\financiero.py:190:80: E501 line too long (86 > 79 characters)
E:\PG\vcp-s\Gamma_bot\logic\financiero.py:198:1: W293 blank line contains whitespace
E:\PG\vcp-s\Gamma_bot\logic\financiero.py:199:80: E501 line too long (103 > 79 characters)
E:\PG\vcp-s\Gamma_bot\logic\financiero.py:201:80: E501 line too long (89 > 79 characters)
E:\PG\vcp-s\Gamma_bot\logic\financiero.py:203:1: W293 blank line contains whitespace
E:\PG\vcp-s\Gamma_bot\logic\financiero.py:208:1: W293 blank line contains whitespace
E:\PG\vcp-s\Gamma_bot\logic\financiero.py:216:1: W293 blank line contains whitespace
E:\PG\vcp-s\Gamma_bot\logic\financiero.py:221:1: W293 blank line contains whitespace
E:\PG\vcp-s\Gamma_bot\logic\financiero.py:235:80: E501 line too long (98 > 79 characters)
E:\PG\vcp-s\Gamma_bot\logic\logic.py:2:1: F401 'typing.Any' imported but unused
E:\PG\vcp-s\Gamma_bot\logic\logic.py:3:1: F401 'gspread' imported but unused
E:\PG\vcp-s\Gamma_bot\logic\logic.py:4:1: F401 'google.oauth2.service_account.Credentials' imported but unused
E:\PG\vcp-s\Gamma_bot\logic\logic.py:18:1: E402 module level import not at top of file
E:\PG\vcp-s\Gamma_bot\logic\logic.py:22:1: E302 expected 2 blank lines, found 1
E:\PG\vcp-s\Gamma_bot\logic\logic.py:33:1: E303 too many blank lines (4)
E:\PG\vcp-s\Gamma_bot\logic\logic.py:40:80: E501 line too long (110 > 79 characters)
E:\PG\vcp-s\Gamma_bot\logic\logic.py:43:80: E501 line too long (101 > 79 characters)
E:\PG\vcp-s\Gamma_bot\logic\logic.py:45:13: F811 redefinition of unused 'Credentials' from line 4
E:\PG\vcp-s\Gamma_bot\logic\logic.py:46:13: F811 redefinition of unused 'gspread' from line 3
E:\PG\vcp-s\Gamma_bot\logic\logic.py:47:80: E501 line too long (95 > 79 characters)
E:\PG\vcp-s\Gamma_bot\logic\logic.py:49:80: E501 line too long (97 > 79 characters)
E:\PG\vcp-s\Gamma_bot\logic\logic.py:57:13: F811 redefinition of unused 'Credentials' from line 4
E:\PG\vcp-s\Gamma_bot\logic\logic.py:59:80: E501 line too long (90 > 79 characters)
E:\PG\vcp-s\Gamma_bot\logic\logic.py:60:80: E501 line too long (86 > 79 characters)
E:\PG\vcp-s\Gamma_bot\logic\logic.py:61:80: E501 line too long (99 > 79 characters)
E:\PG\vcp-s\Gamma_bot\logic\logic.py:100:5: E303 too many blank lines (3)
E:\PG\vcp-s\Gamma_bot\logic\logic.py:102:80: E501 line too long (96 > 79 characters)
E:\PG\vcp-s\Gamma_bot\logic\logic.py:122:80: E501 line too long (96 > 79 characters)
E:\PG\vcp-s\Gamma_bot\logic\logic.py:138:80: E501 line too long (103 > 79 characters)
E:\PG\vcp-s\Gamma_bot\logic\logic.py:144:80: E501 line too long (144 > 79 characters)
E:\PG\vcp-s\Gamma_bot\logic\logic.py:145:80: E501 line too long (87 > 79 characters)
E:\PG\vcp-s\Gamma_bot\logic\logic.py:147:80: E501 line too long (110 > 79 characters)
E:\PG\vcp-s\Gamma_bot\logic\logic.py:165:24: E221 multiple spaces before operator
E:\PG\vcp-s\Gamma_bot\logic\logic.py:165:80: E501 line too long (98 > 79 characters)
E:\PG\vcp-s\Gamma_bot\logic\logic.py:181:80: E501 line too long (81 > 79 characters)
E:\PG\vcp-s\Gamma_bot\logic\logic.py:187:80: E501 line too long (105 > 79 characters)
E:\PG\vcp-s\Gamma_bot\logic\logic.py:189:80: E501 line too long (83 > 79 characters)
E:\PG\vcp-s\Gamma_bot\logic\logic.py:206:80: E501 line too long (86 > 79 characters)
E:\PG\vcp-s\Gamma_bot\logic\logic.py:225:80: E501 line too long (80 > 79 characters)
E:\PG\vcp-s\Gamma_bot\logic\logic.py:230:80: E501 line too long (80 > 79 characters)
E:\PG\vcp-s\Gamma_bot\logic\logic.py:232:80: E501 line too long (115 > 79 characters)
E:\PG\vcp-s\Gamma_bot\logic\logic.py:233:80: E501 line too long (103 > 79 characters)
E:\PG\vcp-s\Gamma_bot\logic\logic.py:236:80: E501 line too long (97 > 79 characters)
E:\PG\vcp-s\Gamma_bot\logic\logic.py:237:80: E501 line too long (123 > 79 characters)
E:\PG\vcp-s\Gamma_bot\logic\logic.py:239:80: E501 line too long (104 > 79 characters)
E:\PG\vcp-s\Gamma_bot\logic\logic.py:241:80: E501 line too long (80 > 79 characters)
E:\PG\vcp-s\Gamma_bot\logic\logic.py:245:80: E501 line too long (104 > 79 characters)
E:\PG\vcp-s\Gamma_bot\logic\logic.py:253:80: E501 line too long (81 > 79 characters)
E:\PG\vcp-s\Gamma_bot\logic\logic.py:259:55: E231 missing whitespace after ','
E:\PG\vcp-s\Gamma_bot\logic\logic.py:273:1: W293 blank line contains whitespace
E:\PG\vcp-s\Gamma_bot\logic\logic.py:294:80: E501 line too long (90 > 79 characters)
E:\PG\vcp-s\Gamma_bot\logic\logic.py:296:80: E501 line too long (85 > 79 characters)
E:\PG\vcp-s\Gamma_bot\logic\logic.py:298:80: E501 line too long (115 > 79 characters)
E:\PG\vcp-s\Gamma_bot\logic\logic.py:315:1: W293 blank line contains whitespace
E:\PG\vcp-s\Gamma_bot\logic\logic.py:322:80: E501 line too long (98 > 79 characters)
E:\PG\vcp-s\Gamma_bot\logic\logic.py:336:80: E501 line too long (80 > 79 characters)
E:\PG\vcp-s\Gamma_bot\logic\logic.py:348:80: E501 line too long (108 > 79 characters)
E:\PG\vcp-s\Gamma_bot\logic\logic.py:373:13: F841 local variable 'evento_creado' is assigned to but never used
E:\PG\vcp-s\Gamma_bot\logic\logic.py:373:80: E501 line too long (99 > 79 characters)
E:\PG\vcp-s\Gamma_bot\logic\logic.py:374:80: E501 line too long (90 > 79 characters)
E:\PG\vcp-s\Gamma_bot\logic\logic.py:379:80: E501 line too long (91 > 79 characters)
E:\PG\vcp-s\Gamma_bot\logic\logic.py:387:80: E501 line too long (81 > 79 characters)
E:\PG\vcp-s\Gamma_bot\logic\logic.py:396:1: W293 blank line contains whitespace
E:\PG\vcp-s\Gamma_bot\logic\logic.py:400:1: W293 blank line contains whitespace
E:\PG\vcp-s\Gamma_bot\logic\logic.py:402:40: W291 trailing whitespace
E:\PG\vcp-s\Gamma_bot\logic\logic.py:403:35: W291 trailing whitespace
E:\PG\vcp-s\Gamma_bot\logic\logic.py:405:31: W291 trailing whitespace
E:\PG\vcp-s\Gamma_bot\logic\logic.py:409:1: W293 blank line contains whitespace
E:\PG\vcp-s\Gamma_bot\logic\logic.py:411:1: W293 blank line contains whitespace
E:\PG\vcp-s\Gamma_bot\logic\logic.py:414:80: E501 line too long (84 > 79 characters)
E:\PG\vcp-s\Gamma_bot\logic\logic.py:419:17: E722 do not use bare 'except'
E:\PG\vcp-s\Gamma_bot\logic\logic.py:421:1: W293 blank line contains whitespace
E:\PG\vcp-s\Gamma_bot\logic\logic.py:437:1: W293 blank line contains whitespace
E:\PG\vcp-s\Gamma_bot\logic\logic.py:440:80: E501 line too long (88 > 79 characters)
E:\PG\vcp-s\Gamma_bot\logic\logic.py:449:80: E501 line too long (81 > 79 characters)
E:\PG\vcp-s\Gamma_bot\logic\logic.py:467:1: E302 expected 2 blank lines, found 1
E:\PG\vcp-s\Gamma_bot\logic\logic.py:486:5: F811 redefinition of unused 'HORARIOS_MATERIAS' from line 469
E:\PG\vcp-s\Gamma_bot\logic\logic.py:494:5: E303 too many blank lines (4)
E:\PG\vcp-s\Gamma_bot\logic\logic.py:495:24: E701 multiple statements on one line (colon)
E:\PG\vcp-s\Gamma_bot\logic\logic.py:497:1: W293 blank line contains whitespace
E:\PG\vcp-s\Gamma_bot\logic\logic.py:500:1: W293 blank line contains whitespace
E:\PG\vcp-s\Gamma_bot\logic\logic.py:505:1: W293 blank line contains whitespace
E:\PG\vcp-s\Gamma_bot\logic\logic.py:508:1: W293 blank line contains whitespace
E:\PG\vcp-s\Gamma_bot\logic\logic.py:513:1: W293 blank line contains whitespace
E:\PG\vcp-s\Gamma_bot\logic\logic.py:530:1: W293 blank line contains whitespace
E:\PG\vcp-s\Gamma_bot\logic\logic.py:532:80: E501 line too long (110 > 79 characters)
E:\PG\vcp-s\Gamma_bot\logic\logic.py:534:1: W293 blank line contains whitespace
E:\PG\vcp-s\Gamma_bot\logic\logic.py:535:80: E501 line too long (83 > 79 characters)
E:\PG\vcp-s\Gamma_bot\logic\logic.py:540:1: W293 blank line contains whitespace
E:\PG\vcp-s\Gamma_bot\logic\logic.py:541:80: E501 line too long (100 > 79 characters)
E:\PG\vcp-s\Gamma_bot\logic\logic.py:543:40: E701 multiple statements on one line (colon)
E:\PG\vcp-s\Gamma_bot\logic\logic.py:544:41: E701 multiple statements on one line (colon)
E:\PG\vcp-s\Gamma_bot\logic\logic.py:551:80: E501 line too long (106 > 79 characters)
E:\PG\vcp-s\Gamma_bot\logic\logic.py:557:5: E303 too many blank lines (2)
E:\PG\vcp-s\Gamma_bot\logic\logic.py:558:80: E501 line too long (96 > 79 characters)
E:\PG\vcp-s\Gamma_bot\logic\logic.py:569:80: E501 line too long (81 > 79 characters)
E:\PG\vcp-s\Gamma_bot\logic\logic.py:580:80: E501 line too long (91 > 79 characters)
E:\PG\vcp-s\Gamma_bot\logic\logic.py:586:80: E501 line too long (130 > 79 characters)
E:\PG\vcp-s\Gamma_bot\logic\logic.py:589:1: W293 blank line contains whitespace
E:\PG\vcp-s\Gamma_bot\logic\logic.py:591:80: E501 line too long (100 > 79 characters)
E:\PG\vcp-s\Gamma_bot\logic\logic.py:593:1: W293 blank line contains whitespace
E:\PG\vcp-s\Gamma_bot\logic\logic.py:600:1: W293 blank line contains whitespace
E:\PG\vcp-s\Gamma_bot\logic\logic.py:604:80: E501 line too long (134 > 79 characters)
E:\PG\vcp-s\Gamma_bot\logic\logic.py:614:80: E501 line too long (99 > 79 characters)
E:\PG\vcp-s\Gamma_bot\logic\logic.py:616:80: E501 line too long (100 > 79 characters)
E:\PG\vcp-s\Gamma_bot\logic\logic.py:617:1: W293 blank line contains whitespace
E:\PG\vcp-s\Gamma_bot\logic\logic.py:622:1: E302 expected 2 blank lines, found 1
E:\PG\vcp-s\Gamma_bot\logic\logic.py:623:80: E501 line too long (121 > 79 characters)
E:\PG\vcp-s\Gamma_bot\logic\logic.py:629:80: E501 line too long (94 > 79 characters)
E:\PG\vcp-s\Gamma_bot\logic\logic.py:637:80: E501 line too long (111 > 79 characters)
E:\PG\vcp-s\Gamma_bot\logic\logic.py:648:80: E501 line too long (89 > 79 characters)
E:\PG\vcp-s\Gamma_bot\logic\logic.py:670:21: W292 no newline at end of file
E:\PG\vcp-s\Gamma_bot\logic\pdf_service.py:2:1: F401 'typing.Any' imported but unused
E:\PG\vcp-s\Gamma_bot\logic\pdf_service.py:15:1: E302 expected 2 blank lines, found 1
E:\PG\vcp-s\Gamma_bot\logic\pdf_service.py:24:1: E302 expected 2 blank lines, found 1
E:\PG\vcp-s\Gamma_bot\logic\pdf_service.py:30:80: E501 line too long (110 > 79 characters)
E:\PG\vcp-s\Gamma_bot\logic\pdf_service.py:31:80: E501 line too long (80 > 79 characters)
E:\PG\vcp-s\Gamma_bot\logic\pdf_service.py:39:1: W293 blank line contains whitespace
E:\PG\vcp-s\Gamma_bot\logic\pdf_service.py:42:1: W293 blank line contains whitespace
E:\PG\vcp-s\Gamma_bot\logic\pdf_service.py:47:1: W293 blank line contains whitespace
E:\PG\vcp-s\Gamma_bot\logic\pdf_service.py:50:80: E501 line too long (136 > 79 characters)
E:\PG\vcp-s\Gamma_bot\logic\pdf_service.py:56:80: E501 line too long (111 > 79 characters)
E:\PG\vcp-s\Gamma_bot\logic\pdf_service.py:57:80: E501 line too long (119 > 79 characters)
E:\PG\vcp-s\Gamma_bot\logic\pdf_service.py:58:80: E501 line too long (145 > 79 characters)
E:\PG\vcp-s\Gamma_bot\logic\pdf_service.py:67:80: E501 line too long (109 > 79 characters)
E:\PG\vcp-s\Gamma_bot\logic\pdf_service.py:68:80: E501 line too long (90 > 79 characters)
E:\PG\vcp-s\Gamma_bot\logic\pdf_service.py:72:1: W293 blank line contains whitespace
E:\PG\vcp-s\Gamma_bot\logic\pdf_service.py:74:80: E501 line too long (86 > 79 characters)
E:\PG\vcp-s\Gamma_bot\logic\pdf_service.py:77:80: E501 line too long (93 > 79 characters)
E:\PG\vcp-s\Gamma_bot\logic\pdf_service.py:79:1: W293 blank line contains whitespace
E:\PG\vcp-s\Gamma_bot\logic\pdf_service.py:98:80: E501 line too long (92 > 79 characters)
E:\PG\vcp-s\Gamma_bot\logic\pdf_service.py:126:80: E501 line too long (85 > 79 characters)
E:\PG\vcp-s\Gamma_bot\repositories\sheets_repository.py:8:1: E302 expected 2 blank lines, found 1
E:\PG\vcp-s\Gamma_bot\repositories\sheets_repository.py:11:9: F401 'logic.financiero.AgenteFinanciero' imported but unused
E:\PG\vcp-s\Gamma_bot\repositories\sheets_repository.py:12:9: F401 'logic.logic.AgenteAutonomoHoras' imported but unused
E:\PG\vcp-s\Gamma_bot\repositories\sheets_repository.py:12:9: F401 'logic.logic.AgenteAsistenciaMaterias' imported but unused
E:\PG\vcp-s\Gamma_bot\repositories\sheets_repository.py:13:80: E501 line too long (90 > 79 characters)
E:\PG\vcp-s\Gamma_bot\repositories\sheets_repository.py:28:80: E501 line too long (80 > 79 characters)
E:\PG\vcp-s\Gamma_bot\repositories\sheets_repository.py:33:80: E501 line too long (87 > 79 characters)
E:\PG\vcp-s\Gamma_bot\run_local.py:2:1: F401 'typing.Any' imported but unused
E:\PG\vcp-s\Gamma_bot\run_local.py:3:1: F401 'os' imported but unused
E:\PG\vcp-s\Gamma_bot\run_local.py:4:1: F401 'dotenv.load_dotenv' imported but unused
E:\PG\vcp-s\Gamma_bot\run_local.py:8:80: E501 line too long (97 > 79 characters)
E:\PG\vcp-s\Gamma_bot\run_local.py:23:80: E501 line too long (93 > 79 characters)
E:\PG\vcp-s\Gamma_bot\run_local.py:27:80: E501 line too long (80 > 79 characters)
E:\PG\vcp-s\Gamma_bot\run_local.py:28:80: E501 line too long (85 > 79 characters)
E:\PG\vcp-s\Gamma_bot\services\telegram_service.py:5:1: E302 expected 2 blank lines, found 1
E:\PG\vcp-s\Gamma_bot\services\telegram_service.py:13:80: E501 line too long (80 > 79 characters)
E:\PG\vcp-s\Gamma_bot\services\telegram_service.py:21:80: E501 line too long (80 > 79 characters)
E:\PG\vcp-s\Gamma_bot\test_qa_suite.py:2:1: F401 'typing.Any' imported but unused
E:\PG\vcp-s\Gamma_bot\test_qa_suite.py:6:1: F401 'unittest.mock.mock_open' imported but unused
E:\PG\vcp-s\Gamma_bot\test_qa_suite.py:7:1: F401 'json' imported but unused
E:\PG\vcp-s\Gamma_bot\test_qa_suite.py:14:1: E402 module level import not at top of file
E:\PG\vcp-s\Gamma_bot\test_qa_suite.py:15:1: F401 'logic.ai_service.AIService' imported but unused
E:\PG\vcp-s\Gamma_bot\test_qa_suite.py:15:1: E402 module level import not at top of file
E:\PG\vcp-s\Gamma_bot\test_qa_suite.py:16:1: E402 module level import not at top of file
E:\PG\vcp-s\Gamma_bot\test_qa_suite.py:17:1: F401 'logic.logic.EstadoGestor' imported but unused
E:\PG\vcp-s\Gamma_bot\test_qa_suite.py:17:1: E402 module level import not at top of file
E:\PG\vcp-s\Gamma_bot\test_qa_suite.py:18:1: F401 'com.core.security.verificar_usuario_manual' imported but unused
E:\PG\vcp-s\Gamma_bot\test_qa_suite.py:18:1: E402 module level import not at top of file
E:\PG\vcp-s\Gamma_bot\test_qa_suite.py:18:80: E501 line too long (91 > 79 characters)
E:\PG\vcp-s\Gamma_bot\test_qa_suite.py:19:1: F401 'logic.cron_jobs.rotar_logs' imported but unused
E:\PG\vcp-s\Gamma_bot\test_qa_suite.py:19:1: F401 'logic.cron_jobs.resumen_semanal' imported but unused
E:\PG\vcp-s\Gamma_bot\test_qa_suite.py:19:1: E402 module level import not at top of file
E:\PG\vcp-s\Gamma_bot\test_qa_suite.py:25:1: E402 module level import not at top of file
E:\PG\vcp-s\Gamma_bot\test_qa_suite.py:130:80: E501 line too long (83 > 79 characters)
E:\PG\vcp-s\Gamma_bot\test_qa_suite.py:131:80: E501 line too long (82 > 79 characters)
E:\PG\vcp-s\Gamma_bot\test_qa_suite.py:132:80: E501 line too long (82 > 79 characters)
E:\PG\vcp-s\Gamma_bot\test_qa_suite.py:134:80: E501 line too long (87 > 79 characters)
E:\PG\vcp-s\Gamma_bot\test_qa_suite.py:141:80: E501 line too long (98 > 79 characters)
E:\PG\vcp-s\Gamma_bot\test_qa_suite.py:142:80: E501 line too long (80 > 79 characters)
E:\PG\vcp-s\Gamma_bot\test_qa_suite.py:143:80: E501 line too long (81 > 79 characters)
E:\PG\vcp-s\Gamma_bot\test_qa_suite.py:146:1: W293 blank line contains whitespace
E:\PG\vcp-s\Gamma_bot\test_qa_suite.py:152:1: W293 blank line contains whitespace
E:\PG\vcp-s\Gamma_bot\test_qa_suite.py:163:80: E501 line too long (89 > 79 characters)
E:\PG\vcp-s\Gamma_bot\test_qa_suite.py:164:1: W293 blank line contains whitespace
E:\PG\vcp-s\Gamma_bot\test_qa_suite.py:168:1: W293 blank line contains whitespace
E:\PG\vcp-s\Gamma_bot\test_qa_suite.py:172:80: E501 line too long (83 > 79 characters)
E:\PG\vcp-s\Gamma_bot\test_qa_suite.py:175:80: E501 line too long (95 > 79 characters)
E:\PG\vcp-s\Gamma_bot\test_qa_suite.py:176:80: E501 line too long (128 > 79 characters)
E:\PG\vcp-s\Gamma_bot\test_qa_suite.py:177:1: W293 blank line contains whitespace
E:\PG\vcp-s\Gamma_bot\test_qa_suite.py:195:1: W293 blank line contains whitespace
E:\PG\vcp-s\Gamma_bot\test_qa_suite.py:198:1: W293 blank line contains whitespace
E:\PG\vcp-s\Gamma_bot\test_qa_suite.py:201:1: W293 blank line contains whitespace
E:\PG\vcp-s\Gamma_bot\test_qa_suite.py:202:80: E501 line too long (87 > 79 characters)
E:\PG\vcp-s\Gamma_bot\test_qa_suite.py:203:80: E501 line too long (92 > 79 characters)
E:\PG\vcp-s\Gamma_bot\test_qa_suite.py:204:1: W293 blank line contains whitespace
E:\PG\vcp-s\Gamma_bot\test_qa_suite.py:221:1: W293 blank line contains whitespace
E:\PG\vcp-s\Gamma_bot\test_qa_suite.py:263:80: E501 line too long (87 > 79 characters)
E:\PG\vcp-s\Gamma_bot\test_qa_suite.py:267:1: W293 blank line contains whitespace
E:\PG\vcp-s\Gamma_bot\test_qa_suite.py:269:80: E501 line too long (102 > 79 characters)
E:\PG\vcp-s\Gamma_bot\test_qa_suite.py:271:80: E501 line too long (84 > 79 characters)
```