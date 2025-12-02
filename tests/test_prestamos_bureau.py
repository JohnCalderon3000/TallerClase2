import os
import csv
import pytest
import requests
import json
import datetime
import subprocess

BASE = os.environ.get('API_BASE', 'http://localhost:8000')
CSV_PATH = os.path.join(os.path.dirname(__file__), '..', 'test_data', 'PrestamosBancarios.csv')
RESULTS_CSV = os.path.join(os.path.dirname(__file__), '..', 'reports', 'prestamos_bureau_results.csv')
RUN_FUNCTIONAL = os.environ.get('RUN_FUNCTIONAL', 'false').lower() in ('1', 'true', 'yes')


def load_csv():
    rows = []
    with open(CSV_PATH, newline='', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        for r in reader:
            rows.append(r)
    return rows


def get_openapi_local():
    # prefer local saved spec if available
    local = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'openapi_local.json'))
    if os.path.exists(local):
        with open(local, 'r', encoding='utf-8') as f:
            try:
                return json.load(f)
            except Exception:
                return None
    return None


def find_bureau_path(openapi):
    if not openapi:
        return None, None
    paths = openapi.get('paths', {})
    for p, ops in paths.items():
        if '/bureau' in p and 'consultar' in p:
            for method in ops.keys():
                return p, method
    return None, None


def test_openapi_has_bureau():
    openapi = get_openapi_local()
    path, method = find_bureau_path(openapi)
    assert path is not None, 'OpenAPI local spec does not contain /bureau/consultar path'


@pytest.fixture(scope='session')
def result_report():
    """Collects test results during the session and writes CSV/XLSX at the end."""
    results = []
    yield results

    # Ensure reports directory exists
    reports_dir = os.path.dirname(RESULTS_CSV)
    os.makedirs(reports_dir, exist_ok=True)

    # Write CSV report
    fieldnames = [
        'ID', 'Escenario', 'cliente_id', 'expected', 'status_code', 'outcome', 'error_message', 'timestamp'
    ]
    try:
        with open(RESULTS_CSV, 'w', newline='', encoding='utf-8') as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()
            for r in results:
                writer.writerow({k: r.get(k, '') for k in fieldnames})
    except Exception as e:
        print('Failed to write results CSV:', e)

    # Attempt to convert to XLSX using existing tool
    try:
        subprocess.run(['py', '-3', 'tools/csv_to_xlsx.py', RESULTS_CSV, RESULTS_CSV.replace('.csv', '.xlsx')], check=True)
    except Exception:
        pass


@pytest.mark.parametrize('case', load_csv())
def test_bureau_cases_discovery(case, result_report):
    # Only run light discovery checks unless RUN_FUNCTIONAL enabled
    openapi = get_openapi_local()
    path, method = find_bureau_path(openapi)
    if not path:
        pytest.skip('No bureau path discovered in local OpenAPI; skip functional checks')

    # If functional tests not enabled, skip execution to avoid impacting production
    if not RUN_FUNCTIONAL:
        pytest.skip('Functional tests disabled. Set RUN_FUNCTIONAL=1 to enable.')

    url = BASE.rstrip('/') + path
    # Build payload best-effort from Datos de Prueba or cliente_id
    body = {}
    dp = case.get('Datos de Prueba', '') or case.get('Datos de Prueba', '')
    for item in (dp or '').split(';'):
        if '=' in item:
            k, v = item.split('=', 1)
            k = k.strip()
            v = v.strip()
            if k == 'cliente_id':
                try:
                    body['cliente_id'] = int(v)
                except Exception:
                    body['cliente_id'] = v
            else:
                body[k] = v

    start = datetime.datetime.utcnow().isoformat()
    outcome = 'UNKNOWN'
    status_code = ''
    error_msg = ''
    try:
        resp = requests.post(url, json=body, timeout=10)
        status_code = resp.status_code

        # Evaluate expected outcomes heuristically based on 'Resultado Esperado' column
        expected = (case.get('Resultado Esperado', '') or '').lower()
        passed = False
        if 'http 200' in expected or '200' in expected:
            passed = (resp.status_code == 200)
        elif '422' in expected or 'validation' in expected:
            passed = (resp.status_code in (400, 422))
        elif '403' in expected:
            passed = (resp.status_code == 403)
        elif '503' in expected or '500' in expected:
            passed = (resp.status_code >= 500)
        else:
            passed = (resp.status_code < 500)

        outcome = 'PASS' if passed else 'FAIL'
        if not passed:
            error_msg = f"Unexpected status {resp.status_code}: {resp.text[:200]}"
    except Exception as e:
        outcome = 'ERROR'
        error_msg = str(e)

    # Record result
    cliente = ''
    dp = case.get('Datos de Prueba', '') or case.get('Datos de Prueba', '')
    for item in (dp or '').split(';'):
        if '=' in item:
            k, v = item.split('=', 1)
            if k.strip() == 'cliente_id':
                cliente = v.strip()

    result_report.append({
        'ID': case.get('ID'),
        'Escenario': case.get('Escenario'),
        'cliente_id': cliente,
        'expected': case.get('Resultado Esperado'),
        'status_code': status_code,
        'outcome': outcome,
        'error_message': error_msg,
        'timestamp': start,
    })

    # Fail the test explicitly if outcome is FAIL or ERROR
    if outcome == 'FAIL':
        pytest.fail(error_msg or f"Case {case.get('ID')} failed: status {status_code}")
    if outcome == 'ERROR':
        pytest.fail(error_msg)
