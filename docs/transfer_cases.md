# Casos de Transferencia

El archivo `test_data/transfer_transaction_cases.csv` contiene 15 casos de prueba específicos para transferencias.

Listado resumido:

- Path feliz: transferencia exitosa dentro de límites diarios y sin requerir OTP.
- Exceder límite diario: intentos que superan $50.000 diarios y deben ser rechazados.
- Exceder límite mensual: intentos que superan $5.000.000 mensuales.
- Saldo insuficiente: la cuenta origen no tiene fondos suficientes.
- OTP inválido/ausente: montos > $1.000.000 requieren OTP; probar OTP inválido y OTP faltante.
- Mantenimiento: intentos entre 01:00–03:00 deben devolver mantenimiento o encolamiento según política.
- Cuenta destino inválida: número de cuenta inexistente o mal formado.
- Edge cases: monto mínimo ($0.01), monto negativo, decimales > 2 posiciones.
- Concurrencia: dos transferencias simultáneas que compiten por el mismo saldo.
- Validaciones de cuenta: origen bloqueada, origen == destino.

Uso rápido:

```powershell
python tools\csv_to_xlsx.py test_data\transfer_transaction_cases.csv test_data\transfer_transaction_cases.xlsx
```

Puedes copiar este contenido al `README.md` si prefieres mantener un solo documento principal.
