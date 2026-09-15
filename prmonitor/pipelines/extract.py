"""Explicit extraction normalization and UTC window filtering."""
from __future__ import annotations
from datetime import datetime
from .articles import article_id, canonical_url

def normalize_extracted(rows: list[dict], *, window_start: str, window_end: str) -> tuple[list[dict], int]:
    start=datetime.fromisoformat(window_start.replace('Z','+00:00')); end=datetime.fromisoformat(window_end.replace('Z','+00:00'))
    output=[]; unknown=0
    for raw in rows:
        article=dict(raw); published=article.get('published_at') or article.get('published_date')
        if published:
            try:
                point=datetime.fromisoformat(str(published).replace('Z','+00:00'))
                if not start <= point < end: continue
            except ValueError: article['timestamp_unknown']=True; unknown+=1
        else: article['timestamp_unknown']=True; unknown+=1
        if article.get('url'):
            article['canonical_url']=canonical_url(article['url'])
        article['id']=article_id(article.get('canonical_url'),title=article.get('title',''),source=article.get('source_name',''),published_at=str(published or ''))
        output.append(article)
    return output, unknown
