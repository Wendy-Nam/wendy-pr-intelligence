import pytest
from prmonitor.services.jobs import plan_jobs, validate_result_envelope

def test_host_prepare_returns_jobs_without_execution():
 plan=plan_jobs('r',mode='host',pipeline='market')
 assert len(plan.jobs)==1 and plan.next_actions and plan.jobs[0].kind=='market_brief'
def test_split_budget_fails_before_execution():
 with pytest.raises(ValueError): plan_jobs('r',mode='headless',strategy='split',expected_categories=['a','b','c'],max_calls=2)
def test_result_envelope_is_scoped_to_run_and_request():
 req=plan_jobs('r',mode='host').jobs[0]
 with pytest.raises(ValueError,match='RESULT_ID_MISMATCH'):
  validate_result_envelope({'run_id':'other','job_id':req.job_id,'request_hash':req.request_hash,'result':{}},req)

def test_ingest_result_returns_scoped_immutable_attempt():
 from prmonitor.services.jobs import ingest_result
 req=plan_jobs('r',mode='host').jobs[0]
 attempt=ingest_result({'run_id':'r','job_id':req.job_id,'request_hash':req.request_hash,'result':{}},req,result_hash='h')
 assert attempt['run_id']=='r' and attempt['result_hash']=='h'

def test_resume_reuses_only_matching_successes_and_retries_failed():
 from prmonitor.services.jobs import resume_plan
 plan=plan_jobs('r',mode='headless',strategy='split',expected_categories=['a','b'])
 prior={plan.jobs[0].job_id:{'state':'succeeded','request_hash':plan.jobs[0].request_hash},
        plan.jobs[1].job_id:{'state':'failed','request_hash':plan.jobs[1].request_hash}}
 resumed=resume_plan(plan,prior)
 assert [j.job_id for j in resumed.jobs] == [plan.jobs[1].job_id, plan.jobs[2].job_id]

def test_repair_request_is_hash_scoped():
 from prmonitor.services.jobs import build_repair_request
 req=plan_jobs('r',mode='host').jobs[0]
 repaired=build_repair_request(req,[{'code':'UNKNOWN_REF'}])
 assert repaired.request_hash != req.request_hash and repaired.payload['repair_for'] == req.request_hash

def test_optional_enrichment_failure_is_warning_not_required_result():
 from prmonitor.services.runs import execute_headless
 plan=plan_jobs('r',mode='headless',enrichment='optional')
 def invoke(req):
  return ({'error': {'code':'ENRICHMENT_DOWN'}} if not req.required else
          {'run_id':req.run_id,'job_id':req.job_id,'request_hash':req.request_hash,'result':{}})
 execution=execute_headless(plan, invoke, max_calls=2, deadline_seconds=5)
 assert execution.calls == 2 and execution.results[0]['warning']['code'] == 'ENRICHMENT_DOWN'
