from prmonitor.services.self_workflow import prepare_self_report

def test_self_workflow_is_rules_first_and_scope_explicit():
 report=prepare_self_report([{'id':'a_1','title':'Contoso launches service','summary':'new service','source_name':'x','url':'https://x'}], company_aliases=['contoso'])
 assert report.counts['total']==1 and report.counts['llm_enabled'] is False

def test_self_brief_count_uses_records_not_physical_lines(tmp_path):
 """F14: 맥락 셀 안의 개행이 PR 건수를 부풀리면 안 된다."""
 from prmonitor.steps.self_brief import _self_report
 csv_path=tmp_path/'pr.csv'
 csv_path.write_text('날짜,매체,기자,제목,언급유형,톤,주가관련,맥락,URL\n'
                     '2026-09-15,매체,,제목,직접,긍정,,"두 줄\n맥락",https://x\n', encoding='utf-8-sig')
 report=_self_report(csv_path)
 assert report.counts['total']==1 and report.counts['tones']['positive']==0

def test_self_brief_count_is_zero_without_csv(tmp_path):
 assert _missing(tmp_path).counts['total']==0

def _missing(tmp_path):
 from prmonitor.steps.self_brief import _self_report
 return _self_report(tmp_path/'nope.csv')
