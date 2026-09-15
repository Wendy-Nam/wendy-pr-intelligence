from pathlib import Path
import json,hashlib,re
from jsonschema import Draft202012Validator
root=Path(__file__).resolve().parents[1];ex=root/'examples'
def read(n):return json.loads((ex/n).read_text())
def canon(x):return json.dumps(x,ensure_ascii=False,sort_keys=True,separators=(',',':'),allow_nan=False).encode()
schema=read('market-result.schema.json');Draft202012Validator.check_schema(schema)
Draft202012Validator(schema).validate(read('llm-result.json'))
req=read('llm-request.json');res=read('llm-result.json')
assert req['input_hash']==hashlib.sha256(canon({k:req[k] for k in ['kind','instructions','input','output_schema','limits']})).hexdigest()
assert (req['run_id'],req['job_id'],req['input_hash'])==(res['run_id'],res['job_id'],res['input_hash'])
registry={x['id']:x for x in read('articles.json')['articles']}
for i,a in registry.items():assert i=='a_'+hashlib.sha256(a['canonical_url'].encode()).hexdigest()[:32]
assert set(req['input']['required_ref_ids'])==set(registry)
body=res['payload'];assert {x['category_id'] for x in body['category_summary']}==set(req['input']['required_category_ids'])
for c in body['category_summary']:
 expected={a['id'] for a in req['input']['articles'] if a['category_id']==c['category_id']}
 assert set(c['covered_refs'])==expected
 assert set().union(*(set(x['refs']) for x in c['paragraphs']))==expected
assert {h['ref'] for h in body['headlines']}==set(registry)
report=read('validation-report.json')
assert report['briefing_hash']==hashlib.sha256((ex/'briefing.json').read_bytes()).hexdigest()
assert report['policy_hash']==hashlib.sha256(canon(read('validation-policy.json'))).hexdigest()
for p in root.rglob('*.json'):json.loads(p.read_text())
for p in root.rglob('*.md'):
 s=p.read_text()
 for dest in re.findall(r'\]\(([^)]+)\)',s):
  if '://' in dest or dest.startswith('#'):continue
  dest=dest.split('#')[0]
  assert (p.parent/dest).exists(),(p,dest)
status=json.loads((root/'STATUS.json').read_text());ids={t['id'] for t in status['tickets']}
for t in status['tickets']:
 assert set(t['depends_on'])<=ids
 assert t['status'] in {'pending','in_progress','done','blocked'}
impl=(root/'04-IMPLEMENTATION.md').read_text();verify=(root/'05-VERIFICATION.md').read_text()
for i in range(15):assert f'## T{i:02}' in impl
for i in range(95):assert f'| V{i:02} |' in verify
print('PASS: schema, request/result hashes, refs/coverage, article IDs, artifact hashes, local links, T00–T14 and V00–V94')
print('Markdown files:',len(list(root.rglob('*.md'))),'JSON files:',len(list(root.rglob('*.json'))))
