import os,sys,json,tempfile,importlib.util,subprocess
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch
ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT))
tmp=Path(tempfile.mkdtemp(prefix='wendy-audit-'))
os.environ.update(PRM_PROJECT_DIR=str(tmp/'project'),PRM_PLUGIN_DATA=str(tmp/'cache'),PRM_LLM='codex',PRM_KEEP_SPLITS='1')
from prmonitor import paths
from prmonitor.steps import llm_adapter,market_brief,pre,post
paths.ensure_dirs()
date='2026-09-15'
ctx=paths.PROCESSED_DIR/f'synthesis-context-{date}.json'
ctx.write_text(json.dumps({'categories':[{'category_id':'ev','facts':[]}]}))
models=[]
def failed(job):
    models.append(job.model)
    return 1
with patch.object(llm_adapter,'run_synthesis',side_effect=failed),patch.object(market_brief.time,'sleep'):
    market_brief._run_parallel_synth(date,'','medium',dict(os.environ))
briefing=paths.BRIEFING_DIR/f'newsletter-briefing-{date}.json'
data=json.loads(briefing.read_text())
spec=importlib.util.spec_from_file_location('audit_formatter',ROOT/'skills/briefing-formatter/format.py')
fmt=importlib.util.module_from_spec(spec);spec.loader.exec_module(fmt)
print('ALL_SYNTH_FAILED',{'briefing_exists':briefing.exists(),'data':data,'quality_warnings':fmt.validate_briefing_quality(data),'models':models})
print('ARGV_QUOTING')
for prompt in ['Summarize two articles',"What's new?",'a "quoted" headline']:
    try: print(repr(prompt),llm_adapter._build_argv('echo {prompt}',llm_adapter.SynthJob(prompt=prompt,model='')))
    except Exception as e: print(repr(prompt),type(e).__name__,str(e))
print('FLAGS')
from prmonitor.__main__ import build_parser
for flag in ['--no-email','--dry-run']:
    try: build_parser().parse_args(['market-brief',flag])
    except SystemExit as e: print(flag,e.code)
# Expanded collection must rebuild synthesis context; fake deterministic scripts only.
raw=paths.RAW_DIR/f'urls-{date}.json';raw.write_text('{"urls":[{}]}')
(paths.RAW_DIR/f'urls-{date}.hours').write_text('24')
ctx.write_text('{"stale":true}')
steps=[]
def step(argv,msg):
    name=Path(argv[1]).name;steps.append(name)
    outputs={'fetch-urls.py':(raw,{'urls':[{}]}),'batch-extract.py':(paths.PROCESSED_DIR/f'extracted-{date}.json',{}),'classify.py':(paths.PROCESSED_DIR/f'classified-{date}.json',{}),'aggregate.py':(paths.PROCESSED_DIR/f'newsletter-facts-{date}.json',{}),'preload-synthesis-context.py':(ctx,{'fresh':True})}
    if name in outputs:
        p,d=outputs[name];p.write_text(json.dumps(d))
    return True
with patch.object(pre,'_run_step',side_effect=step):
    rc=pre.run(SimpleNamespace(date=date,hours=72))
print('CACHE_EXPANSION',{'rc':rc,'steps':steps,'synthesis_context':json.loads(ctx.read_text())})
# Exercise real formatter + resolver through post, but intercept external delivery and persistent updates.
paths.venv_python=lambda: ROOT/'.venv/bin/python'
sent=[]
def fake_send(*args,**kw):sent.append(True);return True
with patch.object(post,'send_html_email',side_effect=fake_send),patch.object(post,'_write_exec_log'),patch.object(post,'cleanup_retention'):
    rc=post.run(SimpleNamespace(date=date,hours=24,no_email=False))
print('EMPTY_BRIEFING_POST',{'rc':rc,'would_send':bool(sent),'review_exists':(paths.OUTPUT_DIR/'REVIEW_NEEDED.md').exists()})
print('MISSING_GATE_FILE',post._quality_warning_count('missing'))
print('TEMP_ROOT',tmp)
