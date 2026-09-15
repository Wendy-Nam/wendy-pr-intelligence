"""Deterministic briefing/content gate independent of renderer and transport."""
from __future__ import annotations
from dataclasses import dataclass
from .models import canonical_json_hash

@dataclass(frozen=True)
class Finding:
    code: str; severity: str; path: str; message: str; refs: tuple[str,...]=()
@dataclass(frozen=True)
class ValidationReport:
    status: str; findings: tuple[Finding,...]; briefing_hash: str; policy_hash: str
    required_jobs: dict; coverage: dict
    def as_dict(self):
        return {'schema_version':1,'status':self.status,'findings':[{'code':f.code,'severity':f.severity,'path':f.path,'message':f.message,'refs':list(f.refs)} for f in self.findings], 'briefing_hash':self.briefing_hash,'policy_hash':self.policy_hash,'required_jobs':self.required_jobs,'coverage':self.coverage}

def validate_briefing(briefing: dict, *, article_ids: set[str], category_ids: set[str], policy: dict | None = None) -> ValidationReport:
 policy=policy or {}; findings=[]; refs=[]
 try:
  if not isinstance(briefing,dict):
   findings.append(Finding('SCHEMA_INVALID','error','/','briefing must be object'))
  else:
   if not isinstance(briefing.get('tldr'),str) or not briefing.get('tldr','').strip():
    findings.append(Finding('EMPTY_BRIEFING','error','/tldr','tldr is empty'))
   insights = briefing.get('insights')
   if not isinstance(insights,list) or not insights:
    findings.append(Finding('SCHEMA_INVALID','error','/insights','required insights missing'))
    insights = []
   for i, insight in enumerate(insights):
    if not isinstance(insight, dict):
     findings.append(Finding('SCHEMA_INVALID','error',f'/insights/{i}','insight must be object'))
     continue
    raw_refs = insight.get('refs', [])
    if not isinstance(raw_refs, list):
     findings.append(Finding('SCHEMA_INVALID','error',f'/insights/{i}/refs','refs must be array'))
     continue
    refs.extend(x for x in raw_refs if isinstance(x, str))
   seen=set(); expected=set(category_ids)
   categories = briefing.get('category_summary', [])
   if not isinstance(categories, list):
    findings.append(Finding('SCHEMA_INVALID','error','/category_summary','category_summary must be array'))
    categories=[]
   for i, cat in enumerate(categories):
    cid = cat.get('category_id') if isinstance(cat, dict) else None
    if cid in seen: findings.append(Finding('DUPLICATE_CATEGORY','error',f'/category_summary/{i}','duplicate category'))
    if cid is not None: seen.add(cid)
   for cid in expected-seen: findings.append(Finding('MISSING_CATEGORY','error','/category_summary',f'missing category {cid}'))
   unknown=set(refs)-set(article_ids)
   if unknown: findings.append(Finding('UNKNOWN_REF','error','/insights',f'unknown refs: {sorted(unknown)}',tuple(sorted(unknown))))
   declared = briefing.get('covered_refs')
   if isinstance(declared, list) and set(declared) - set(refs):
    findings.append(Finding('COVERAGE_GAP','error','/covered_refs','declared refs are absent from insight body'))
   required_refs = set(policy.get('required_refs', [])) if isinstance(policy.get('required_refs', []), list) else set()
   missing_required = required_refs - set(refs)
   if missing_required: findings.append(Finding('COVERAGE_GAP','error','/insights',f'missing required refs: {sorted(missing_required)}',tuple(sorted(missing_required))))
 except Exception as exc:
  findings.append(Finding('VALIDATOR_ERROR','error','/','validator exception: '+type(exc).__name__))
 status='HELD' if findings else 'PASS'
 return ValidationReport(status,tuple(findings),canonical_json_hash(briefing),canonical_json_hash(policy),{'expected':1,'succeeded':1},{'expected':len(article_ids),'covered':len(set(refs)&set(article_ids))})

def deliverable_is_current(report: ValidationReport, *, briefing: dict, policy: dict,
                           html_bytes: bytes, expected_html_hash: str | None = None) -> bool:
    """Final send guard: PASS and all content/policy/render hashes still match."""
    import hashlib
    return (report.status == 'PASS' and report.briefing_hash == canonical_json_hash(briefing)
            and report.policy_hash == canonical_json_hash(policy)
            and (expected_html_hash is None or hashlib.sha256(html_bytes).hexdigest() == expected_html_hash))
