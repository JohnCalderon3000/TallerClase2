# Transfer Test Suite

This repository contains:


Quick setup:

1. Create a virtualenv and install deps:

```powershell
python -m venv .venv; .\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

2. Generate Excel from CSV (optional):

```powershell
python tools\csv_to_xlsx.py test_data\transfers_cases.csv test_data\transfers_cases.xlsx
```

3. Run discovery tests (non-destructive):

```powershell
pytest -q
```

4. To run functional tests that will call the transfer endpoint, set the environment variable `RUN_FUNCTIONAL=1`.

```powershell
$env:RUN_FUNCTIONAL = '1'
pytest tests\test_transfers.py -q
```

Notes:

**Escenarios de Transacción**
- **Path feliz:** transferencia exitosa dentro de límites diarios y sin requerir OTP.
- **Exceder límite diario:** intentos que superan $50.000 diarios y deben ser rechazados.
- **Exceder límite mensual:** intentos que superan $5.000.000 mensuales.
- **Saldo insuficiente:** la cuenta origen no tiene fondos suficientes.
- **OTP inválido/ausente:** montos > $1.000.000 requieren OTP; probar OTP inválido y OTP faltante.
- **Mantenimiento:** intentos entre 01:00–03:00 deben devolver mantenimiento o encolamiento según política.
- **Cuenta destino inválida:** número de cuenta inexistente o mal formado.
- **Edge cases:** monto mínimo ($0.01), monto negativo, decimales > 2 posiciones.
- **Concurrencia:** dos transferencias simultáneas que compiten por el mismo saldo.
- **Validaciones de cuenta:** origen bloqueada, origen == destino.

Los casos de prueba detallados están en `test_data/transfers_cases.csv` y en `test_data/transfers_cases2.csv`.

**Reporte CSV de Transacciones**
- Se añadió `reports/transfer_test_report.csv` con un resumen de los 15 casos funcionales y de concurrencia para revisión rápida.

Si quieres que además convierta el reporte a Excel o que lo integre con una plantilla de pruebas (TestRail/JIRA), dime el formato objetivo y lo preparo.
