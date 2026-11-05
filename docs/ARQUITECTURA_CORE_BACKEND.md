# Arquitectura del Core Backend: Conexión de Archivos, Módulos y Flujos de Comandos

Este documento describe la arquitectura modular, topología de archivos y flujos de ejecución del Core Backend de **Gamma Bot** (v2.0.0), integrando la interacción entre el Bot de Telegram, la API REST para Gamma Mobile, la sincronización Local-First y los servicios externos.

---

## 1. Topología Modular y Conexión de Archivos

El sistema está estructurado bajo una arquitectura por capas desacopladas (*Layered & Hexagonal Architecture*):

```mermaid
flowchart TD
    subgraph INGRESS["Capa de Entrada (Ingress / Presentation)"]
        WSGI["flask_app.py<br/>(WSGI / Endpoints / Webhooks)"]
        TG_BOT["com/bot.py<br/>(GAMMA Class / TeleBot)"]
        API_V1["api/v1/__init__.py<br/>(Blueprint Router Central)"]
        SEC["api/security.py<br/>(@require_api_key, Limiter)"]
        SCHEMAS["api/schemas.py<br/>(DTOs Pydantic v2)"]
    end

    subgraph ROUTES["Blueprints REST API (api/v1/)"]
        R_DASH["routes_dashboard.py<br/>(/summary, /bootstrap)"]
        R_ASIS["routes_asistencia.py<br/>(/marcar, /estado-hoy, /sync)"]
        R_PRE["routes_presupuesto.py<br/>(/fijos, /salario-base, /techos)"]
        R_PROY["routes_proyectos.py<br/>(/simular, /{id}/aprobar)"]
        R_OBL["routes_obligaciones.py<br/>(/vencimientos, /foco, /abonar)"]
        R_MOV["routes_movimientos.py<br/>(/movimientos, /ocr, /parse)"]
        R_REP["routes_reportes.py<br/>(/financiero/excel, /pdf)"]
        R_AVI["routes_avisos.py<br/>(/avisos, /ia/interpretar)"]
        R_CLI["routes_clima.py<br/>(/clima)"]
        R_CIE["routes_cierres.py<br/>(/cierres/ejecutar)"]
        R_DIS["routes_dispositivos.py<br/>(/dispositivos/registrar, /notificar)"]
    end

    subgraph HANDLERS["Controladores Telegram (com/handlers/)"]
        H_BASE["base.py<br/>(/start, /help, /menu)"]
        H_ASIS["asistencia.py<br/>(/marcar, /corte, /asistencia)"]
        H_FIN["finanzas.py<br/>(Registro gastos/ingresos, fotos)"]
        H_DEU["deudas.py<br/>(/deudas, /vencimientos, /foco)"]
        H_AVI["avisos.py<br/>(/aviso, /recordatorio)"]
        H_SOP["soporte.py<br/>(/ticket, consultas técnicas)"]
    end

    subgraph LOGIC["Lógica de Negocio y Dominio (logic/)"]
        L_HORAS["logic.py<br/>(AgenteAutonomoHoras)"]
        L_FIN["financiero.py<br/>(AgenteFinanciero, MLD, DTI)"]
        L_AI["ai_service.py<br/>(AIService, Gemini NLP/OCR)"]
        L_CRON["cron_jobs.py<br/>(Clima, Resumen, Cortes)"]
        L_PDF["pdf_service.py<br/>(Generación PDF ReportLab)"]
    end

    subgraph SERVICES["Servicios Transversales (services/)"]
        S_SYNC["sync_service.py<br/>(SyncService Local <-> Sheets)"]
        S_NOTIF["notification_dispatcher.py<br/>(Despachador Multicanal)"]
        S_CASH["cashflow_service.py<br/>(Proyecciones de Caja)"]
        S_EXCEL["excel_service.py<br/>(openpyxl Generator)"]
    end

    subgraph ADAPTERS["Adaptadores de Notificación (adapters/notifications/)"]
        A_TG["telegram_adapter.py<br/>(Telegram API)"]
        A_WA["whatsapp_adapter.py<br/>(Evolution API)"]
        A_PUSH["push_adapter.py<br/>(Firebase Cloud Messaging)"]
    end

    subgraph REPOSITORIES["Capa de Persistencia y Datos (repositories/)"]
        REPO_LOC["local_repository.py<br/>(LocalRepository SQLite: gamma_local.db)"]
        REPO_SHT["sheets_repository.py<br/>(SheetsRepository + Cache TTL + gspread)"]
    end

    subgraph STORAGE["Almacenamiento Físico"]
        DB_SQLITE[("gamma_local.db<br/>(SQLite Local)")]
        G_SHEETS[("Google Sheets API<br/>(Workbooks Drive)")]
    end

    %% Relaciones de Ingress
    WSGI --> TG_BOT
    WSGI --> API_V1
    API_V1 --> SEC
    API_V1 --> ROUTES
    ROUTES --> SCHEMAS

    %% Relaciones de Handlers
    TG_BOT --> HANDLERS

    %% Rutas y Handlers a Lógica
    R_ASIS --> L_HORAS
    H_ASIS --> L_HORAS
    R_DASH --> L_FIN
    R_PRE --> REPO_SHT
    R_PROY --> L_FIN
    R_OBL --> L_FIN
    H_FIN --> L_FIN
    H_FIN --> L_AI
    H_DEU --> L_FIN
    R_MOV --> L_AI
    R_MOV --> L_FIN
    R_REP --> S_EXCEL
    R_REP --> L_PDF
    R_AVI --> L_HORAS
    R_CLI --> L_CRON

    %% Lógica a Servicios y Repositorios
    L_HORAS --> REPO_LOC
    L_HORAS --> S_SYNC
    L_FIN --> REPO_SHT
    L_CRON --> S_NOTIF
    S_SYNC --> REPO_LOC
    S_SYNC --> REPO_SHT
    S_NOTIF --> A_TG
    S_NOTIF --> A_WA
    S_NOTIF --> A_PUSH

    %% Repositorios a Storage
    REPO_LOC --> DB_SQLITE
    REPO_SHT --> G_SHEETS
```

