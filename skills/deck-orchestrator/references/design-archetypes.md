# Design Archetypes — Visual Recipes for Consultancy-Grade Slides

The orchestrator picks a `slide_archetype` based on what the slide is arguing (see `visual-types.md` for the claim-type mapping). This file is the **recipe book**: for each archetype it specifies anatomy, color discipline, typography, icon usage, and an exemplar so the renderer has unambiguous instructions.

Archetype IDs in this file are stable contracts. The plan emitted by the orchestrator references these IDs; the renderer (`deck-render`) implements them; QA (`deck-qa`) audits compliance against them.

## Why archetypes (not just layouts)

A reference deck's master/layout vocabulary is generic — `Title + Body + Object`. Two slides with the same layout signature can read very differently because the **archetype** (composition pattern, color logic, icon vocabulary) is the source of design quality, not the layout. The plugin must reason at the archetype level, not the placeholder level.

A correct archetype choice does three things:
1. **Frames the claim** — the visual structure mirrors the argument shape (sequence, comparison, focus, etc.).
2. **Establishes hierarchy** — the eye knows immediately where to land first, second, third.
3. **Applies a consistent visual language** — color and icon use carry meaning, not decoration.

## Selection meta-rules

When more than one archetype fits the claim type, prefer in this order:

1. **Spotlight over equal weighting** — if one element is the focus and the others are context, use a spotlight archetype (color contrast + focus marker), not an equal-weight comparison.
2. **Block-list over data-table for executive audiences** — agenda and progression slides for execs use numbered/lettered blocks; ops review and time-boxing use tables.
3. **Three-state visual language only when status is time-sequenced** — CURRENT/LATER/SIGN-OFF works for plan slides where boxes will move through states; do NOT use it for "scope vs out-of-scope" or for static comparisons (use spotlight instead).
4. **Sub-callout grid when the slide has a secondary takeaway** — agenda + desired-outcome, comparison + key-finding, framework + so-what — split as primary content + sub-callout below.

## Logic shape (argument fit)

An archetype is not only a *visual* choice — its composition implies an **argument shape**. A sequential/causal visual asserts a deductive chain; a parallel/comparison visual asserts an inductive set. Picking an archetype whose shape fights the argument (e.g. a parallel-comparison visual for a sequential, deductive point) is a logic defect, not just a style one.

| Archetype | Implied logic | Typical order basis | Why |
|---|---|---|---|
| `stage-flow-with-signoff` | **deductive** | time | stages run in sequence toward a gate |
| `before-after-process` | **deductive** | time | current → future is a causal / temporal progression |
| `process-2…5-phase`, `timeline-horizontal` | **deductive** | time | ordered steps |
| `spotlight-comparison-columns` | **inductive** | degree / structure | parallel things, one in focus |
| `comparison-2…5`, `cards-2…5` | **inductive** | degree / structure | parallel items of one class |
| `tiered-region-coverage-table`, `mapping-table-with-status` | **inductive** | structure | rows × destinations, all parallel |
| `two-col-overview-with-subcallout` | **inductive** | structure | agenda items are parallel |
| `recommendation-hero`, `hero-statement`, `data-contrast`, `quote-hero`, `risk-heatmap`, `framework`, `pyramid` | — (single claim / positioning) | n/a | no same-level grouping → no logic constraint |

**Enforced:** `scripts/logic_structure_check.py` carries this map (`ARCHETYPE_LOGIC`) and the deck-qa **Layer 5b** judge flags a slide whose archetype contradicts the `logic_type` of the pillar it supports (or its own `logic_type` override). Set a pillar's `logic_type` to match the argument, then pick an archetype whose shape agrees.

## Footer-clearance budget (renderer hard rule)

A 16:9 slide is 7.5" tall. Every reference deck has a footer band — the Manulife template uses ~6.95–7.30" for logo + page number + program name. **Renderers must reserve ≥0.30" clearance from the lowest content shape to y=6.95.**

Practical implication for each recipe:

