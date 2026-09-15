from prmonitor.validation import validate_briefing
def test_valid_briefing_passes_and_unknown_ref_holds():
 b={'tldr':'ok','insights':[{'refs':['a_1']}],'category_summary':[{'category_id':'c'}]}
 assert validate_briefing(b,article_ids={'a_1'},category_ids={'c'}).status=='PASS'
 b['insights'][0]['refs']=['missing']
 assert validate_briefing(b,article_ids={'a_1'},category_ids={'c'}).findings[0].code=='UNKNOWN_REF'

def test_send_guard_rejects_changed_briefing_or_policy():
 from prmonitor.validation import deliverable_is_current
 b={'tldr':'ok','insights':[{'refs':['a_1']}],'category_summary':[{'category_id':'c'}]}; p={}
 report=validate_briefing(b,article_ids={'a_1'},category_ids={'c'},policy=p)
 assert deliverable_is_current(report,briefing=b,policy=p,html_bytes=b'html')
 b['tldr']='changed'
 assert not deliverable_is_current(report,briefing=b,policy=p,html_bytes=b'html')

def test_validation_distinguishes_duplicate_and_coverage_gap():
 b={'tldr':'ok','insights':[{'refs':[]}], 'covered_refs':['a_1'],
    'category_summary':[{'category_id':'c'},{'category_id':'c'}]}
 r=validate_briefing(b,article_ids={'a_1'},category_ids={'c'})
 assert {f.code for f in r.findings} == {'DUPLICATE_CATEGORY','COVERAGE_GAP'}