---

## 2. Diagrama de Clases del Core (`classDiagram`)

Representación de las principales clases del dominio, servicios y persistencia:

```mermaid
classDiagram
    class GAMMA {
        +TeleBot bot
        +str token
        +int admin_chat_id
        +iniciar_polling()
        +registrar_handlers()
    }

    class AgenteAutonomoHoras {
        +str spreadsheet_id
        +LocalRepository repo_local
        +ejecutar_marcado_para_bot(modo: str) MarcacionResult
        +ejecutar_corte_automatico() MarcacionResult
        +preparar_datos_reporte(hoja, descuento, saldo, iva) tuple
        +obtener_lista_avisos_calendar() list
    }

    class AgenteFinanciero {
        +str spreadsheet_id
        +SheetsRepository repo_sheets
        +obtener_balance() dict
        +registrar_transaccion(datos: dict) bool
        +simular_proyecto(monto, meses, concepto) dict
    }

    class LocalRepository {
        +str db_path
        +obtener_jornada_por_fecha(fecha: str) dict
        +insertar_o_actualizar_jornada(datos: dict) bool
        +registrar_evento_marcacion(tipo, hora, fecha) int
        +obtener_cola_sincronizacion_pendiente() list
        +marcar_sincronizado(id_evento: int) bool
    }

    class SheetsRepository {
        +gspread.Client client
        +_sheets_cache cache
        +get_todas_obligaciones() list
        +get_presupuesto_base() dict
        +actualizar_gasto_fijo(concepto, monto) bool
        +insertar_obligacion(datos: dict) bool
        +limpiar_cache() void
    }

    class SyncService {
        +str spreadsheet_id
        +LocalRepository repo_local
        +SheetsRepository repo_sheets
        +volcar_local_a_sheets(mes, anio, modulo) dict
        +volcar_sheets_a_local(mes, anio, modulo) dict
    }

    class NotificationDispatcher {
        +TelegramAdapter tg_adapter
        +WhatsAppAdapter wa_adapter
        +PushAdapter push_adapter
        +despachar_aviso(mensaje: str, canal: str, destinatario: str) bool
    }

    class MarcacionResult {
        +str tipo
        +str hora
        +str mensaje
        +bool auto_corte
        +dict datos_jornada
    }

    class EstadoJornadaHoyResponse {
        +str fecha
        +str estado
        +str hora_entrada
        +str hora_salida
        +int minutos_transcurridos
        +str tiempo_transcurrido_formato
        +bool puede_marcar_entrada
        +bool puede_marcar_salida
        +bool es_feriado_o_descanso
    }

    class BootstrapResponse {
        +dict resumen_financiero
        +EstadoJornadaHoyResponse estado_asistencia_hoy
        +dict clima
        +list proximos_avisos
        +list proximos_vencimientos
    }

    GAMMA ..> AgenteAutonomoHoras : orquesta
    GAMMA ..> AgenteFinanciero : orquesta
    AgenteAutonomoHoras --> LocalRepository : persiste local (<5ms)
    AgenteAutonomoHoras --> SyncService : write-through sync
    AgenteFinanciero --> SheetsRepository : lee y muta datos
    SyncService --> LocalRepository : lee pendientes
    SyncService --> SheetsRepository : impacta en filas
    AgenteAutonomoHoras ..> MarcacionResult : produce
    RoutesDashboard ..> BootstrapResponse : serializa
    RoutesAsistencia ..> EstadoJornadaHoyResponse : serializa
```

