import pytest
from prmonitor.render import render_briefing
from prmonitor.validation import validate_briefing
def test_held_preview_watermarks_and_ready_render_rejects(tmp_path):
 b={'tldr':'','insights':[],'category_summary':[]}; report=validate_briefing(b,article_ids=set(),category_ids=set())
 with pytest.raises(ValueError): render_briefing(b,report,policy={},output=tmp_path/'x.html')
 out=render_briefing(b,report,policy={},output=tmp_path/'x.html',allow_held=True)
 assert 'REVIEW NEEDED' in out.read_text()
