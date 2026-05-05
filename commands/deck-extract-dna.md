---
description: Profile a reference .pptx deck to extract its design DNA (theme, layouts, visual conventions)
argument-hint: <reference.pptx> [output-dir]
---

# /deck-extract-dna

One-time profiling of a reference deck. Produces JSON files that downstream skills consume.

## Arguments

- `<reference.pptx>` — the deck to profile
- `[output-dir]` — where to write profile/digest/dna JSON (default: `./outputs/`)

## What this does

1. Stage 1 (programmatic): walks slide_masters and slide_layouts via python-pptx; extracts theme1.xml palette and font scheme. Output: `{name}-profile.json` + `{name}-digest.json`
2. Stage 2 (vision-LLM): rasterizes a sample of slides via LibreOffice; sends thumbnails to a vision-capable Claude with a controlled-vocabulary prompt for qualitative DNA. Output: `{name}-dna.json`
3. Presents summary: layouts found, theme colors (with hex), fonts, qualitative highlights

Cache is keyed by file-hash + mtime — re-runs are no-ops unless the reference deck changes.

## Notes

- If the slash command echoes its help text instead of executing on first invocation, run `/reload-plugins` to activate it in the current session.
