"""Pure self-PR record normalization."""
from __future__ import annotations
def to_pr_records(articles: list[dict], *, company_aliases: list[str]) -> list[dict]:
 aliases=[x.lower() for x in company_aliases]; out=[]
 for a in articles:
  text=(a.get('title','')+' '+a.get('summary',a.get('body',''))).strip(); low=text.lower()
  if aliases and not any(x in low for x in aliases): continue  # ponytail: empty scope = already-scoped input
  tone=a.get('tone') or ('negative' if any(x in low for x in ('risk','lawsuit','decline')) else 'neutral')
  out.append({'id':a.get('id'), 'title':a.get('title',''), 'summary':a.get('summary',''), 'tone':tone, 'source_name':a.get('source_name',''), 'source_url':a.get('url')})
 return out
