import os
import csv
import json
import pytest
import requests

BASE = os.environ.get('API_BASE', 'http://localhost:8000')
CSV_PATH = os.path.join(os.path.dirname(__file__), '..', 'test_data', 'transfers_cases.csv')
RUN_FUNCTIONAL = os.environ.get('RUN_FUNCTIONAL', 'false').lower() in ('1', 'true', 'yes')


def load_csv():
    path = os.path.abspath(CSV_PATH)
    rows = []
    with open(path, newline='', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        for r in reader:
            rows.append(r)
    return rows


def get_openapi():
    for candidate in ['/openapi.json', '/openapi.yaml', '/docs', '/docs.json']:
        url = BASE.rstrip('/') + candidate
        try:
            r = requests.get(url, timeout=3)
            if r.status_code == 200:
                try:
                    return r.json()
                except Exception:
                    return {'raw': r.text}
        except requests.RequestException:
            continue
    pytest.skip('OpenAPI not reachable at {base}'.format(base=BASE))


def find_transfer_path(openapi):
    # naive search: find any path containing 'transfer' or operationId with 'transfer'
    paths = openapi.get('paths') if isinstance(openapi, dict) else None
    if not paths:
        return None, None
    for p, ops in paths.items():
        if 'transfer' in p.lower():
            for method in ops.keys():
                return p, method
        for method, op in ops.items():
            opid = op.get('operationId', '')
            if 'transfer' in opid.lower():
                return p, method
    return None, None


def test_openapi_accessible():
    try:
        openapi = get_openapi()
    except Exception:
        pytest.skip('OpenAPI not accessible')
    assert openapi is not None


def test_transfer_path_exists():
    openapi = get_openapi()
    path, method = find_transfer_path(openapi)
    assert path is not None, 'No transfer path found in OpenAPI'


@pytest.mark.parametrize('case', load_csv())
def test_functional_cases_discovery(case):
    # Non-invasive discovery assertions
    if case.get('Tag', '').strip().lower() not in ('functional', 'concurrency'):
        pytest.skip('Skipping non-functional/performance case')
    openapi = get_openapi()
    path, method = find_transfer_path(openapi)
    if not path:
        pytest.skip('No transfer endpoint discovered; skip functional test')
    # Only run real functional tests when explicitly enabled
    if not RUN_FUNCTIONAL:
        pytest.skip('Functional tests disabled. Set RUN_FUNCTIONAL=1 to enable.')

    url = BASE.rstrip('/') + path
    # build a simple payload from Datos Prueba field (best-effort)
    datos = case.get('Datos Prueba', '')
    body = {}
    for pair in datos.split(';'):
        if '=' in pair:
            k, v = pair.split('=', 1)
            k = k.strip()
            v = v.strip()
            if k == 'monto':
                try:
                    body['amount'] = float(v)
                except Exception:
                    body['amount'] = v
            elif k == 'origen':
                body['from_account'] = v
            elif k == 'destino':
                body['to_account'] = v
            elif k == 'timestamp':
                body['timestamp'] = v
    otp = case.get('OTP', '').strip()
    if otp:
        body['otp'] = otp

    expected = case.get('ExpectedHTTP', '').strip()
    try:
        expected_code = int(expected)
    except Exception:
        expected_code = None

    resp = requests.post(url, json=body, timeout=10)
    if expected_code:
        assert resp.status_code == expected_code, f"Case {case.get('ID')} expected {expected_code} got {resp.status_code} - {resp.text}"
    else:
        assert resp.status_code < 500, f"Unexpected server error: {resp.status_code}"
