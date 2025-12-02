# Transfer Test Suite

This repository contains:

- `test_data/transfers_cases.csv`: CSV with functional and performance test cases.
- `tools/csv_to_xlsx.py`: small script to convert the CSV into an Excel `.xlsx` file.
- `tests/test_transfers.py`: pytest tests that perform non-invasive discovery and optional functional tests against the API at `http://localhost:8000`.
- `requirements.txt`: Python dependencies.

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
- The functional tests try to discover the transfer endpoint from the service OpenAPI (`/openapi.json` or `/docs`). If discovery fails, tests are skipped.
- Functional tests are disabled by default to avoid impacting real accounts. Enable them explicitly with `RUN_FUNCTIONAL=1`.
- Performance tests are described in the CSV under `performance` tag and are NOT implemented as automated load tests here. Use tools like `locust` or `k6` to run the performance scenarios safely against a test environment.
