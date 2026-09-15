from prmonitor.services.jobs import plan_jobs
from prmonitor.services.runs import execute_headless
def test_headless_respects_call_budget_before_invoking():
 plan=plan_jobs('r',mode='headless',strategy='split',expected_categories=['a','b'],max_calls=3)
 calls=[]
 def invoke(req): calls.append(req.job_id); return {'run_id':'r','job_id':req.job_id,'request_hash':req.request_hash,'result':{}}
 result=execute_headless(plan,invoke,max_calls=1,deadline_seconds=10)
 assert result.exhausted and result.calls==1 and len(calls)==1
