# Domain-pack depth standard

Use this reference when drafting or reviewing a domain pack. It captures the
structure of a high-quality operational pack without reusing another
organization's data.

## 1. Start with a connected monitoring model

The pack should explain not just what the company sells, but what can change a
decision for the company.

| Layer | Minimum useful content | Must connect to |
|---|---|---|
| Company identity | Official Korean/English names, tested aliases, products, positioning | PR queries, branding, boost terms |
| Competitor map | Material competitors, aliases, category memberships | Headlines, sources, boost terms |
| Category map | Description, priority, self relevance, key players, watch terms, rationale where indirect | Render order, source coverage, queries |
| Cross-cutting themes | Dependencies that cross categories: platform, supply chain, regulation, channel, financing, geography | Queries and editorial context |
| Audience | Decision makers, purpose, frequency, desired length, sensitivity tolerance | Pipelines and delivery groups |

Aim for enough variety to capture the market, not a fixed count. In a complex
market, 8–15 competitors and 5–8 categories is often a useful starting range.
Smaller markets may need fewer. Do not add companies solely to reach a number.

### Alias quality

Use aliases that have been checked against real coverage. Record Korean,
English, legal, product, and commonly used names when useful. Avoid short or
ambiguous aliases unless a reliable discriminator exists; a short abbreviation
that matches unrelated companies creates worse monitoring than omitting it.

## 2. Design collection as a portfolio, not a list

For a market with global activity, cover distinct lanes where available:

1. Specialist international reporting for early market signals.
2. Competitor and key-partner newsrooms for primary announcements.
3. Purpose-built global news queries for companies or themes that lack feeds.
4. Domestic reporting for the company, local regulation, and local context.
5. Government or regulator sources for policy, trade, safety, or compliance.

Every source/query needs a reason: its category coverage, geography/language,
priority, and why it is not redundant. Queries should target a monitoring
question—not merely repeat a generic industry noun—and should carry a locale,
time window, and a purpose note. Verify feeds and newsroom URLs; mark a source
that cannot be verified as a candidate rather than silently including it.

For each high-priority category, show at least one credible collection path.
For globally exposed organizations, include both international and domestic
coverage unless the user says otherwise.

## 3. Build precision before volume

Start broad enough to avoid blind spots, then document how the pack separates
useful signals from predictable noise.

- **Boost terms:** organization aliases, distinctive competitors, product and
  technology terms in relevant languages.
- **Strong exclusions:** content that should never enter that briefing, even
  when a broad term matches.
- **Ordinary exclusions and exceptions:** recurring but conditional noise, with
  explicit exceptions that protect legitimate market coverage.
- **Stakeholder boosts:** only for a verified investor, customer, supplier, or
  strategic relationship; include its unrelated-topic noise guard.
- **Low-signal patterns:** recurring event attendance, market-report promotion,
  or similar coverage that is not material unless additional evidence exists.
- **Sensitivity policy:** legal, crisis, negative, and market-commentary
  articles may need different treatment for PR operators, executives, and
  broad distribution.

Treat every precision rule as a hypothesis from evidence or user knowledge.
Do not carry a false-positive rule from another industry without revalidating it.

## 4. Keep market intelligence and PR monitoring distinct

The market brief needs categories, external sources, and comparative context.
The PR brief needs accurate self-identification and reputation handling.

For the PR lane, include:

- Tested self aliases plus distinct Korean and international search queries.
- Topic-diversity keys so one recurring topic cannot fill the entire report.
- Positive, negative, and stock/market-commentary lexicons appropriate to the
  organization's media environment.
- Media-name and domain mappings when bylines or republished articles are a
  known problem.

Do not use market-brief exclusions to erase needed self-coverage. Let the
audience-specific sensitivity policy decide what is labelled, held, or omitted.

## 5. Make editorial context auditable

Company positioning, strategic relationships, key events, and competitor
baselines can sharpen implications, but they require a source URL and an
as-of date. Keep uncertain items out of factual context until approved.

`prompt-examples.yaml` should teach a decision boundary, not a slogan style:

- A good example ties an observable external fact to a supported company
  context and stops at the evidence boundary.
- A bad example names the failure mode: unsupported inference, fabricated
  number, false analogy, abstract buzzword, or generic truism.

When no approved internal context exists, use empty slots or clearly marked
drafts. Never simulate internal metrics merely to make the examples look deep.

## 6. Cross-file readiness check

Before YAML is written or approved, confirm:

- Every competitor category exists in `categories.yaml` and the company profile.
- Every rendered category has a label, subdued color, order, and at least one
  collection/keyword path.
- Every source category and query purpose maps to a known category or a named
  cross-cutting theme.
- Company aliases agree across `company-profile.yaml`, `branding.yaml`,
  `keywords.yaml`, and `pr-queries.yaml` where relevant.
- Pipeline recipients, subjects, and delivery groups name the intended
  audience and do not contain inherited example organization data.
- Delivery credentials are empty samples or user-provided secrets only.
- YAML parses; `doctor --strict` and a no-email dry run pass after writing.

If any link is missing, report it as a specific draft gap instead of filling it
with invented content.
