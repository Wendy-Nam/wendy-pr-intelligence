from __future__ import annotations
from ..render_safety import text, safe_url
def render_pr_html(records: list[dict], *, title: str='PR Monitoring') -> str:
 parts=[f'<h1>{text(title)}</h1>']
 for row in records:
  link=safe_url(row.get('source_url'))
  anchor=f'<a href="{link}">{text(row.get("title"))}</a>' if link else text(row.get('title'))
  parts.append(f'<article><h2>{anchor}</h2><p>{text(row.get("summary"))}</p></article>')
 return '\n'.join(parts)
