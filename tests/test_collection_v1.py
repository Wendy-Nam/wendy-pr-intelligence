"""T03 exact cache and article identity regressions (V17--V23 core)."""
from prmonitor.pipelines.articles import article_id, canonical_url, registry
from prmonitor.storage.cache import StageCache, stage_key

def test_canonical_article_id_ignores_tracking_and_fragment():
    a = 'HTTPS://Example.COM:443/A?utm_source=x&x=1#frag'
    b = 'https://example.com/A?x=1'
    assert canonical_url(a) == b
    assert article_id(a) == article_id(b)

def test_exact_key_cache_reuses_and_invalidates(tmp_path):
    cache=StageCache(tmp_path); calls=[]
    key=stage_key('context','1',{'aggregate':'a'},'cfg','2026-01-01T00:00:00Z','2026-01-02T00:00:00Z',{'self':'x'})
    assert cache.get_or_build(key,lambda: calls.append(1) or {'x':1}) == ({'x':1},False)
    assert cache.get_or_build(key,lambda: calls.append(2) or {'x':2}) == ({'x':1},True)
    changed=stage_key('context','1',{'aggregate':'a'},'cfg','2026-01-01T00:00:00Z','2026-01-03T00:00:00Z',{'self':'x'})
    assert cache.get_or_build(changed,lambda: calls.append(3) or {'x':3}) == ({'x':3},False)
    assert calls == [1,3]
    assert cache.get_or_build(key,lambda: calls.append(4) or {'x':4}, force_refresh=True) == ({'x':4},False)

def test_corrupt_cache_rebuilds_and_tracking_aliases_share_registry_id(tmp_path):
    cache=StageCache(tmp_path); key='a'*64
    cache.get_or_build(key,lambda:{'x':1})
    (tmp_path/'stages'/key/'artifact.json').write_text('{bad',encoding='utf-8')
    assert cache.get_or_build(key,lambda:{'x':2}) == ({'x':2},False)
    merged = registry([{'url':'https://x/a','title':'a'}, {'url':'https://x/a#fragment','title':'b'}])
    assert len(merged) == 1

def test_all_source_failure_is_not_no_data():
    from prmonitor.services.collection import SourceResult, report
    from prmonitor.models import RunState
    failed = report('r','s','e',[SourceResult('rss','failed',error={'code':'NETWORK'})],discovered=0,extracted=0,eligible=0)
    empty = report('r','s','e',[SourceResult('rss','ok')],discovered=0,extracted=0,eligible=0)
    assert failed.outcome is RunState.FAILED
    assert empty.outcome is RunState.NO_DATA

def test_context_changes_when_self_context_changes():
    from prmonitor.pipelines.context import build_context
    base = dict(date='2026-09-15',categories=[],competitor_articles={},window_start='s',window_end='e')
    a=build_context(**base,self_context={'baseline':'a'})
    b=build_context(**base,self_context={'baseline':'b'})
    assert a['input_hash'] != b['input_hash']
    assert a['self_context_bundle']['baseline'] == 'a'

def test_explicit_aggregate_has_no_path_or_config_dependency():
    from prmonitor.pipelines.aggregate import aggregate_articles
    output=aggregate_articles([{'url':'https://x/a','title':'A','categories':['c'],'relevance_score':4}],profile={'categories':{'c':{'label_ko':'C'}}},ref_date='2026-09-15')
    fact=output['categories'][0]['facts'][0]
    assert fact['id'].startswith('a_') and fact['_tier'] == 1

def test_explicit_classifier_keeps_self_articles_out_of_market_pool():
    from prmonitor.pipelines.classify import classify_articles
    out=classify_articles([{'url':'https://x/a','title':'Our Robot launch'}],profile={'company':{'name':'Our Robot'},'categories':{}},keywords={})
    assert out[0]['self_mention'] and out[0]['decision'] == 'exclude'

def test_collection_service_reuses_exact_report(tmp_path):
    from prmonitor.services.collection import CollectionService, SourceResult, report
    from prmonitor.storage.cache import StageCache
    calls=[]; service=CollectionService(StageCache(tmp_path))
    def produce():
        calls.append(1); return report('r','s','e',[SourceResult('rss','ok')],discovered=1,extracted=1,eligible=1)
    first,reused=service.collect(cache_key='b'*64,producer=produce)
    second,reused_again=service.collect(cache_key='b'*64,producer=produce)
    assert first.outcome == second.outcome and not reused and reused_again and calls == [1]

def test_extraction_window_excludes_future_and_marks_unknown_time():
    from prmonitor.pipelines.extract import normalize_extracted
    rows, unknown=normalize_extracted([{'url':'https://x/a','published_at':'2026-09-15T00:00:00Z'},{'url':'https://x/b'}],window_start='2026-09-14T00:00:00Z',window_end='2026-09-16T00:00:00Z')
    assert len(rows) == 2 and unknown == 1 and rows[1]['timestamp_unknown']
