---
name: domain-pack-research
description: Research an organization and create a deep, reviewable PR Intelligence domain-pack draft with linked competitors, categories, sources, precision rules, and editorial context.
---

# Research-backed domain-pack drafting

Use this skill when a user wants to initialize or substantially improve PR
Intelligence configuration from a company name, industry, website, or existing
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

Use [the pack-depth standard](references/pack-depth.md) before proposing scope
or writing. It defines the required links between monitoring scope, collection,
precision, PR handling, and editorial output. Treat it as a quality bar, not a
template to copy: never transfer another organization's names, facts, sources,
or editorial judgments into the new pack.

## Draft in three reviewable passes

1. **Monitoring scope** — propose a company identity map, 6–12 competitors,
   4–7 categories, priority regions, 3–8 monitoring questions, and relevant
   cross-cutting themes (for example supply chain, regulation, or platform
   dependencies). Map every competitor to categories and state why each
   category matters to the organization. Include sources and wait for approval.
2. **Collection and precision design** — for each approved category, propose
   Korean and English keywords, precise Google News queries, and high-quality
   specialist, official-newsroom, domestic, and regulatory sources as relevant.
   Give each source/query a purpose, locale, priority, and category coverage.
   Verify RSS URLs before recording them. Design strong exclusions, ordinary
   exclusions, exceptions, and ambiguous-alias safeguards from observed false
   positives; do not add generic noise lists by habit.
3. **Editorial and PR context** — draft positioning, strategic relationships,
   dated key events with provenance, competitor baselines, separate PR query
   lanes for domestic and international coverage, topic diversity keys, and
   audience-specific sensitivity treatment. Draft good/bad insight examples
   only from supported facts; every generated example remains editorial-review
   material, not an internal fact.

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
purpose, key-event provenance, and cross-file category references complete.
Run the cross-file checks in the pack-depth standard before calling the draft
ready for approval.

## Verification and handoff

After writing, parse every YAML, run `python3 -m prmonitor doctor --strict`, and
perform a no-email dry run. Report changed files, the evidence ledger, candidate
items awaiting approval, collection coverage, and the next command:
`market-brief` or `self-brief`.

Do not enable delivery, overwrite secrets, or claim a research draft is final
without explicit user authorization.