- `stage-flow-with-signoff` — sign-off panel must terminate by y=6.65; source footer line at y=6.55 max.
- `two-col-overview-with-subcallout` — sub-callout caption text must terminate by y=6.65; if the caption is two lines tall (≈0.30"), start no later than y=6.35.
- `spotlight-comparison-columns` — dashed container must terminate by y=6.85; per-column footer panels are inside the container, so they automatically clear if the container does.
- `tiered-region-coverage-table` — table bottom row must terminate by y=6.55 (legend at top consumes ~0.30" so the table itself runs y=2.20–6.55 at most).

Heights and gaps for each recipe are tuned to honor these limits. **If you change a node count or text length, recheck the bottom-of-stack y-coordinate; never let it drift past the footer-clearance budget.**

---

## Archetype 1: `stage-flow-with-signoff`

**When to use:** Planning/orientation slide showing where the current work fits in a multi-stage program that culminates in a downstream gate (sign-off, approval, milestone).

**Layout signature:** `title:1_body:1` from a comparison layout (renderer uses raw shapes — placeholders cleared except title/footer/page-number).

**Anatomy** (16:9, 13.33 × 7.5 in):

```
[Action title — 2 tones: bold short claim + en-dash + normal-weight elaboration]

[Stage 1] → [Stage 2] → [Stage 3] → [Stage 4]              [SIGN-OFF panel]
   |                                                             ↑
   ├──────┬──────┬──────┬──────┐                                 |
[WS 1] [WS 2] [WS 3] [WS 4] [Final WS] - - dashed connector - - ┘

[Footer source line]
```

**Color discipline (three-state):**
- **CURRENT** (active stage / today's workshop): primary brand color fill, white text.
- **LATER** (upcoming stages / workshops): light grey fill (`#F2F2F4`), border `#D9DADF`, dark text.
- **SIGN-OFF** (gate panel): cream fill (`#FFF4E0`), accent border (`#F49600` or palette accent), dark text. Header band uses the accent color.
- **Connector** to sign-off: dashed line in the accent color with arrowhead.

**Typography:**
- Stage / workshop labels: bold uppercase 11pt.
- Stage / workshop body: 11pt regular, italic for date or context-in-parens.
- Sign-off header: bold 10pt (size down if the panel is narrow — wrapping looks sloppy).
- Sign-off body: 9pt regular with bold sub-heads.

**Icon usage:** none.

**Title pattern:** action title naming the slide's role in the sequence + what the downstream gate decides. Example: `Workshop 1 of 4 within Stage 1 – together these workshops inform Stage 1 sign-off on the conceptual CRR risk factor list per jurisdiction and the number of models decision for Canada`.

**Common pitfalls:**
- WORKSHOP labels wrapping to two lines because the box is too narrow — shorten the label or widen the box (prefer widening; consistency across the row matters).
- Sign-off panel positioned as a tall right-side column — looks heavy; prefer compact box at lower-right with the connector pointing into it.
- Connector too thin or wrong color — use ≥1.5pt dashed in the accent color.

---

## Archetype 2: `two-col-overview-with-subcallout`

**When to use:** Agenda, session overview, or kick-off slides that need to show (a) narrative purpose & objectives, (b) a structured agenda, AND (c) the desired outcome / success criteria for the session.

**Layout signature:** `title:1_body:2` (two-column layout), with shapes added below for the sub-callout grid.

**Anatomy:**

```
[Action title]

  [Section header: Session Overview]   |   [Section header: Agenda]
                                       |
  Purpose                              |   1 │ [Agenda item 1]
  [paragraph — 2-4 lines]              |
                                       |   2 │ [Agenda item 2]
  Objectives                           |
  • [bullet 1]                         |   3 │ [Agenda item 3]
  • [bullet 2]                         |
  • [bullet 3]                         |   4 │ [Agenda item 4]
                                       |
                                       |   ────────────────────
                                       |   [Section header: Desired Outcome]
                                       |
                                       |   [icon]      [icon]
                                       |   [Label 1]   [Label 2]
                                       |   [caption]   [caption]
```

**Color discipline:**
- Section headers (`Session Overview`, `Agenda`, `Desired Outcome`): centered, bold, primary brand color, 14pt.
- Numbered agenda blocks: large numeral (32pt bold, primary brand color) + thin vertical accent bar (4pt wide, primary brand color, gradient lighter for blocks lower in the list — optional) + topic text 14pt regular.
- Left column body: dark text on light cream background panel (dashed border in primary brand color for the panel).
- Sub-callout grid: icons in primary brand color, 14pt bold labels, 11pt regular captions.

**Typography:**
- Section headers: 14pt bold, primary color, centered above each column / sub-block.
- "Purpose" / "Objectives" sub-heads: 12pt bold, dark.
- Numbered agenda: numeral 32pt bold (primary color), topic 14pt regular (dark).
- Sub-callout label: 14pt bold, dark.
- Sub-callout caption: 11pt regular, muted dark grey.

**Icon usage:** REQUIRED in the sub-callout grid — typically 2 or 3 icons matching the desired outcomes. Common picks:
- Target / bullseye → "Clarity", "Focus", "Alignment on outcome"
- Network / people-connected → "Alignment", "Stakeholder agreement"
- Gear → "Process", "Operationalization"
- Magnifying glass → "Diagnosis", "Discovery"
- Compass → "Direction", "Navigation"
- Check / shield → "Sign-off", "Approval"

**Title pattern:** action title naming the session's outcome — what the session will produce. Example: `Today: identify Canada CRR pain points and assess SAI built-in coverage to inform Workshop 2`. NOT `Today's Agenda` (topic title — banned).

**Common pitfalls:**
- Using a time-boxed table (T+0 / T+7 / T+20...) for an executive audience — that's an ops-review pattern; for execs use numbered blocks.
- Forgetting the sub-callout grid — without it the slide doesn't answer "so what does success look like?".
- Sub-callout icons that are decorative (smiley, lightbulb without context) — pick icons that name the outcome literally.
- More than 4 numbered agenda items — split the slide or merge items.

---

## Archetype 3: `spotlight-comparison-columns`

**When to use:** Comparing 3+ parallel things (regions, products, segments, scenarios) where ONE is the focus of the conversation and the others are context.

**Layout signature:** `title:1_body:3` or `title:1_body:4`, with a dashed-border container around the comparison area and a focus marker above the spotlight column.

**Anatomy:**

```
[Action title — 2 tones]

                                  [Globe icon] Global Context
        ┌─ Focus marker ──┐
        [target icon]
        Focus of Today's
        Discussion
   ┌────┴─────────┐  ┌──────────────┐  ┌──────────────┐
   │ Focus col    │  │ Context col1 │  │ Context col2 │
   │ (Qualifier)  │  │ (Qualifier)  │  │ (Qualifier)  │
   ├──────────────┤  ├──────────────┤  ├──────────────┤
   │ [Step 1]     │  │ [Step 1]     │  │ [Step 1]     │
   │      ↓       │  │      ↓       │  │      ↓       │
   │ [Step 2]     │  │ [Step 2]     │  │ [Step 2]     │
   │      ↓       │  │      ↓       │  │      ↓       │
   │ [Step 3]     │  │ [Step 3]     │  │ [Step 3]     │
   │      ↓       │  │      ↓       │  │      ↓       │
   │ [Step 4]     │  │ [Step 4]     │  │ [Step 4]     │
   ├──────────────┤  ├──────────────┤  ├──────────────┤
   │ [Footer:     │  │ [Footer:     │  │ [Footer:     │
   │  scale /     │  │  scale /     │  │  scale /     │
   │  rating /    │  │  rating /    │  │  rating /    │
   │  caveat]     │  │  caveat]     │  │  caveat]     │
   └──────────────┘  └──────────────┘  └──────────────┘
   └─────────── dashed container border ──────────────┘

[Footer source line — optional]
```

**Color discipline:**
- **Focus column header**: primary brand color fill, white bold text.
- **Focus column boxes**: primary brand color fill, white text.
- **Context column headers**: medium grey fill (`#8E90A2`), white bold text — OR same medium grey as text only on white fill (see Manulife reference).
- **Context column boxes**: medium grey fill (`#8E90A2`), white text.
- **Container**: light grey fill (`#F8F8FA`) with dashed border in primary brand color (focus side) blending to grey (context side) — or single dashed border in muted grey if simpler.
- **Focus marker box** (above focus column): no fill, target icon in primary brand color, label in primary brand color bold.
- **Global context label** (above context columns): no fill, globe icon in muted grey, label in muted grey bold.

**Typography:**
- Column headers: 16pt bold, with scope qualifier in parens (`(AML Manager)`, `(No CRR Model)`) on a second line if needed — keeps headers readable.
- Step boxes: 12-14pt bold for label, 10pt regular for sub-text.
- Footer panels: 9-10pt regular, italic for caveats.
- Focus marker: 14pt bold + 24pt icon.

**Icon usage:**
- **Target / bullseye** above the focus column to indicate "Focus of Today's Discussion".
- **Globe** above the context columns to indicate "Global Context" (or compass / map-pin if globe is overused).
- Icons should match in size and stroke weight.

**Title pattern:** action title with comparative summary using en-dash and qualifier list. Example: `Three regional CRR schemes operate today – Canada 3-tier point based, and APAC tiered (varies by jurisdiction), US trigger-based without CRR`.

**Inline scope qualifier convention:** when a header needs context, append in parens: `Header (qualifier)` — e.g., `Canada Market (AML Manager)`. Use this NOT as part of the title but as part of column / row labels to embed context where it lives.

**Common pitfalls:**
- Using three-state language (CURRENT/LATER) instead of spotlight (focus/context) — wrong: implies the context columns will become active later when in fact they're scope qualifiers, not phases.
- Focus marker missing — without it, the eye doesn't know where to land first.
- Context columns identical in color to focus — destroys hierarchy.
- Footer scale strip running across all columns horizontally — visually disconnects the scale from its column. Embed each scale inside its column's footer panel instead.

---

## Archetype 4: `tiered-region-coverage-table`

**When to use:** Dense data table comparing N rows (factors, attributes, line items) across M jurisdictions (regions, segments, vendors) with a tier indicator in each cell.

**Layout signature:** `title:1_body:1` with a table shape covering most of the body area + legend strip above.

**Anatomy:**

```
[Action title — 2 tones]

[Legend: ● High coverage  ◐ Partial  ○ Gap   |   ✓ In OOTB  ✗ Custom needed]

┌──────────────────┬─────────┬─────────┬─────────┐
│ Risk factor      │ Canada  │ APAC    │ US      │
├──────────────────┼─────────┼─────────┼─────────┤
│ Customer type    │   ●     │   ●     │   ◐     │
│ Geography        │   ●     │   ◐     │   ○     │
│ Product          │   ●     │   ●     │   N/A   │
│ ...              │   ...   │   ...   │   ...   │
└──────────────────┴─────────┴─────────┴─────────┘

[Sub-block (optional): Notable [items] not in [reference set]
 [list] ]

[Footer source line]
```

**Color discipline:**
- Header row: dark fill (`#262626`), white bold text.
- Tier badges: small filled glyphs (Harvey-ball style) — ● green = high, ◐ amber = partial, ○ red = gap.
- Alternating row shading optional (`#F8F8FA` even rows) for tables >8 rows.
- Total row (if any): primary brand color fill, white bold text.
- N/A cells: italic muted grey, no badge.

**Typography:**
- Header row: 11pt bold uppercase.
- Body cells: 10pt regular.
- Sub-block: 11pt regular with 12pt bold heading.

**Icon usage:** tier badges only. No decorative icons.

**Title pattern:** action title summarizing coverage state — number of gaps, biggest gap region, or coverage threshold. Example: `SAI OOTB covers 70% of AML Manager risk factors — six factors require custom configuration, concentrated in Geography and Product`.

**Common pitfalls:**
- Body text under the table that restates row counts — that's the table's job; the body should interpret (e.g., "concentrated in Geography").
- Tier badges using only color (no shape) — fails accessibility; always pair color with shape (filled / partial / empty circle).
- Missing legend — every cell with a badge needs a legend above the table.

---

## Archetype 5: `recommendation-hero`

**When to use:** A slide whose entire job is to land ONE recommendation, with 2–3 supporting evidence cards beneath.

**Layout signature:** `title:1_body:1` + freeform shapes for the hero band and evidence cards.

**Anatomy:**

```
[Action title — two-tone: "Adopt SAI CDD on Stage 1" – "compresses timeline by 4 months and aligns to OOTB inventory"]

  ┌──────────────────────────────────────────────────────────────────┐
  │ HERO BAND (primary brand color, white text)                       │
  │   "Adopt the SAI CDD module configuration in Stage 1"             │
  │   24–28pt bold, centered                                          │
  └──────────────────────────────────────────────────────────────────┘

  Why now:                                                              ← optional sub-head 14pt bold

  ┌──────────────────┐ ┌──────────────────┐ ┌──────────────────┐
  │ [icon]           │ │ [icon]           │ │ [icon]           │
  │ Evidence card 1  │ │ Evidence card 2  │ │ Evidence card 3  │
  │ • short bullet   │ │ • short bullet   │ │ • short bullet   │
  │ • short bullet   │ │ • short bullet   │ │ • short bullet   │
  │                  │ │                  │ │                  │
  │ Source: ___      │ │ Source: ___      │ │ Source: ___      │
  └──────────────────┘ └──────────────────┘ └──────────────────┘
```

**Color discipline:**
- Hero band: primary brand color fill, white text, no border. ~1.0–1.2" tall.
- Evidence cards: white fill, primary-color thin border (1pt), or alternating border colors per card.
- Card icons in primary brand color.
- "Why now" sub-head in dark text, primary-colored thin underline (NOT a decorative line under the title — only here as a section bridge).

**Typography:**
- Hero band text: 24–28pt bold centered.
- Sub-head: 14pt bold.
- Card titles: 13pt bold.
- Card bullets: 11pt regular.
- Source line: 9pt italic muted.

**Icon usage:** REQUIRED at top of each evidence card. Pick icons that name the evidence dimension (lightning = speed, gear = ops, check = compliance, magnifier = diagnostic, network = alignment, target = outcome).

**Title pattern:** action title that names the recommendation in the bold half and the chief reason in the normal-weight half. Example: `**Adopt SAI CDD on Stage 1** – compresses timeline by 4 months and aligns to OOTB risk-factor inventory`.

**Common pitfalls:**
- Hero band as a tiny banner (looks decorative). Make it the dominant visual element — at least 12% of slide height.
- More than 3 evidence cards — split into two slides.
- Evidence cards with paragraphs of text — each card should be 2–4 short bullets max.

---

## Archetype 6: `before-after-process`

**When to use:** Comparing CURRENT process flow vs PROPOSED process flow, with the delta or improvement called out explicitly between them.

**Layout signature:** `title:1_body:2` (two columns) with a center delta callout overlapping both columns visually.

**Anatomy:**

```
[Action title — two-tone]

  CURRENT (grey label, left)              FUTURE (green label, right)

  ┌──────────────┐                              ┌──────────────┐
  │ Step 1 grey  │                              │ Step 1 green │
  └──────┬───────┘                              └──────┬───────┘
         ↓               ┌─────────────┐               ↓
  ┌──────┴───────┐       │  DELTA      │        ┌──────┴───────┐
  │ Step 2 grey  │       │  −4 months  │        │ Step 2 green │
  └──────┬───────┘       │  +12% alert │        └──────┬───────┘
         ↓               │  precision  │               ↓
  ┌──────┴───────┐       └─────────────┘        ┌──────┴───────┐
  │ Step 3 grey  │                              │ Step 3 green │
  └──────┬───────┘                              └──────┬───────┘
         ↓                                             ↓
  ┌──────┴───────┐                              ┌──────┴───────┐
  │ Outcome grey │                              │ Outcome green│
  └──────────────┘                              └──────────────┘

  [Source footer]
```

**Color discipline:**
- CURRENT column header & boxes: medium grey (`#8E90A2` for header, `#9C9FAE` for box fill) with white text.
- FUTURE column header & boxes: primary brand color with white text.
- DELTA callout: cream fill (`#FFF4E0`), accent border (`#F49600`), accent text. Sits in the visual gutter between columns.
- Connector arrows: matching column color.

**Typography:**
- Column headers: 16pt bold.
- Step labels: 12–13pt bold, white on column-color fill.
- DELTA callout: 11pt bold for the metric, 9pt regular for the label.

**Icon usage:** none in the columns. Optional small directional arrow in the DELTA callout pointing right (CURRENT → FUTURE).

**Title pattern:** `**[change verb] [process]** – delta in time/quality/cost terms`. Example: `**Re-platform CRR onto SAI CDD** – cuts implementation from 9 months to 5 and aligns to OOTB factor library`.

**Common pitfalls:**
- DELTA callout missing or buried — without it, this archetype is just two parallel lists.
- Different number of steps in CURRENT vs FUTURE — visually misleading; either pad with "n/a" boxes or restructure.
- Too many steps (>5 per column) — split into multiple before-after slides per process domain.

---

## Archetype 7: `risk-heatmap`

**When to use:** Plotting items on a 2×2 (likelihood × impact, severity × velocity, etc.) with each item as a labeled dot. Exec audiences for risk reviews.

**Layout signature:** `title:1_body:1` with axis labels, gridded 2×2 fills, and freeform dots + labels.

**Anatomy:**

```
[Action title — two-tone, e.g. "Three risks land in the High/High quadrant – remediation by June required"]

           Low impact          ← X-axis →           High impact
           ┌─────────────────┬─────────────────┐
  High     │ ●Item A         │ ●Item B  ●Item C │  ← upper-right = critical
  likely   │ light yellow    │ red             │
   ↑       ├─────────────────┼─────────────────┤
   |       │ ●Item D         │ ●Item E         │
  Low      │ light grey      │ amber           │
  likely   └─────────────────┴─────────────────┘

  [Legend or footer key]
```

**Color discipline:**
- Quadrant fills (low contrast — these are background): bottom-left = light grey, bottom-right = light amber, top-left = light yellow, top-right = light red.
- Dots: primary brand color for items in the focus quadrant; muted grey for items in non-focus quadrants. (Some teams prefer all-same-color dots and let position carry the severity — pick one convention and stick with it across slides.)
- Item labels: dark text, 10pt regular, positioned to NOT overlap dots from other items.
- Axis labels: 11pt bold, dark grey.

**Typography:**
- Axis labels: 11pt bold uppercase.
- Item labels: 10pt regular.
- Quadrant labels (if shown): 9pt italic muted in quadrant corners.

**Icon usage:** dots ARE the icons. No additional icons needed. Optional severity badges next to dots (●●● = critical, ●● = high, ● = medium) as a secondary encoding.

**Title pattern:** action title that summarizes the heatmap's conclusion — which quadrant has the most items, what action is implied. Example: `**Three risks land in High/High** – Geography mismatch, vendor SLA gap, and code-review backlog need remediation by June`.

**Common pitfalls:**
- Items plotted with overlapping dots — if two items share a position, offset slightly and use a connector line to a single label.
- Quadrant fills too saturated — overpowers the dots; use light tints only.
- Missing axis labels — readers can't interpret position; always label both axes.
- More than 8 items — heatmap becomes unreadable; split or aggregate.

---

## Archetype 8: `mapping-table-with-status`

**When to use:** Comparing N items (current state, our system, requirements) against M parallel destinations (target system, vendor OOTB, implementation), with a status indicator per row showing the mapping outcome (mapped, partial, gap). Universal in consulting work — current-vs-future, requirement-vs-implementation, our-system-vs-vendor.

**Layout signature:** `title:1_body:1` with a custom-built table (rectangles, not the python-pptx table object — gives full control over status badges, category grouping, alternating row shading).

**Anatomy:**

```
[Action title — two-tone: "Of N rows: X mapped, Y partial, Z need custom"]

[Optional: legend row — ✓ Mapped  ◐ Partial  ○ Custom needed]

┌─────────────────────────┬──────────────────────┬──────────────────┬────┐
│ HEADER (dark fill)      │ Source label         │ Target label     │St. │
├─────────────────────────┼──────────────────────┼──────────────────┼────┤
│ CATEGORY 1 (pale fill)  │                      │                  │    │
│ ├ row 1 source val      │ row 1 target val     │ ─                │ ✓  │
│ ├ row 2 source val      │ row 2 target val     │ ─                │ ✓  │
│ └ row 3 source val      │ row 3 target val     │ ─                │ ◐  │
│                         │                      │                  │    │
│ CATEGORY 2 (pale fill)  │                      │                  │    │
│ ├ row 4 source val      │ row 4 target val     │ ─                │ ✓  │
│ └ row 5 source val      │ row 5 target val     │ ─                │ ○  │
│ ...                     │                      │                  │    │
└─────────────────────────┴──────────────────────┴──────────────────┴────┘

[Optional sub-block: "Notable [items] not in [reference set]: ..."]

[Footer source line]
```

**Color discipline:**
- Header row: dark fill (`text_dark` ≈ `#262626`), white bold text, ~0.35" tall.
- Category-grouping rows: pale brand-color fill (~10% tint of primary, e.g. `#E5F5EC` for Manulife green), bold dark text, ~0.30" tall.
- Body rows: alternating white / very-light-grey (`#F8F8FA`) for >5 rows.
- Status column cells:
  - ✓ Mapped: primary brand color fill, white bold text
  - ◐ Partial: amber/orange fill (`#F49600` or palette accent), white bold text
  - ○ Gap / Custom needed: muted grey fill (`#8E90A2`), white bold text
  - N/A: italic muted grey, no badge

**Typography:**
- Header: 11pt bold uppercase.
- Category rows: 11pt bold dark.
- Body cells: 10pt regular.
- Status badges: 11pt bold (single character or 1-2 letters).

**Auto-computed elements:**
- Headline subtitle in title: count statuses and emit `"Of N rows: X ✓ mapped, Y ◐ partial, Z ○ gap"` automatically.
- Row height: shrink to fit footer-clearance budget for archetype `mapping-table-with-status` (6.55"). If table would overflow, the renderer must reduce `ROW_H` (default 0.30") progressively until total height fits, OR split into a continuation block (for >25 rows).

**Inputs to the renderer:**
```python
mapping_table_with_status(slide, x, y, w, rows, *, status_col_w=0.45,
                          column_headers=("Source", "Target", "Status"),
                          column_widths=None, legend=True,
                          auto_headline_to_title=False)

# rows is a list of dicts:
[
  {"category": "Customer", "source": "Customer Type", "target": "OOTB.CustomerType", "status": "✓"},
  {"category": "Customer", "source": "Citizenship",   "target": "OOTB.Country",       "status": "◐"},
  {"category": "Geography","source": "Country of residence", "target": "OOTB.GeoRisk", "status": "✓"},
  {"category": "Geography","source": "Tax residency", "target": "(custom)",           "status": "○"},
  ...
]
```

**Title pattern:** action title summarizing coverage state. Examples:
- `**SAI OOTB covers 70% of AML Manager risk factors** – six factors require custom configuration, concentrated in Geography and Product`
- `**Of 19 risk factors mapped, 13 land in OOTB** – two require partial config, four need custom build`

**Common pitfalls:**
- Using the python-pptx Table object — limited control over per-cell fills and badge alignment. Always build from rectangles.
- Body text under the table that restates the row counts — that's the title's job. The body interprets ("concentrated in Geography").
- Status badges using only color (no shape) — fails accessibility; always pair color + glyph.
- Forgetting category grouping — without it, a 19-row table reads as undifferentiated noise.
- Row height too generous and table overflows the footer-clearance budget — the helper auto-shrinks ROW_H but only to a minimum; if rows >25, split into two slides.

---

## Future archetypes (not yet implemented)

These are placeholders — add the recipe when first needed:

- `quote-with-attribution-panel` — verbatim quote left, attribution and supporting context right.
- `decision-tree-narrative` — branching logic shown as a visual tree with annotated paths.
- `sankey-flow` — multi-stage flow with quantified band widths (specialist; deck-charts).
- `kpi-dashboard` — 4–6 KPI tiles with current value, target, trend sparkline.
- `roadmap-swimlanes` — workstream rows × time-period columns with milestone markers.

When a slide can't be served by an existing archetype, the orchestrator should propose a new one and ask the user before generating — don't fall back to `bullets`.
