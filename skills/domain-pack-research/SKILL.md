---
name: domain-pack-research
description: Research an organization and create a reviewable PR Monitor domain-pack draft, including competitors, categories, news sources, keywords, and self-context.
---

# Research-backed domain-pack drafting

Use this skill when a user wants to initialize or substantially improve PR
Monitor configuration from a company name, industry, website, or existing
domain pack. This is a drafting workflow: it produces source-backed proposals
and writes files only after the user approves the proposed scope.

## Inputs and modes

Collect the company name, industry, primary geography, and desired briefing
language. In assisted mode, also collect any known competitors, priority topics,
customers, products, or trusted publications.

- **Automatic**: research all missing information.
- **Assisted**: preserve user facts and research only gaps. Prefer this mode.
- **Refresh**: retain the existing pack, propose dated additions or removals,
  and never replace user values without approval.

Before writing an existing workspace, inspect `config/` and create a backup when
the user explicitly approves a replacement. Never treat template examples as
facts about the user’s organization.

## Research standard

Build a small evidence ledger before creating YAML. For every proposed
competitor, source, event, or important claim, retain a direct source URL and
the reason it belongs in the brief.

Use official company/regulatory material and reputable specialist news where
available. Do not invent metrics, product claims, RSS URLs, aliases, or company
relationships. Label uncertain items as `candidate` and ask the user to confirm
or remove them. Use date-qualified wording for changeable facts.

## Draft in three reviewable passes

1. **Monitoring scope** — propose 6–12 competitors, 4–7 categories, company
   aliases, priority regions, and 3–8 monitoring questions. Include sources and
   wait for approval.
2. **Collection design** — for each approved category, propose Korean and
   English keywords, precise Google News queries, and high-quality RSS or
   newsroom sources. Verify RSS URLs before recording them.
3. **Editorial context** — draft positioning, strategic relationships, dated
   key events, competitor baselines, and good/bad insight examples. Every
   generated example is a draft for editorial review, not an internal fact.

## Write only after approval

Use `config-templates/` as the exact schema authority. Generate only the files
needed by the approved scope:

| Purpose | Files |
|---|---|
| Company and taxonomy | `company-profile.yaml`, `categories.yaml`, `branding.yaml` |
| Collection and ranking | `sources.yaml`, `keywords.yaml`, `classify-tuning.yaml` |
| PR monitoring | `pr-queries.yaml`, `tone-lexicon.yaml`, `media.yaml` |
| Editorial rules | `style.yaml`, `prompt-examples.yaml` |
| Delivery and runtime | `delivery.yaml`, `runtime.yaml` only when requested |
| Long-lived context | `data/self-context/company-narrative.md`, key-events, competitor landscape |

Keep aliases, category IDs, colors, watch keywords, source locale, query
purpose, and key-event provenance complete.

## Verification and handoff

After writing, parse every YAML, run `python3 -m prmonitor doctor --strict`, and
perform a no-email dry run. Report changed files, the evidence ledger, candidate
items awaiting approval, collection coverage, and the next command:
`market-brief` or `self-brief`.

Do not enable delivery, overwrite secrets, or claim a research draft is final
without explicit user authorization.