---

## 3. Flujos de Comandos y Procesos (Sequence Diagrams)

### 3.1 Flujo de Marcación Laboral (Local-First + Write-Through Reactivo)

Muestra cómo una marcación (desde Telegram `/marcar` o desde Mobile `POST /asistencia/marcar`) garantiza persistencia inmediata sin latencia y actualización a Google Sheets:

```mermaid
sequenceDiagram
    autonumber
    actor User as Usuario (Telegram / Mobile)
    participant Ingress as Handler / routes_asistencia.py
    participant Agent as AgenteAutonomoHoras (logic.py)
    participant SQLite as LocalRepository (gamma_local.db)
    participant Sync as SyncService (sync_service.py)
    participant Sheets as SheetsRepository (Google Sheets)

    User->>Ingress: Ejecutar marcado (/marcar o POST /asistencia/marcar)
    Ingress->>Agent: ejecutar_marcado_para_bot(modo="normal")
    
    rect rgb(235, 248, 255)
        note over Agent, SQLite: Persistencia Local Inmediata (Latencia < 5ms)
        Agent->>SQLite: obtener_jornada_por_fecha(hoy)
        SQLite-->>Agent: jornada_actual (None o con entrada)
        Agent->>SQLite: registrar_evento_marcacion() + insertar_o_actualizar_jornada()
        SQLite-->>Agent: OK (sincronizado_sheets=0)
    end

    rect rgb(245, 255, 245)
        note over Agent, Sheets: Write-Through no bloqueante a Google Sheets
        Agent->>Sync: volcar_local_a_sheets(modulo="laboral")
        Sync->>SQLite: obtener_eventos_no_sincronizados()
        SQLite-->>Sync: [evento_hoy]
        Sync->>Sheets: Escribir fila en hoja "Horas_Mes_Año"
        alt Éxito en Google Sheets
            Sheets-->>Sync: 200 OK
            Sync->>SQLite: marcar_sincronizado(id_evento)
        else Error de Red o Rate Limit (429)
            Sheets-->>Sync: Exception / Timeout
            note over Sync, SQLite: Queda pendiente en SQLite para siguiente ciclo
        end
    end

    Agent-->>Ingress: MarcacionResult(tipo="entrada"|"salida", hora="08:02", mensaje="...")
    Ingress-->>User: Respuesta 200 OK / Mensaje Telegram con teclado interactivo
```

---

### 3.2 Flujo de Registro Inteligente de Transacciones (NLP / OCR)

Muestra el pipeline cuando el usuario envía un texto `"Almuerzo 45000 efectivo"` o una foto de factura:

```mermaid
sequenceDiagram
    autonumber
    actor User as Usuario (Bot / Mobile)
    participant Ingress as Handler Finanzas / routes_movimientos.py
    participant AI as AIService (ai_service.py)
    participant Gemini as Google Gemini API
    participant Fin as AgenteFinanciero (financiero.py)
    participant Sheets as SheetsRepository (Google Sheets)
    participant Cache as _sheets_cache (Memoria RAM)

    alt Texto natural
        User->>Ingress: "Gasto 75000 farmacia factura 001-002"
        Ingress->>AI: procesar_movimiento_con_ia(texto)
        AI->>Gemini: Prompt estructurado de extracción contable
        Gemini-->>AI: JSON {concepto, total, tipo, categoria, factura}
        AI-->>Ingress: DTO Transacción
    else Foto de Factura
        User->>Ingress: Enviar Foto de Ticket
        Ingress->>AI: ocr_extraer_datos_factura(imagen_bytes)
        AI->>Gemini: Vision Prompt (Extracción RUC, Total, IVA)
        Gemini-->>AI: JSON {proveedor, total, iva_10, factura}
        AI-->>Ingress: DTO Transacción
    end

    Ingress->>Fin: registrar_movimiento(dto)
    Fin->>Sheets: append_row(hoja="Libro Diario", fila_datos)
    Sheets-->>Fin: OK
    Fin->>Cache: clear() (Invalidación inmediata de balance y dashboard)
    Fin-->>Ingress: Confirmación contable
    Ingress-->>User: "✅ Gasto registrado en Libro Diario: ₲ 75.000 | Saldo act: ₲ ..."
```

