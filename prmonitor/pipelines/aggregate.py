"""Explicit-input aggregation primitives; no config/global path reads."""
from __future__ import annotations
from datetime import datetime
from difflib import SequenceMatcher
from .articles import article_id

def _score(a, ref_date):
    value=a.get('importance',a.get('relevance_score',0)); bonus=0
    try:
        delta=(datetime.strptime(ref_date,'%Y-%m-%d')-datetime.strptime((a.get('published_date') or '')[:10],'%Y-%m-%d')).days
        bonus=1 if delta <= 2 else .5 if delta <= 4 else 0
    except ValueError: pass
    return float(value)+bonus

def aggregate_articles(articles: list[dict], *, profile: dict, ref_date: str, tier1_threshold: int=4, tier1_max: int=5) -> dict:
    """Group classified articles while retaining legacy category/tier semantics."""
    groups={}
    for article in articles:
        if article.get('decision') == 'exclude' or article.get('self_mention'): continue
        for category in article.get('categories') or ['uncategorized']:
            groups.setdefault(category,[]).append(dict(article))
    result=[]
    labels={k:v.get('label_ko',k) for k,v in (profile.get('categories') or {}).items()}
    for cid, rows in groups.items():
        rows.sort(key=lambda a:_score(a,ref_date),reverse=True); kept=[]; tier1=0
        for article in rows:
            title=article.get('title','')
            if any(SequenceMatcher(None,title,x.get('title','')).ratio()>.85 for x in kept): continue
            is_one=_score(article,ref_date)>=tier1_threshold and tier1<tier1_max
            if is_one: tier1+=1
            article['_tier']=1 if is_one else 2; article['id']=article_id(article.get('canonical_url') or article.get('url'),title=title,source=article.get('source_name',''),published_at=article.get('published_date',''))
            kept.append(article)
        result.append({'category_id':cid,'category_name':labels.get(cid,cid),'facts':kept})
    return {'date':ref_date,'categories':result}
