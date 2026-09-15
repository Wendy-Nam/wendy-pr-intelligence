#!/usr/bin/env python3
"""Build public, fictional demos using production renderers. No network or LLM calls."""
import importlib.util
import json
import os
import re
import sys
import tempfile
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / 'docs/demo'
DATE = '2026-09-15'

def module(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod

def decorate(html):
    banner = '''<nav class="sample-nav" aria-label="샘플 탐색"><a href="./">← 샘플 목록</a><span>DEMO · 가상 기업·기사·수치로 만든 예시</span><a href="sources.html">샘플 데이터 안내</a></nav>'''
    css = '''<style>.sample-nav{display:flex;flex-wrap:wrap;gap:12px;justify-content:space-between;padding:14px 0;margin-bottom:24px;border-bottom:1px solid #ddd;font:12px/1.6 system-ui;color:#655f56}.sample-nav a{color:#344d42}html{overflow-wrap:anywhere}img{max-width:100%}@media(max-width:600px){body{padding:18px 12px!important}.sample-nav{font-size:11px}}</style>'''
    return re.sub(r'(<body\b[^>]*>)', lambda m: m.group(1)+banner, html.replace('</head>', css+'</head>'), count=1)


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix='prm-demo-') as td:
        os.environ.update(PRM_PLUGIN_ROOT=str(ROOT), PRM_PROJECT_DIR=td, PRM_PLUGIN_DATA=td, PRM_LLM='generic', PRM_SYNTH_CMD='')
        sys.path.insert(0, str(ROOT))
        sys.path.insert(0, str(ROOT/'scripts'))
        from prmonitor import paths
        paths.ensure_dirs()
        from prmonitor.steps import llm_adapter
        # Fixture news deliberately names fictional companies and sample outlets.
        items = [
            ('battery','배터리','Northstar Cell, 저온 충전 성능 개선한 LFP 셀 공개','Northstar Cell은 영하 10도 충전 시간을 기존 대비 20% 줄인 시제품을 공개했다. 양산 일정은 공개하지 않았다.'),
            ('battery','배터리','Aster EV, 배터리 재활용 업체와 회수 체계 시범 운영','Aster EV는 차량 500대를 대상으로 폐배터리 회수와 소재 추적을 시험한다.'),
            ('charging','충전 인프라','Voltway, 물류 거점 12곳에 급속 충전소 구축','Voltway는 배송 차량용 충전소 12곳을 개설했다. 야간 충전 예약 기능도 제공한다.'),
            ('charging','충전 인프라','Meridian Charge, 충전기 가동률 공개 시작','Meridian Charge는 충전소별 가동률과 평균 대기 시간을 공개했다.'),
            ('models','신차·라인업','Aster EV, 도심 배송용 전기 밴 사전 계약 시작','Aster EV는 적재 공간 6세제곱미터의 전기 밴을 공개했다. 첫 인도는 내년 상반기로 안내했다.'),
            ('funding','투자 · M&A','Northstar Cell, 시험 생산 설비 확대 자금 유치','Northstar Cell은 시험 생산 설비 증설에 사용할 300억원 규모의 투자를 유치했다고 밝혔다.'),
        ]
        sources = [dict(url=f'sources.html#market-{i}',name=f'샘플 산업저널 {i}',date=DATE,title=t,summary=s,category=c) for i,(c,n,t,s) in enumerate(items,1)]
        cats=[]
        for cid,label in dict((c,n) for c,n,_,_ in items).items():
            group=[s for s in sources if s['category']==cid]
            cats.append(dict(category_id=cid,category_name=label,summary=' '.join(s['summary'] for s in group),sources=group))
        briefing=dict(date=DATE,tldr='배터리 성능 경쟁과 함께 충전 운영 정보의 공개가 늘었다. 전기 밴 신규 진입과 배터리 시험 생산 투자도 이어졌다.\n\nContoso Motors는 배송 고객의 겨울철 운행 조건과 충전 대기 시간을 함께 점검할 수 있다. 경쟁사 발표 수치는 실제 운행 조건과 대조할 대상이다.',
            headlines=[dict(text=s['title'],source=s['name'],url=s['url'],group='Aster EV' if 'Aster' in s['title'] else '업계 동향') for s in sources],
            insights=[dict(title='겨울철 운행 성능을 충전 운영 데이터와 함께 비교',observation='Northstar Cell은 저온 충전 시제품을 공개했다. Meridian Charge는 충전 대기 시간을 공개했다.',implication='자사 배송 고객의 겨울철 운행 기록을 정리한다. 충전 속도와 실제 대기 시간을 함께 비교할 수 있다.',facts=[sources[0],sources[3]]),
                dict(title='전기 밴 비교 기준에 적재 공간과 인도 일정을 포함',observation='Aster EV가 도심 배송용 전기 밴의 사전 계약을 시작했다.',implication='자사 영업 자료에 적재 공간과 총운영비 비교표를 추가한다. 경쟁 차량의 실제 인도 일정은 후속 확인 대상으로 둔다.',facts=[sources[4]])],
            category_summary=cats,all_sources=sources,company_glossary=[dict(name='Northstar Cell',desc='가상의 배터리 셀 개발사. 저온 성능과 시험 생산을 연구한다.'),dict(name='Voltway',desc='가상의 상용차 충전 사업자. 물류 거점 충전소를 운영한다.')])
        fmt=module('demo_formatter', ROOT/'skills/briefing-formatter/format.py')
        html=fmt.build_html(briefing,DATE,collection_start='2026-09-14',foreign_count=4,domestic_count=2,hours=48)
        html=re.sub(r'생성 \d{4}-\d{2}-\d{2} \d{2}:\d{2} KST', '샘플 기준일 '+DATE, html)
        (OUT/'market-brief.html').write_text(decorate(html))
        (OUT/'market-brief.sample.json').write_text(json.dumps(briefing,ensure_ascii=False,indent=2)+'\n')
        pr_items=[
            ('콘토소 모터스, 배송용 전기 밴 200대 공급 계약','콘토소 모터스가 가상 물류기업과 전기 밴 200대 공급 계약을 체결했다. 차량은 하반기에 순차 인도한다.'),
            ('콘토소 모터스, 지방 서비스센터 3곳 신규 개설','콘토소 모터스는 서비스센터 3곳을 개설했다. 정비 예약과 긴급 출동 지원 범위를 확대했다.'),
            ('콘토소 모터스 일부 차종 인도 지연…일정 재안내','콘토소 모터스 일부 차종의 인도가 지연됐다. 회사는 부품 수급 일정을 확인해 고객에게 변경 일정을 안내했다.'),
            ('전기 상용차 선택 기준, 가격에서 운영비로 확대','샘플 산업저널은 전기 상용차의 충전비와 정비 시간을 비교했다. 콘토소 모터스는 비교 대상 업체 중 하나로 언급됐다.'),
            ('물류 거점 충전 인프라 확충, 차량 업체 협력 늘어','물류 거점 충전 인프라 구축에 여러 차량 업체가 참여하고 있다. 콘토소 모터스도 협력 사례로 소개됐다.'),
            ('콘토소 모터스 주가 상승…전기차 업종 동반 강세','콘토소 모터스 주가가 상승했다. 샘플 증권뉴스는 전기차 업종 전반의 움직임과 함께 소개했다.'),
        ]
        articles=[dict(title=t,full_text=s,url=f'sources.html#self-{i}',source_name=f'샘플 경제뉴스 {i}',published_date=DATE,is_domestic=True) for i,(t,s) in enumerate(pr_items,1)]
        with patch.object(sys,'argv',['render_pr_clipping.py',DATE,'24']):
            pr=module('demo_pr',ROOT/'scripts/pr/render_pr_clipping.py')
        narrative='공급 계약과 서비스센터 개설 보도가 자사 직접 언급의 중심이다. 일부 차종 인도 지연 보도도 있어 고객 안내 일정과 후속 보도를 확인할 필요가 있다.\n\n간접 언급은 총운영비 비교와 충전 인프라 협력 기사에 나타났다. 주가 보도는 사업 성과 보도와 구분해 정리했다.'
        class FixtureBackend:
            def run_text(self,*args,**kwargs): return 0,narrative
        with patch.object(pr,'fetch_gnews_pr',return_value=articles),patch.object(pr,'load_classified_pr',return_value=[]),patch.object(pr,'fetch_missing_bodies'),patch.object(pr,'classify_and_summarize_batch',return_value=({},{})),patch.object(pr,'_LLM_OK',True),patch.object(llm_adapter,'get_backend',return_value=FixtureBackend()):
            pr.main()
        html=(paths.PR_OUTPUT_DIR/f'pr-monitoring-{DATE}.html').read_text()
        html=re.sub(r'자동생성 [^<]+ KST','샘플 기준일 2026-09-15',html)
        (OUT/'self-brief.html').write_text(decorate(html))
        (OUT/'self-brief.sample.json').write_text(json.dumps(articles,ensure_ascii=False,indent=2)+'\n')
        from html import escape
        entries=''.join(f'<article id="market-{i}"><small>마켓 샘플 {i}</small><h2>{escape(t)}</h2><p>{escape(s)}</p></article>' for i,(_,_,t,s) in enumerate(items,1))
        entries+=''.join(f'<article id="self-{i}"><small>자사 PR 샘플 {i}</small><h2>{escape(t)}</h2><p>{escape(s)}</p></article>' for i,(t,s) in enumerate(pr_items,1))
        (OUT/'sources.html').write_text('<!doctype html><html lang="ko"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>샘플 데이터 안내</title><style>body{font:16px/1.8 system-ui;max-width:760px;margin:40px auto;padding:0 20px;color:#27332d}article{padding:24px 0;border-bottom:1px solid #ddd}h2{font-size:20px}a{color:#285940}</style></head><body><a href="./">← 샘플 목록</a><h1>샘플 데이터 안내</h1><p>모든 기업·기사·수치·매체는 화면 시연을 위해 작성한 가상 예시입니다. 실제 보도나 투자 정보가 아닙니다. 실제 운영에서는 각 출처가 원문 기사로 연결됩니다.</p>'+entries+'</body></html>')

if __name__=='__main__': main()
