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
