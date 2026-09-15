"""Offline checks for the committed public sample artifacts."""
from __future__ import annotations
import hashlib, re
from html.parser import HTMLParser
from pathlib import Path

_TEXTUAL = ('title','h1','h2','h3','h4','h5','h6')

class _Audit(HTMLParser):
    """Structural viewport/accessibility scan — no browser, no network."""
    def __init__(self) -> None:
        super().__init__()
        self.problems: list[str] = []; self.headings: list[int] = []
        self.lang = ''; self.viewport = False; self._open: list[list[str]] = []

    def handle_starttag(self, tag, attrs):
        a = dict(attrs)
        if tag == 'html':
            self.lang = (a.get('lang') or '').strip()
        elif tag == 'meta' and (a.get('name') or '').lower() == 'viewport':
            self.viewport = 'width=device-width' in (a.get('content') or '')
        elif tag == 'img' and not (a.get('alt') or '').strip():
            self.problems.append('img without alt text')
        elif tag == 'a' and 'href' in a:
            self._open.append(['a', a.get('aria-label') or ''])
        elif tag in _TEXTUAL:
            if tag != 'title':
                self.headings.append(int(tag[1]))
            self._open.append([tag, ''])

    def handle_data(self, data):
        for item in self._open:
            item[1] += data

    def handle_endtag(self, tag):
        for i in range(len(self._open) - 1, -1, -1):
            if self._open[i][0] == tag:
                name, text = self._open.pop(i)
                if not text.strip():
                    self.problems.append(f'empty <{name}> (no accessible name)')
                break

def audit(name: str, markup: str) -> list[str]:
    parser = _Audit(); parser.feed(markup)
    issues = [f'{name}: {problem}' for problem in dict.fromkeys(parser.problems)]
    if not parser.viewport:
        issues.append(f'{name}: missing responsive viewport meta')
    if not parser.lang:
        issues.append(f'{name}: missing html lang')
    if parser.headings.count(1) != 1:
        issues.append(f'{name}: expected exactly one h1')
    if any(nxt - cur > 1 for cur, nxt in zip(parser.headings, parser.headings[1:])):
        issues.append(f'{name}: heading level skipped')
    return issues

def verify(root: Path) -> dict:
    required = ('index.html','market-brief.html','self-brief.html','sources.html')
    missing=[name for name in required if not (root/name).is_file()]
    html={name:(root/name).read_text(encoding='utf-8') for name in required if name not in missing}
    links=sum(len(re.findall(r'href=["\']sources\.html#[^"\']+', value)) for value in html.values())
    a11y=[issue for name, value in html.items() for issue in audit(name, value)]
    return {'ok': not missing and not a11y and links >= 6, 'missing': missing, 'source_links': links, 'a11y': a11y,
            'hashes': {name: hashlib.sha256((root/name).read_bytes()).hexdigest() for name in required if name not in missing}}

if __name__ == '__main__':
 import json, sys
 result=verify(Path(sys.argv[1]) if len(sys.argv)>1 else Path(__file__).resolve().parents[2]/'docs/demo')
 print(json.dumps(result, ensure_ascii=False, indent=2)); raise SystemExit(0 if result['ok'] else 1)
