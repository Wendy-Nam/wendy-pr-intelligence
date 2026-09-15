"""Deterministic, explicit-input article classification."""
from __future__ import annotations
from .articles import canonical_url

def classify_articles(articles: list[dict], *, profile: dict, keywords: dict, tuning: dict | None = None) -> list[dict]:
    """Classify without I/O; domain rules arrive as snapshot inputs."""
    tuning=tuning or {}; company=profile.get('company',{}); aliases=[company.get('name',''),*(company.get('aliases') or [])]
    excludes=[str(x).lower() for x in keywords.get('strong_exclude',[])]; boosts=[str(x).lower() for x in keywords.get('boost',keywords.get('boost_keywords',[]))]
    categories=profile.get('categories',{}); competitors=profile.get('competitors',[]); result=[]
    for raw in articles:
        article=dict(raw); title=article.get('title',''); body=article.get('full_text',article.get('summary','')); text=(title+' '+body).lower()
        if any(x and x in text for x in excludes): article.update(decision='exclude',relevance_score=0,categories=[]); result.append(article); continue
        article['self_mention']=any(str(x).lower() in text for x in aliases if x)
        hits=[x for x in boosts if x in text]; article['relevance_score']=len(hits)
        assigned=[]
        for cid, cfg in categories.items():
            terms=[*cfg.get('watch_keywords',[]),*cfg.get('key_players',[]),cfg.get('label_ko','')]
            if any(str(t).lower() in text for t in terms if t): assigned.append(cid)
        article['categories']=assigned or ['uncategorized']
        mentioned=[]
        for c in competitors:
            names=[c.get('name',''),*(c.get('aliases') or [])]
            if any(str(n).lower() in text for n in names if n): mentioned.append(c.get('name'))
        article['competitors_mentioned']=mentioned
        article['decision']='exclude' if article['self_mention'] else 'include'
        if article.get('url'):
            article['canonical_url']=canonical_url(article['url'])
        result.append(article)
    return result
