---
description: Render a .pptx to PDF + per-slide JPEGs for human visual review
argument-hint: <input.pptx> [--out <dir>] [--slide N] [--dpi 150] [--open]
---

# /deck-preview

Render a .pptx to PDF + per-slide JPEGs you can open and review. Outputs land next to the source deck (in a `<stem>-preview/` subfolder) by default — somewhere you'd naturally find them.

This is for *you*, not for AI vision audit (that's `vision_audit_render.py`, which writes to a temp dir + manifest for subagent consumption).

## Arguments

- `<input.pptx>` — the deck to render
- `[--out <dir>]` — output directory (default: `<input>-preview/` in the source's parent folder)
- `[--slide N]` — render only slide N (1-indexed); omit to render all
- `[--dpi 150]` — render resolution (default 150; use 110 for faster, 200+ for printable)
- `[--open]` — open the resulting PDF in macOS Preview after render

## What this does

Pipeline: `soffice --headless --convert-to pdf` (LibreOffice) → `pdftoppm -jpeg` (poppler). Output structure:

```
<deck>-preview/
├── <deck>.pdf              ← full deck as PDF
├── slide-01.jpg            ← per-slide JPEG (zero-padded, 2-digit)
├── slide-02.jpg
└── ...
```

Returns a JSON summary listing the PDF + image paths.

## Common usage

**Quick visual sanity-check after a rebuild:**
```bash
python ${CLAUDE_PLUGIN_ROOT}/scripts/deck_preview.py working/aegis/deck.pptx --open
```

**Just render slide 5 (faster iteration loop):**
```bash
python ${CLAUDE_PLUGIN_ROOT}/scripts/deck_preview.py deck.pptx --slide 5 --open
```

**Print-quality render to a specific folder:**
```bash
python ${CLAUDE_PLUGIN_ROOT}/scripts/deck_preview.py deck.pptx --out ~/Desktop/preview/ --dpi 220
```

## Prerequisites

- LibreOffice installed (`brew install --cask libreoffice` on macOS)
- Poppler installed (`brew install poppler` on macOS) — provides `pdftoppm`

## Notes

- LibreOffice rendering is close-but-not-identical to Microsoft PowerPoint rendering. For client delivery, always open the actual `.pptx` in PowerPoint as a final check.
- If the slash command echoes its help text instead of executing on first invocation, run `/reload-plugins` to activate it in the current session.
