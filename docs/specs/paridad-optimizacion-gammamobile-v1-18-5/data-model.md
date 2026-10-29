# Data Model & Contracts: Paridad con Gamma Mobile

## 1. Esquema `MovimientoCreate` ([src/api/schemas.py](file:///e:/PG/vcp-s/Gamma_bot/src/api/schemas.py))

```python
class MovimientoCreate(BaseModel):
    monto: int = Field(..., gt=0, description="Monto en guaraníes")
    concepto: str = Field(..., min_length=1, max_length=120)
    categoria: str = Field(..., min_length=1, max_length=50)
    movimiento: TipoMovimiento = Field(
        default=TipoMovimiento.GASTO,
        alias="tipo",
        description="Tipo de movimiento: Gasto o Ingreso",
    )
    fecha: Optional[str] = None
    client_id: Optional[str] = Field(None, alias="clientId")

    model_config = ConfigDict(populate_by_name=True)
```

---

## 2. Contrato `GET /api/v1/obligaciones/foco` ([src/api/blueprint.py](file:///e:/PG/vcp-s/Gamma_bot/src/api/blueprint.py))

Respuesta HTTP 200:
```json
{
  "criterio": "Monto menor (Bola de Nieve)",
  "deuda_foco": {
    "acreedor": "Banco X",
    "saldo": 1500000,
    "cuota": 250000,
    "moneda": "PYG"
  },
  "acreedor": "Banco X",
  "saldo": 1500000,
  "cuota": 250000,
  "moneda": "PYG"
}
```

---

## 3. Contrato `POST /api/v1/asistencia/marcar` (Respuesta Informativa)

Respuesta HTTP 200 (Caso informativo):
```json
{
  "status": "ok",
  "tipo": "info",
  "mensaje": "ℹ️ Ya registraste tu entrada hoy a las 08:30",
  "confirmado_en_planilla": true
}
```

---

## 4. Contrato `GET /api/v1/asistencia/cierres`

Respuesta HTTP 200:
```json
{
  "status": "ok",
  "cierres": [
    {
      "periodo": "Septiembre 2026",
      "fecha_cierre": "2026-09-30",
      "total_horas": 160.0,
      "salario_neto": 4500000,
      "pdf_disponible": true,
      "url_pdf": "/api/v1/reportes/cierre_septiembre_2026.pdf"
    }
  ]
}
```
