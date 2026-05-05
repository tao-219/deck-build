---
name: deck-render
description: This skill should be used when the user asks to render slides to .pptx, build a slide from a structured spec, rebuild one slide in an existing deck, or apply an archetype recipe (stage-flow-with-signoff, two-col-overview-with-subcallout, spotlight-comparison-columns, tiered-region-coverage-table, recommendation-hero, before-after-process, risk-heatmap). Also invoked by deck-orchestrator after the slide plan is approved. Two paths — (a) thin-wrapper delegation to document-skills:pptx for layout-driven generation, (b) raw-shape construction via importable Python helpers in ${CLAUDE_PLUGIN_ROOT}/scripts/deck_helpers.py for archetype-driven slides where placeholder layouts can't carry the visual language.
---

# Deck Render

Materializes structured slide specs into editable .pptx files. Two paths depending on the archetype:

| Path | When | Mechanism |
|---|---|---|
| **Path A — Layout delegation** | The slide is well-served by a single layout from the reference deck (basic title-body, content-with-image, comparison-2/3) | Delegate to `document-skills:pptx` (install via `/plugin install document-skills@anthropic-agent-skills`) |
| **Path B — Raw shape construction** | The slide uses a recipe archetype from `design-archetypes.md` (stage-flow-with-signoff, spotlight-comparison-columns, two-col-overview-with-subcallout, tiered-region-coverage-table) | python-pptx primitives + the helper recipes in this skill |

Path B exists because reference decks rarely have layouts that match recipe archetypes pre-built — those are composed at render time from primitives.

## When to use

- Invoked by deck-orchestrator after a slide plan is approved.
- Standalone for one-off slide insertion (less common).

## Inputs

- `inputs/deck-plan.json` — structured spec from deck-orchestrator.
- `inputs/reference.pptx` — the reference deck to render INTO (provides theme + master).
- `inputs/reference-profile.json` — layout index → semantic name mapping (from deck-extract-dna).

## Outputs

- `outputs/deck.pptx` — final editable .pptx.

## Procedure

1. Verify `document-skills:pptx` skill is available. If not: fail with install instructions (Path A unusable — Path B still works).
2. Load `deck-plan.json`. For each slide, read `archetype` field.
3. **If archetype is a recipe archetype** (see `design-archetypes.md`): use Path B — construct via primitives + the helper recipes below.
4. **If archetype is a generic visual type**: use Path A — delegate to `document-skills:pptx` with the layout index resolved via the reference profile.
5. **Specialist charts** (Waterfall, Marimekko, Harvey Balls): invoke `deck-charts` skill first to produce shape-level XML; embed via Path B.
6. Save the output .pptx.

---

## Helper recipes (Path B) — importable Python module

The recipes below are implemented as an importable module at `${CLAUDE_PLUGIN_ROOT}/scripts/deck_helpers.py`. Import what you need and call directly — no copy-paste required.

```python
import sys
sys.path.insert(0, "${CLAUDE_PLUGIN_ROOT}/scripts")  # post-install
# For standalone use without plugin install:
# sys.path.insert(0, "/Users/taoli/projects/deck-build/scripts")
from deck_helpers import (
    # Palette + fonts (Manulife defaults — override via set_palette/set_fonts)
    PRIMARY, LATER_FILL, SIGNOFF_FILL, CONTEXT_GREY, TEXT_DARK, TEXT_MUTED, WHITE,
    FONT_HEADING, FONT_BODY,
    set_palette, set_fonts,
    # Recipe helpers
    two_tone_title, numbered_agenda_block, section_header,
    sub_callout_grid, spotlight_callout,
    # Icons
    target_icon, network_icon, globe_icon, gear_icon, magnifier_icon,
    check_icon, lightning_icon,
    # Strip discipline + connectors
    strip_shapes, replace_title, add_arrow, add_line,
    # Primitives
    add_rect, add_text_to_shape, add_paragraph, set_run,
    # Footer-clearance budget per archetype
    footer_clearance,
)
```

Adapt the palette to a non-Manulife reference deck:

```python
from pptx.dml.color import RGBColor
set_palette(
    primary=RGBColor(0x1E, 0x3A, 0x8A),     # navy for some other client
    context_grey=RGBColor(0x9A, 0xA0, 0xA6),
)
set_fonts(heading="Arial Black", body="Calibri")
```

For implementation details on each recipe (constants, signatures, internal logic), see [`references/helper-internals.md`](references/helper-internals.md). The module at `${CLAUDE_PLUGIN_ROOT}/scripts/deck_helpers.py` is the source of truth — never copy from `helper-internals.md` into a new script.

---

## Hard rules

- Path A (layout delegation): never copy, fork, or derive from `document-skills:pptx` source. Only invoke via Skill tool.
- Path B (raw construction): always render INTO the reference deck (load it as the base file). Never generate from scratch when a reference is supplied — the master/theme/font scheme inheritance is the whole point.
- Never substitute font families that aren't in the reference's font scheme.
- Never use colors that aren't in the reference's extracted palette (use the constants block at the top of every render script).
- For two-tone titles: the bold and normal runs must share the same font family and size; only weight differs.
- For numbered agenda blocks: the numeral, accent bar, and topic text must share consistent vertical rhythm — y-coordinates align.
- For spotlight callouts: the icon and label must align horizontally (label vertically centered against icon).

## Failure modes

- **document-skills not installed (Path A only):** fail fast with `/plugin install document-skills@anthropic-agent-skills` instruction. Path B still works without it.
- **Layout index out of range (Path A):** the deck-orchestrator produced a visual_type the reference deck doesn't support. Either the orchestrator should have fallen back to a Path B archetype, or the reference DNA is stale. Re-run deck-extract-dna.
- **Font not in reference scheme:** the theme's font scheme will be applied at open time but the .pptx will look wrong in editors that strict-render. Always check fonts against the reference DNA before emitting.
- **Specialist chart construction failed (deck-charts):** surface the error to the user, don't fall back silently.
