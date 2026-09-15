from pathlib import Path
from scripts.demo.verify_samples import audit, verify

def test_committed_samples_have_required_pages_and_source_links():
 result=verify(Path(__file__).parents[1]/'docs/demo')
 assert result['ok'] and result['source_links'] >= 6 and result['a11y'] == []

def test_audit_flags_missing_viewport_and_accessibility_defects():
 issues=audit('bad.html', '<html><head><title>t</title></head><body>'
   '<h1>a</h1><h3>skipped</h3><img src="x.png"><a href="#y"></a></body></html>')
 assert [problem.split(': ',1)[1] for problem in issues] == [
   'img without alt text', 'empty <a> (no accessible name)',
   'missing responsive viewport meta', 'missing html lang', 'heading level skipped']
