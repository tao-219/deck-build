# Visual Types — Claim Type → Slide Archetype → Layout Capability

This is the LLM-author-facing vocabulary. The orchestrator picks a visual type based on what the slide is trying to argue. The renderer maps the visual type to a layout capability, and the reference deck's profile maps the capability to a specific layout index.

```
claim_type  →  slide_archetype  →  layout_capability  →  layout_index
(LLM)          (template-agnostic)  (DNA contract)        (specific deck)
```

## Quick selection guide

| If the slide is arguing... | Pick this visual type |
|---|---|
| A single conclusion / headline number | `hero-statement` or `data-contrast` |
| A multi-step process or roadmap | `process-N-phase` (N=2-5) or `timeline-horizontal` |
| Where today's work fits in a multi-stage program with a downstream gate | `stage-flow-with-signoff` (recipe) |
| A comparison between options | `comparison-N` (N=2-5) |
| Comparing 3+ parallel things where ONE is the focus and others are context | `spotlight-comparison-columns` (recipe) |
| Agenda / session overview that needs purpose + structured agenda + desired outcome | `two-col-overview-with-subcallout` (recipe) |
| Coverage / capability table across N rows × M jurisdictions with tier indicators | `tiered-region-coverage-table` (recipe) |
| A single recommendation that needs to land HARD with supporting evidence | `recommendation-hero` (recipe) |
| Current process vs proposed process with the delta called out | `before-after-process` (recipe) |
| 2×2 plot of items by likelihood × impact (or any two dimensions) | `risk-heatmap` (recipe) |
| N items × M target columns with status badges (mapped/partial/gap) | `mapping-table-with-status` (recipe) |
| A list of supporting evidence | `bullets` or `cards-N` |
| A breakdown of components | `framework` or `pyramid` |
| A quantitative trend | `chart-line` or `chart-bar` |
| A trade-off between dimensions | `chart-quadrant` or `chart-scatter` |
| A contribution analysis | `chart-waterfall` |
| A two-dimensional segmentation | `chart-marimekko` |
| A severity / status assessment | `harvey-balls` |
| A direct quote from a stakeholder | `quote-hero` |
| An explanatory narrative with visual | `content-with-image` |
| A section transition / divider | `section-divider` |
| The deck cover or closing | `title-cover` / `closing` |

The "(recipe)" tag signals an archetype with a full anatomy/color/icon recipe in `design-archetypes.md`. Prefer recipe archetypes over generic visual types when both fit — recipes carry richer hierarchy and visual language.

## Visual types in detail

### Narrative archetypes

- `hero-statement` — single declarative statement, large type, minimal supporting context. Use for opening punchlines, recommendations, conclusions.
- `data-contrast` — one or two big numbers (KPIs) with brief annotation. Use when one or two metrics carry the entire slide.
- `quote-hero` — verbatim stakeholder quote with attribution. Use sparingly; reserve for stakeholder validation.

### Process archetypes

- `process-2-phase`, `process-3-phase`, `process-4-phase`, `process-5-phase` — sequential boxes/arrows. Use for roadmaps, methodologies, workflow steps.
- `timeline-horizontal` — date-anchored events on a horizontal axis. Use for project plans with specific dates.

### Comparison archetypes

- `comparison-2`, `comparison-3`, `comparison-4`, `comparison-5` — side-by-side columns. Use for option evaluation, before/after, vendor comparison.
- `comparison-tables` — comparison rendered as a table (more attributes, less visual emphasis).

### Evidence archetypes

- `bullets` — flat indented list. Default fallback when nothing more visual fits.
- `cards-2`, `cards-3`, `cards-4`, `cards-5` — content blocks of equal weight. Use for parallel-structured supporting points.
- `content-with-image` — narrative text + supporting visual. Use when the visual contextualizes the text.

### Structural archetypes

- `framework` — multi-component diagram (e.g. 2x2 matrix, pyramid, layered). Use for conceptual models.
- `pyramid` — hierarchical pyramid with N levels. Use for strategic frameworks (Maslow-style).

### Chart archetypes (delegate to deck-charts skill)

- `chart-bar` — categorical comparison (vertical or horizontal bars).
- `chart-line` — trend over time.
- `chart-quadrant` — 2x2 positioning.
- `chart-scatter` — two-dimensional plot.
- `chart-waterfall` — contribution to a total. **Specialist; deck-charts skill handles construction.**
- `chart-marimekko` — two-dimensional segmentation. **Specialist.**
- `harvey-balls` — severity assessment with filled-circle glyphs. **Specialist.**

### Structural slides

- `title-cover` — deck cover with title, subtitle, date, presenter.
- `section-divider` — between-section transition. Big section title, optional subtitle.
- `closing` — closing slide (thank you, contacts, next steps).
- `contact` — explicit contact details (rare).

## Selection rules

1. **Always pick the most semantically specific type.** `hero-statement` beats `bullets` if a single conclusion will carry the slide. A recipe archetype (e.g. `spotlight-comparison-columns`) beats a generic one (`comparison-3`) whenever the recipe's pattern fits.
2. **One idea per slide.** If the content has two ideas, split into two slides — don't compress with `comparison-2`.
3. **Charts are last resort for narrative.** A chart shows data; the action title states the conclusion. Don't use a chart when the conclusion needs words to explain.
4. **`bullets` is the fallback.** If no other visual type fits, use `bullets` — but reconsider whether the slide can be rewritten as a `framework` or `cards-N`.
5. **Spotlight beats three-state when status isn't time-sequenced.** If you're tempted to color one column "CURRENT" and others "LATER" but the others are scope qualifiers (not future phases), use `spotlight-comparison-columns` instead.
6. **Block-list beats time-boxed table for executive audiences.** Numbered agenda blocks (`two-col-overview-with-subcallout`) for execs; T+0/T+7 tables for ops reviews.

## Capability fallback

If the reference deck doesn't have a layout matching the desired visual type, the renderer falls back via `slide_archetype → layout_capability`. The DNA's `capabilities.body_counts_available` field tells the agent which counts are supported. If the user asks for `cards-7` and the deck only supports `cards-2/3/4/5`, the agent must either split the slide (preferred) or fall back to `bullets`.

## Anti-patterns

- Choosing `cards-5` because the content has 5 items, when those 5 items are actually 5 unrelated facts (use multiple slides instead).
- `framework` when no real framework exists — just a labeled diagram for show.
- `comparison-N` when the dimensions being compared aren't apples-to-apples.
- `chart-bar` when there's no quantitative comparison being made.
- `process-N-phase` when steps aren't actually sequential.
