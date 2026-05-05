---
name: deck-extract-dna
description: This skill should be used when the user asks to profile a reference .pptx deck, extract a deck's theme/colors/fonts/layouts, set up a new reference template, re-profile an updated template, or inspect a deck's master/layouts. Produces JSON artifacts that other deck-build skills (deck-orchestrator, deck-render) consume to ensure new content matches the reference style. Run once per reference template; cache the result.
---

# Deck Extract DNA

Profile a reference deck. Output two JSON artifacts that downstream skills consume.

## When to use

- A new reference deck has been supplied (one-time setup per template)
- An existing reference deck has been updated (re-profile)
- The user asks to inspect a deck's master, layouts, or theme

## Inputs

- `inputs/reference.pptx` — the reference deck to profile

## Outputs (currently implemented — Stage 1 only)

- `outputs/{name}-profile.json` — full profile with placeholder positions, theme palette, font scheme (renderer-facing). Source: `scripts/profile_template.py`.
- `outputs/{name}-digest.json` — compact capability summary (LLM-facing). Source: same script.

**Future (Stage 2 — not yet implemented):**
- `outputs/{name}-dna.json` — qualitative visual DNA from vision-LLM pass.

## Two-stage extraction

Per design decision in `docs/research/07_synthesis_and_plan.md`: separate XML extraction from vision-LLM interpretation.

### Stage 1: Programmatic XML extraction (ground truth) — IMPLEMENTED

Script:
- `${CLAUDE_PLUGIN_ROOT}/skills/deck-extract-dna/scripts/profile_template.py` — walk slide_masters / slide_layouts via python-pptx; emit placeholder inventory, signatures, capabilities, theme palette, font scheme into `profile.json` + `digest.json`

This stage is **deterministic and lossless**. Output drives the renderer.

```bash
python ${CLAUDE_PLUGIN_ROOT}/skills/deck-extract-dna/scripts/profile_template.py <reference.pptx> <output_dir>
```

### Stage 2: Vision-LLM qualitative interpretation — STUB

Planned script (not yet built):
- `scripts/visual_dna.py` — rasterize a sample of slides via LibreOffice; send thumbnails to a vision-capable Claude with a controlled-vocabulary prompt

Will capture what XML can't:
- Composition philosophy (executive-spacious vs analyst-dense)
- Chart emphasis style (single-color vs diverging palette)
- Footnote convention (8pt italic right-aligned vs 10pt below chart)
- Density rhythm (max bullets per slide observed, header-row depth, etc.)

When built, output will be controlled-vocabulary JSON; the renderer will use it as soft guidance for layout choices.

## Procedure

1. Run `profile_template.py` on the reference deck. Produces `profile.json` (full) + `digest.json` (compact).
2. (Future) Run `visual_dna.py` on a sampled subset of slides (~5-10 representative). Produces `dna.json`.
3. Present summary to the user: layouts found, theme colors, fonts, qualitative DNA highlights (when Stage 2 exists).

## Caching

Profile by file-hash + mtime. Re-profile only when the reference deck changes.
