"""
Safe, opt-in performance runner (minimal). Reads CSV with performance cases and either
- prints the execution plan (default), or
- executes a lightweight run when you set env var RUN_PERF=1 and EXECUTE=1.

Usage examples:
# Dry-run (safe)
python tools\run_performance.py test_data\performance_cases.csv

# Execute (use a test environment only!)
$env:RUN_PERF = '1'
$env:EXECUTE = '1'
python tools\run_performance.py test_data\performance_cases.csv --concurrency 50 --requests 100

Notes:
- This script is intentionally conservative. It will NOT run unless both RUN_PERF and EXECUTE env vars are set to '1'.
- Use a dedicated test environment; do NOT run against production.
"""

import csv
import os
import sys
import time
import argparse
import threading
import requests
from queue import Queue


def parse_args():
    p = argparse.ArgumentParser()
    p.add_argument('csv', help='CSV file with performance cases')
    p.add_argument('--concurrency', type=int, default=10)
    p.add_argument('--requests', type=int, default=100)
    return p.parse_args()


def load_cases(path):
    rows = []
    with open(path, newline='', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        for r in reader:
            rows.append(r)
    return rows


def worker(q, stats, base_url):
    while True:
        item = q.get()
        if item is None:
            break
        url, payload = item
        try:
            t0 = time.time()
            r = requests.post(url, json=payload, timeout=10)
            dt = time.time() - t0
            stats['total'] += 1
            stats['latencies'].append(dt)
            if r.status_code >= 500:
                stats['errors'] += 1
        except Exception:
            stats['errors'] += 1
        finally:
            q.task_done()


def build_payload_from_datos(datos):
    body = {}
    for pair in (datos or '').split(';'):
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
    return body


def run_case(case, concurrency, total_requests, base_url):
    datos = case.get('Datos Prueba', '') or case.get('Datos Prueba', '')
    payload = build_payload_from_datos(datos)
    # Default transfer path (discovery not implemented here) -> user must set TRANSFER_PATH env var
    transfer_path = os.environ.get('TRANSFER_PATH', '/transfers')
    url = base_url.rstrip('/') + transfer_path

    q = Queue()
    stats = {'total': 0, 'errors': 0, 'latencies': []}
    threads = []
    for _ in range(concurrency):
        t = threading.Thread(target=worker, args=(q, stats, base_url), daemon=True)
        t.start()
        threads.append(t)

    for i in range(total_requests):
        q.put((url, payload))
    q.join()

    for _ in threads:
        q.put(None)
    for t in threads:
        t.join(timeout=1)

    latencies = stats['latencies']
    p95 = sorted(latencies)[int(len(latencies) * 0.95) - 1] if latencies else None
    return {'total': stats['total'], 'errors': stats['errors'], 'p95': p95}


def main():
    args = parse_args()
    cases = load_cases(args.csv)
    base = os.environ.get('API_BASE', 'http://localhost:8000')

    run_perf = os.environ.get('RUN_PERF', '0') == '1'
    execute = os.environ.get('EXECUTE', '0') == '1'

    if not run_perf:
        print('RUN_PERF not enabled. Printing plan for performance cases:')
        for c in cases:
            print(f"ID {c.get('ID')}: {c.get('Escenario')} -> {c.get('Pasos')}")
        return

    print('RUN_PERF enabled. Execution requires EXECUTE=1 to run against target.')
    for c in cases:
        print('\n---')
        print(f"Case {c.get('ID')}: {c.get('Escenario')}")
        print(f"Plan: {c.get('Pasos')}")
        if not execute:
            print('EXECUTE not enabled. Skipping actual execution.')
            continue
        print('Executing (this will send HTTP POST requests) — ensure test environment')
        res = run_case(c, concurrency=args.concurrency, total_requests=args.requests, base_url=base)
        print(f"Result: total={res['total']} errors={res['errors']} p95={res['p95']}")


if __name__ == '__main__':
    main()
