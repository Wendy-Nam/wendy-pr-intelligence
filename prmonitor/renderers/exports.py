from __future__ import annotations
import csv, io
def _cell(value):
 value='' if value is None else str(value)
 return "'"+value if value[:1] in {'=','+','-','@'} else value
def export_csv(records: list[dict]) -> str:
 out=io.StringIO(newline=''); writer=csv.DictWriter(out,fieldnames=['id','title','summary','tone','source_name','source_url']); writer.writeheader(); writer.writerows([{k:_cell(v) for k,v in row.items()} for row in records]); return out.getvalue()

def export_xlsx(records: list[dict], path):
 """Write the same record view as CSV using the optional bundled openpyxl dep."""
 from openpyxl import Workbook
 fields=['id','title','summary','tone','source_name','source_url']; book=Workbook(); sheet=book.active; sheet.append(fields)
 for row in records: sheet.append([_cell(row.get(key)) for key in fields])
 book.save(path); return path
