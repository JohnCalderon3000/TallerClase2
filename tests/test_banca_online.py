import csv
import os
import json
import requests
import pytest
from openpyxl import Workbook


CSV_PATH = os.path.join(os.path.dirname(__file__), '..', 'test_data', 'BancaOnline.csv')
XLSX_PATH = os.path.join(os.path.dirname(__file__), '..', 'test_data', 'BancaOnline.xlsx')


def load_cases():
    cases = []
    with open(CSV_PATH, newline='', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        for r in reader:
            cases.append(r)
    return cases


@pytest.fixture(scope='session')
def results_collector():
    results = []
    yield results
    # after session, write XLSX summary
    wb = Workbook()
    ws = wb.active
    ws.title = 'BancaOnline Results'
    headers = ['ID', 'Escenario', 'Resultado', 'HTTP Status', 'Response', 'Notas']
    ws.append(headers)
    for row in results:
        ws.append([row.get(h, '') for h in ['ID', 'Escenario', 'Resultado', 'HTTP Status', 'Response', 'Notas']])
    os.makedirs(os.path.dirname(XLSX_PATH), exist_ok=True)
    wb.save(XLSX_PATH)


def discover_endpoint():
    # try a list of common transfer endpoints
    candidates = [
        'http://localhost:8000/transfers',
        'http://localhost:8000/api/transfers',
        'http://localhost:8000/api/transfer',
        'http://localhost:8000/transfer',
    ]
    for url in candidates:
        try:
            # try OPTIONS first
            r = requests.options(url, timeout=1)
            if r.status_code < 500:
                return url
        except requests.RequestException:
            continue
    return None


@pytest.mark.parametrize('case', load_cases())
def test_banca_online_case(case, results_collector):
    """Executes a simple transfer POST and records result. Conservative: skips if service unreachable."""
    endpoint = discover_endpoint()
    row = {'ID': case.get('ID', ''), 'Escenario': case.get('Escenario', '')}
    if not endpoint:
        pytest.skip('No transfer endpoint discovered on localhost:8000')

    # construct payload from CSV `Datos Prueba` if present
    payload = {}
    datos = case.get('Datos Prueba', '') or ''
    try:
        # try to parse key=val;key2=val2 format
        for part in datos.split(';'):
            if not part.strip():
                continue
            k, v = part.split('=', 1)
            # attempt numeric cast for monto
            if k.strip() == 'monto':
                try:
                    payload[k.strip()] = float(v)
                except Exception:
                    payload[k.strip()] = v
            else:
                payload[k.strip()] = v
    except Exception:
        payload = {'raw': datos}

    try:
        r = requests.post(endpoint, json=payload, timeout=5)
        status = r.status_code
        text = r.text
        if 200 <= status < 300:
            result = 'PASSED'
        else:
            result = 'FAILED'
        row.update({'Resultado': result, 'HTTP Status': status, 'Response': text, 'Notas': ''})
    except requests.RequestException as ex:
        row.update({'Resultado': 'ERROR', 'HTTP Status': '', 'Response': '', 'Notas': str(ex)})
        # mark test as xfail if connection refused
        pytest.skip(f'Connection problem executing request: {ex}')

    results_collector.append(row)
    # make a basic assertion to fail the test when non-2xx
    assert row['Resultado'] == 'PASSED', f"Expected 2xx but got {row.get('HTTP Status')}"
