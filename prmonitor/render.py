"""Validated briefing rendering boundary."""
from __future__ import annotations
from pathlib import Path
from .render_safety import text, safe_url
from .validation import ValidationReport, deliverable_is_current

#: Marks a HELD deliverable wherever it is rendered — canonical renderer and the
#: legacy newsletter wrapper share this one string so previews look identical.
HELD_WATERMARK = '<div class="review-needed">REVIEW NEEDED — HELD</div>\n'

def render_briefing(briefing: dict, report: ValidationReport, *, policy: dict,
                    output: Path, allow_held: bool = False) -> Path:
    if report.status != 'PASS' and not allow_held:
        raise ValueError('HELD_RENDER_REQUIRES_ALLOW_HELD')
    watermark = HELD_WATERMARK if report.status != 'PASS' else ''
    body=f'<h1>{text(briefing.get("tldr"))}</h1>\n'
    for insight in briefing.get('insights',[]):
        body += f'<section><p>{text(insight.get("observation"))}</p></section>\n'
    output.parent.mkdir(parents=True,exist_ok=True); output.write_text(watermark+body,encoding='utf-8'); return output
