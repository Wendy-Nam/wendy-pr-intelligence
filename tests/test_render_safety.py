from prmonitor.render_safety import safe_url, text
def test_text_escaped_and_javascript_rejected():
 assert text('<script>alert(1)</script>') == '&lt;script&gt;alert(1)&lt;/script&gt;'
 assert safe_url('javascript:alert(1)') is None
 assert safe_url('https://example.com/a?x=1')