import os
import csv
import pytest
import requests
import json

BASE = os.environ.get('API_BASE', 'http://localhost:8000')
CSV_PATH = os.path.join(os.path.dirname(__file__), '..', 'test_data', 'PrestamosBancarios.csv')
RUN_FUNCTIONAL = os.environ.get('RUN_FUNCTIONAL', 'false').lower() in ('1', 'true', 'yes')


def load_csv():
    rows = []
    with open(CSV_PATH, newline='', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        for r in reader:
            rows.append(r)
    return rows


def get_openapi_local():
    # prefer local saved spec if available
    local = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'openapi_local.json'))
    if os.path.exists(local):
        with open(local, 'r', encoding='utf-8') as f:
            try:
                return json.load(f)
            except Exception:
                return None
    return None


def find_bureau_path(openapi):
    if not openapi:
        return None, None
    paths = openapi.get('paths', {})
    for p, ops in paths.items():
        if '/bureau' in p and 'consultar' in p:
            for method in ops.keys():
                return p, method
    return None, None


def test_openapi_has_bureau():
    openapi = get_openapi_local()
    path, method = find_bureau_path(openapi)
    assert path is not None, 'OpenAPI local spec does not contain /bureau/consultar path'


@pytest.mark.parametrize('case', load_csv())
def test_bureau_cases_discovery(case):
    # Only run light discovery checks unless RUN_FUNCTIONAL enabled
    openapi = get_openapi_local()
    path, method = find_bureau_path(openapi)
    if not path:
        pytest.skip('No bureau path discovered in local OpenAPI; skip functional checks')

    # If functional tests not enabled, skip execution to avoid hitting production
    if not RUN_FUNCTIONAL:
        pytest.skip('Functional tests disabled. Set RUN_FUNCTIONAL=1 to enable.')

    url = BASE.rstrip('/') + path
    # Build payload best-effort from Datos de Prueba or cliente_id
    body = {}
    dp = case.get('Datos de Prueba', '') or case.get('Datos de Prueba', '')
    for item in (dp or '').split(';'):
        if '=' in item:
            k, v = item.split('=', 1)
            k = k.strip()
            v = v.strip()
            if k == 'cliente_id':
                try:
                    body['cliente_id'] = int(v)
                except Exception:
                    body['cliente_id'] = v
            else:
                body[k] = v

    # Attempt request
    resp = requests.post(url, json=body, timeout=10)

    # Evaluate expected outcomes heuristically based on 'Resultado Esperado' column
    expected = case.get('Resultado Esperado', '').lower()
    if 'http 200' in expected or '200' in expected:
        assert resp.status_code == 200, f"Case {case.get('ID')} expected 200 got {resp.status_code} - {resp.text}"
    elif '422' in expected or 'validation' in expected:
        assert resp.status_code in (400, 422), f"Case {case.get('ID')} expected validation error got {resp.status_code}"
    elif '403' in expected:
        assert resp.status_code == 403
    elif '503' in expected or '500' in expected:
        assert resp.status_code >= 500
    else:
        # default: ensure no 500
        assert resp.status_code < 500, f"Unexpected server error: {resp.status_code}"
