---
name: pr-setup
description: Initialize, research, and maintain a PR Intelligence workspace.
---

# PR Monitor setup

Use this skill for setup and diagnosis. The engine is company-neutral; a
workspace becomes useful only after its `config/` and `data/self-context/`
files describe the organization and market. For a research-backed draft, invoke
the `domain-pack-research` skill.

## Basic setup

For an explicit first installation, run:

```bash
python3 prmonitor_launch.py init --force
python3 -m prmonitor doctor --strict
```

Do not install dependencies or overwrite existing user configuration unless the
user explicitly requests setup or an update.

## Research-backed scaffold

When the user asks to create a company configuration, offer these modes:

| Mode | Needed input | Result |
|---|---|---|
| Automatic | Company name and industry | Research-backed first draft. |
| Assisted (recommended) | Company, industry, plus known competitors or focus areas | Preserves user facts and researches only gaps. |
| Manual | All desired inputs | No web research. |

For Automatic or Assisted mode, use `domain-pack-research`. Never skip the
approval gate between research and writing files.

1. **Seed** — collect company name (Korean and English if applicable), industry,
   positioning, and any known competitors, categories, regions, or sources.
2. **Research** — use web research to identify 6–12 competitors, 4–7 monitoring
   categories, company-name aliases, current events, news sources, and Korean/
   English search terms. Keep source URLs for factual claims.
3. **Review** — present a compact proposed scope with sources. Mark uncertain
   items as candidates and wait for the user's approval or edits.
4. **Scaffold** — after approval, create or update the YAML files using the
   matching schemas in `config-templates/`: `company-profile`, `categories`,
   `branding`, `keywords`, `sources`, `style`, `classify-tuning`, `pr-queries`,
   `tone-lexicon`, `media`, and `delivery` as applicable.
5. **Context** — draft `data/self-context/company-narrative.md`, key events,
   competitor landscape, and `prompt-examples.yaml`. Clearly label generated
   examples as drafts requiring editorial review.
6. **Verify** — parse every YAML file, run `python3 -m prmonitor doctor --strict`,
   then perform a no-email dry run before enabling delivery.

## Existing workspaces

Before changing a populated `config/`, inspect it and explain what will change.
Back up existing user files before an explicit replacement. User-provided facts
always win over research; never fabricate competitors, metrics, or source URLs.

## Output

Report created or changed files, research sources, assumptions/candidates that
need review, and the next safe command: `market-brief` or `self-brief`.
