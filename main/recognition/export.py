"""Write recognized tables to an Excel workbook (one sheet per table)."""

import io
import re

from openpyxl import Workbook
from openpyxl.styles import Font
from openpyxl.utils import get_column_letter

_NUMBER = re.compile(r"^-?\d+(?:[  ]\d{3})*(?:[.,]\d+)?$")


def _to_cell_value(text):
    """Turn '1 234,5' / '59.7' into numbers so Excel can sum them; keep everything else as text."""
    t = text.strip()
    if _NUMBER.match(t):
        try:
            return float(t.replace(" ", "").replace(" ", "").replace(",", "."))
        except ValueError:
            pass
    return t


def tables_to_xlsx(tables):
    """tables: [{"page": int, "rows": [[str]]}] -> bytes of an .xlsx file."""
    wb = Workbook()
    wb.remove(wb.active)
    for n, table in enumerate(tables, start=1):
        ws = wb.create_sheet(title=f"Стр{table['page']}_Табл{n}"[:31])
        for row in table["rows"]:
            ws.append([_to_cell_value(cell) for cell in row])
        for cell in ws[1] if ws.max_row else []:
            cell.font = Font(bold=True)
        for col in range(1, ws.max_column + 1):
            longest = max((len(str(c.value or "")) for c in ws[get_column_letter(col)]), default=8)
            ws.column_dimensions[get_column_letter(col)].width = min(max(10, longest + 2), 60)
    buf = io.BytesIO()
    wb.save(buf)
    return buf.getvalue()
