import csv
from openpyxl import Workbook
import sys

"""
Usage: python tools/csv_to_xlsx.py test_data/transfers_cases.csv test_data/transfers_cases.xlsx
"""

def csv_to_xlsx(csv_path, xlsx_path):
    wb = Workbook()
    ws = wb.active
    with open(csv_path, newline='', encoding='utf-8') as f:
        reader = csv.reader(f)
        for r_idx, row in enumerate(reader, start=1):
            for c_idx, cell in enumerate(row, start=1):
                ws.cell(row=r_idx, column=c_idx, value=cell)
    wb.save(xlsx_path)


if __name__ == '__main__':
    if len(sys.argv) < 3:
        print('Usage: python csv_to_xlsx.py input.csv output.xlsx')
        sys.exit(1)
    csv_to_xlsx(sys.argv[1], sys.argv[2])
