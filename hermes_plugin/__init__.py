"""Hermes native registration shim; importing it never installs or invokes the engine."""
from pathlib import Path

def register(ctx):
    skills_dir = Path(__file__).resolve().parent.parent / 'skills'
    for child in sorted(skills_dir.iterdir()):
        skill = child / 'SKILL.md'
        if child.is_dir() and skill.is_file() and hasattr(ctx, 'register_skill'):
            ctx.register_skill(child.name, skill)
