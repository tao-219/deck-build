---
description: Strip hidden slides, comments, and revision metadata from a .pptx before client delivery
argument-hint: <input.pptx> <output.pptx> [--remove-hidden|--remove-comments|--remove-revision-info|--remove-notes|--all]
---

# /deck-clean

Strip artifacts that shouldn't ship to a client: hidden slides (graveyard / backup), slide comments, comment authors, revision/changes metadata, and optionally speaker notes.

## Arguments

- `<input.pptx>` — source deck
- `<output.pptx>` — cleaned output
- One or more flags:
  - `--remove-hidden` — strip slides marked as `show="0"` in `sldIdLst` + drop their part files
  - `--remove-comments` — strip `ppt/comments/*.xml` + `ppt/commentAuthors.xml` + per-slide comment relationships
  - `--remove-revision-info` — strip `ppt/changesInfos/*`, `ppt/revisionInfo.xml`, `ppt/authors.xml` (collaboration metadata)
  - `--remove-notes` — strip `ppt/notesSlides/*` + `ppt/notesMasters/*` + per-slide notes relationships (NOT included in `--all`)
  - `--all` — `--remove-hidden` + `--remove-comments` + `--remove-revision-info`

## What this does

Implementation: zip-level surgery (`scripts/deck_clean.py`). Unpacks the .pptx, modifies XML files, drops unwanted parts, updates `[Content_Types].xml` + relationship files, repacks. Avoids python-pptx's limitations around slide deletion + orphan handling.

Returns a JSON summary listing what was removed, plus a human-readable count to stderr (suppress with `--quiet`).

## Common usage

**Final delivery — strip everything except notes:**
```bash
python ${CLAUDE_PLUGIN_ROOT}/scripts/deck_clean.py working/aegis/deck.pptx deliverables/deck-final.pptx --all
```

**Just strip comments before sharing internally:**
```bash
python ${CLAUDE_PLUGIN_ROOT}/scripts/deck_clean.py deck.pptx deck-no-comments.pptx --remove-comments
```

**Strip everything including notes (very-final delivery):**
```bash
python ${CLAUDE_PLUGIN_ROOT}/scripts/deck_clean.py deck.pptx deck-final.pptx --all --remove-notes
```

## Notes

- Always writes to a NEW file — never in-place. Verify the output before deleting the source.
- Hidden-slide detection uses `p:sldId show="0"` attribute — slides hidden via the PowerPoint UI Hide-Slide command. Backup slides that aren't marked as hidden won't be caught.
- After running, open the output in PowerPoint or LibreOffice to verify nothing broke. The cleaner targets standard pptx parts only — exotic add-in parts are passed through unchanged.
- If the slash command echoes its help text instead of executing on first invocation, run `/reload-plugins` to activate it in the current session.
