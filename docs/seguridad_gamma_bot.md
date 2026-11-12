# Plan de Remediación de Seguridad: `Gamma_bot`

**Repositorio:** `KEVIN11000/Gamma_bot`  
**Severidad:** 🔴 **ALTA (Prioridad Inmediata)**  
**Componente:** Módulo de Seguridad y Autenticación de API (`src/api/security.py`)  
**Clasificación CWE:** CWE-259 (Use of Hard-coded Password), CWE-1188 (Insecure Default Initialization)

---

## 1. Descripción de la Vulnerabilidad

En [`src/api/security.py`](file:///tmp/security_audit/repos/Gamma_bot/src/api/security.py#L33-L64), las funciones de validación de credenciales (`is_valid_api_key` y `is_valid_webhook_secret`) implementan un mecanismo de "fallback" hacia valores constantes en texto plano (`"dev-key"` y `"dev-webhook-secret"`) cuando las variables de entorno `X_API_KEY`, `GAMMA_MOBILE_API_KEY` o `WHATSAPP_WEBHOOK_SECRET` no se encuentran definidas.

### Código Vulnerable Actual:
```python
# src/api/security.py (Líneas 33-38)
expected_key = os.getenv("X_API_KEY") or os.getenv("GAMMA_MOBILE_API_KEY")
if not expected_key:
    if is_production():
        return False
    expected_key = "dev-key"  # ⚠️ VULNERABILIDAD
```
```python
# src/api/security.py (Líneas 50-59)
expected_secret = (
    os.getenv("WHATSAPP_WEBHOOK_SECRET")
    or os.getenv("WEBHOOK_SECRET")
    or os.getenv("X_API_KEY")
)
if not expected_secret:
    if is_production():
        return False
    expected_secret = "dev-webhook-secret"  # ⚠️ VULNERABILIDAD
```

---

## 2. Vector de Ataque e Impacto

1. **Dependencia frágil de `FLASK_ENV`:**  
   La función `is_production()` solo retorna `True` si `os.getenv("FLASK_ENV", "development").lower() == "production"`.  
   Si en PythonAnywhere o en el entorno de despliegue:
   * La variable `FLASK_ENV` no fue agregada explícitamente al WSGI o `.env`.
   * Tiene un error tipográfico (ej. `prod`, `Production ` con espacio).
   * Se ejecuta en un worker secundario sin las variables cargadas.
2. **Bypass total de la API:**  
   Cualquier atacante puede enviar peticiones con la cabecera:
   ```http
   POST /api/v1/... HTTP/1.1
   Host: kevin11000.pythonanywhere.com
   X-API-KEY: dev-key
   ```
   O para los webhooks de WhatsApp:
   ```http
   POST /api/v1/webhooks/whatsapp HTTP/1.1
   Host: kevin11000.pythonanywhere.com
   X-Webhook-Secret: dev-webhook-secret
   ```
   Y el servidor validará la firma con éxito, otorgando acceso a la lectura de registros, reportes financieros y ejecución de endpoints.

---

## 3. Solución Técnica (Parche de Código)

El principio de seguridad debe ser **Fail-Closed (Cierre por defecto)**: Si la clave no está explícitamente configurada en el entorno, la función **debe rechazar la petición siempre**, sin importar en qué entorno se encuentre el servidor.

### Parche a aplicar en `src/api/security.py`:

```diff
--- a/src/api/security.py
+++ b/src/api/security.py
@@ -30,13 +30,10 @@ def is_valid_api_key(provided_key: str | None) -> bool:
     if not provided_key:
         return False
-    from config import is_production
 
     expected_key = os.getenv("X_API_KEY") or os.getenv("GAMMA_MOBILE_API_KEY")
     if not expected_key:
-        if is_production():
-            return False
-        expected_key = "dev-key"
+        return False
 
     # Timing-attack resistant hash comparison
     h_provided = hashlib.sha256(provided_key.encode("utf-8")).digest()
@@ -47,16 +44,12 @@ def is_valid_webhook_secret(provided_secret: str | None) -> bool:
     if not provided_secret:
         return False
-    from config import is_production
 
     expected_secret = (
         os.getenv("WHATSAPP_WEBHOOK_SECRET")
         or os.getenv("WEBHOOK_SECRET")
         or os.getenv("X_API_KEY")
     )
     if not expected_secret:
-        if is_production():
-            return False
-        expected_secret = "dev-webhook-secret"
+        return False
 
     h_provided = hashlib.sha256(provided_secret.encode("utf-8")).digest()
```

> [!NOTE]
> Los tests unitarios no se romperán porque en la suite de pruebas (`tests/conftest.py`, `tests/test_sync_service.py`, etc.) ya se inyectan variables mediante `os.environ["X_API_KEY"] = "test-secret-key"`.

---

## 4. Verificación en el Servidor (PythonAnywhere)

En tu consola o panel de control de PythonAnywhere:

1. **Verificar el archivo de configuración WSGI:**  
   Asegúrate de que en el archivo `/var/www/kevin11000_pythonanywhere_com_wsgi.py` estén cargadas las variables antes de iniciar la app Flask:
   ```python
   import os
   os.environ["FLASK_ENV"] = "production"
   os.environ["X_API_KEY"] = "TU_CLAVE_ALEATORIA_SUPER_SEGURA_AQUI"
   os.environ["WHATSAPP_WEBHOOK_SECRET"] = "TU_WEBHOOK_SECRET_AQUI"
   ```
2. **Generar una API Key criptográficamente fuerte:**  
   En tu terminal puedes generar una clave segura de 32 bytes con Python:
   ```bash
   python3 -c "import secrets; print(secrets.token_urlsafe(32))"
   ```
3. **Prueba de intrusión defensiva:**  
   Verifica que una petición con `dev-key` sea rechazada con `401 Unauthorized`:
   ```bash
   curl -i -H "X-API-KEY: dev-key" https://kevin11000.pythonanywhere.com/api/v1/cierres/
   # Respuesta esperada: HTTP/1.1 401 UNAUTHORIZED
   ```
