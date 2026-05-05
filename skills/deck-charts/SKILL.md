---
name: deck-charts
description: STUB — not yet implemented. Will construct specialist consulting charts (Waterfall, Marimekko, Harvey Balls) as native PowerPoint shape compositions. Each chart will return OOXML shape XML that the renderer injects into a slide. Do NOT invoke until scripts at `${CLAUDE_PLUGIN_ROOT}/skills/deck-charts/scripts/` exist; the spec below is the implementation contract, not working code.
---

# Deck Charts

> **Status: STUB — not yet implemented.** Scripts referenced below (`waterfall.py`, `marimekko.py`, `harvey_balls.py`) do NOT exist yet. This file is the implementation spec for the future build (planned via `/create-plugin` workflow). Do NOT invoke this skill from `deck-orchestrator` or directly until the scripts are present — Claude will fail trying to run them.

Specialist consulting charts that PptxGenJS and python-pptx can't render natively. Each will be constructed from primitive shapes so they remain fully editable.

## When to use (post-implementation)

- Invoked by deck-render when a slide spec calls for `chart-waterfall`, `chart-marimekko`, or `harvey-balls`
- Direct user request for one of these chart types
- **Currently: do not invoke. Stub.**

## Inputs

- `inputs/data.json` — structured chart data (schema per chart type)
- `inputs/style.json` — color/font from reference DNA

## Outputs

- `outputs/chart.xml` — shape composition XML to inject into a slide
- `outputs/chart-spec.json` — the resolved spec (for QA cross-check)

## Charts

### Waterfall

Script: `scripts/waterfall.py`

Visualizes drivers of change between two periods (e.g., revenue bridge).

Construction:
- Stacked-bar approach with invisible "base" series
- `BaseValue_n = BaseValue_(n-1) + Value_(n-1)` for positive growth; subtract for declines
- Connectors (line shapes) between top/bottom of adjacent bars
- Color coding: distinct color for starting/ending totals; separate palette for positive vs negative deltas (from reference DNA)

Data schema:
```json
{
  "categories": ["Start", "Δ Volume", "Δ Price", "Δ Mix", "End"],
  "values": [100, 15, -8, 5, 112],
  "totals": [0, 4],  // indices that are full bars (start + end), not deltas
  "labels": {"format": "{:+.0f}", "show_value_in_bar": true}
}
```

### Marimekko (Mekko)

Script: `scripts/marimekko.py`

Two-dimensional segmentation: width encodes one dimension, height encodes another.

Construction:
1. Calculate column widths: `Width_i = Value_(category,i) / Σ Value_categories`
2. Calculate segment heights within each column: `Height_(j,i) = Value_(segment,j,i) / Value_(category,i)`
3. Map x-position by summing widths of preceding columns
4. Insert Rectangle shapes for every segment with text labels

Data schema:
```json
{
  "row_labels": ["Customer A", "Customer B", "Customer C"],
  "column_labels": ["Region 1", "Region 2", "Region 3"],
  "values": [
    [40, 20, 10],  // Region 1: A=40, B=20, C=10
    [25, 30, 15],  // Region 2
    [10, 5, 5]     // Region 3
  ]
}
```

### Harvey Balls

Script: `scripts/harvey_balls.py`

Filled-circle severity glyphs: ○ ◔ ◑ ◕ ●

Construction:
- Five preset glyphs corresponding to severity levels 0/25/50/75/100%
- Implemented as filled arc shapes (more reliable than Unicode glyphs across renderers)
- Color from reference DNA primary

Data schema:
```json
{
  "rows": ["Criterion 1", "Criterion 2", ...],
  "columns": ["Option A", "Option B", ...],
  "scores": [
    [0.0, 0.5, 1.0],
    [0.25, 0.75, 0.5]
  ]
}
```

## Editability requirement

Every chart must be composed of native PowerPoint shapes (autoshapes, text boxes, lines). Never:
- Embed as a raster image
- Embed as an SVG (PowerPoint renders SVG inconsistently)
- Use a chart object (those use a different XML namespace and don't survive deep edits well)

The user must be able to open the slide in PowerPoint and resize, recolor, or relabel any element.

## Hard rules

- All colors from reference DNA only.
- Text labels in body font from reference DNA.
- Footnote source line auto-included if `data.json.source` field present.