---

### 3.3 Flujo de Simulación y Aprobación de Proyectos de Inversión

Muestra la evaluación paramétrica de viabilidad de crédito y su pase a deuda activa:

```mermaid
sequenceDiagram
    autonumber
    actor Mobile as Gamma Mobile App
    participant Route as routes_proyectos.py
    participant Fin as AgenteFinanciero
    participant Sheets as SheetsRepository
    participant Cache as _sheets_cache

    Mobile->>Route: POST /proyectos/simular {concepto: "Notebook", monto: 6000000, meses: 12}
    Route->>Fin: simular_proyecto(monto, meses, concepto)
    Fin->>Sheets: get_presupuesto_base() & get_todas_obligaciones()
    Sheets-->>Fin: Ingresos fijos, gastos fijos, cuotas activas
    
    note over Fin: Cálculo MLD (Margen Libre Disponible)<br/>DTI = (Cuotas Totales / Ingreso Base) * 100<br/>Semáforo: VERDE (DTI<35%), AMARILLO (35-45%), ROJO (>45%)
    
    Fin->>Sheets: Registrar fila en "Obligaciones_Maestro" con Estado="Simulado"
    Sheets-->>Fin: OK (ID_Proyecto: "PRY-8A2F1B")
    Fin-->>Route: ProyectoSimularResponse (DTI: 24.6%, Semáforo: VERDE)
    Route-->>Mobile: HTTP 200 OK con Diagnóstico y Cuota Mensual

    opt Usuario decide aprobar el proyecto
        Mobile->>Route: POST /proyectos/PRY-8A2F1B/aprobar
        Route->>Sheets: actualizar_estado_obligacion("PRY-8A2F1B", "Activo")
        Sheets-->>Route: OK
        Route->>Cache: clear()
        Route-->>Mobile: HTTP 200 OK {status: "ok", estado: "Activo"}
    end
```

---

### 3.4 Flujo de Hidratación Atómica de la App Móvil (`GET /bootstrap`)

Muestra la agregación paralela y resiliente ante fallos de subsistemas externos:

```mermaid
sequenceDiagram
    autonumber
    actor Mobile as Gamma Mobile (Splash / Home)
    participant Boot as routes_dashboard.py (/bootstrap)
    participant Fin as AgenteFinanciero (Finanzas)
    participant Asis as routes_asistencia.py (Asistencia)
    participant Clima as cron_jobs.py (Open-Meteo)
    participant Avisos as routes_avisos.py (Avisos/Calendar)
    participant Deudas as financiero.py (Cronograma Deudas)

    Mobile->>Boot: GET /api/v1/bootstrap (Header: X-API-KEY)

    par Cómputo de Balance
        Boot->>Fin: calcular_resumen_financiero()
        Fin-->>Boot: {saldo_acumulado, margen_libre, iva, ...}
    and Consulta de Jornada Hoy
        Boot->>Asis: obtener_estado_jornada_hoy_dto()
        Asis-->>Boot: EstadoJornadaHoyResponse (TRABAJANDO, minutos: 185)
    and Pronóstico Meteorológico
        Boot->>Clima: obtener_datos_clima()
        alt Open-Meteo responde
            Clima-->>Boot: {temp: 24.5, alerta_paraguas: true}
        else Falla de conexión / Timeout
            Clima-->>Boot: Fallback seguro {condicion: "No disponible", temp: 0.0}
        end
    and Avisos Activos
        Boot->>Avisos: obtener_lista_avisos_activos()
        Avisos-->>Boot: [avisos_locales + calendar]
    and Vencimientos del Mes
        Boot->>Deudas: obtener_cronograma_vencimientos()
        Deudas-->>Boot: {vencimientos: [...]}
    end

    Boot->>Boot: Ensamblar DTO BootstrapResponse
    Boot-->>Mobile: HTTP 200 OK (Payload unificado Room Database)
```

---

## 4. Máquina de Estados del Reloj Laboral

```mermaid
stateDiagram-v2
    [*] --> LIBRE : Fin de semana o feriado
    [*] --> PENDING : Día laboral (sin marcación)

    PENDING --> TRABAJANDO : Marcación Entrada (manual o directa)
    TRABAJANDO --> TRABAJANDO : Marcación reiterada (retorna HTTP 200 info)
    TRABAJANDO --> COMPLETADO : Marcación Salida voluntaria
    TRABAJANDO --> COMPLETADO : Corte Automático por Cron (límite 9h)

    COMPLETADO --> [*] : Jornada concluida y sincronizada
    LIBRE --> [*]
```
