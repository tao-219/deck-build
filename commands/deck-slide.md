---
description: Insert or replace slides in an existing .pptx deck
argument-hint: <slide-spec> <existing.pptx> [position|--replace:N]
---

# /deck-slide

Insert new slides into an existing deck, OR replace an existing slide in place.

## Arguments

- `<slide-spec>` — markdown describing what the slide(s) should contain (action title, supporting points, visual type hint)
- `<existing.pptx>` — the deck to insert into (theme/layouts inherited automatically)
- `[position|--replace:N]` — placement directive:
  - `after:N` — insert after slide N (1-indexed)
  - `before:N` — insert before slide N
  - `--replace:N` — drop slide N and put the new slide at the same index
  - omitted — append at end (default)

## Modes

### Insert mode (default)

Adds a new slide at the chosen position. Existing slides shift to accommodate.

### Replace mode (`--replace:N`)

Drops the existing slide at position N (1-indexed) and inserts the new slide at the same index. Useful for rebuilding a single slide without manual delete + re-insert. Internally uses `deck_helpers.replace_slide(prs, idx, build_fn)` which handles the drop + add + reposition atomically.

**Pattern in a custom Python script:**

```python
from pptx import Presentation
from deck_helpers import replace_slide, apply_dna, two_tone_title

apply_dna("/path/to/reference-dna/")
prs = Presentation("working-deck.pptx")

def build_new_slide_5(slide):
    two_tone_title(slide, 0.5, 0.55, 12.5, 0.85,
                   "Bold short claim", "normal-weight elaboration")
    # ...rest of slide construction...

replace_slide(prs, 4, build_new_slide_5)  # 1-indexed slide 5 = idx 4
prs.save("working-deck.pptx")
```

## What this does

1. Loads the existing deck and profiles its master/layouts (via deck-extract-dna if not cached)
2. Parses the slide spec into structured form (action title, content type, evidence)
3. Selects the best layout from the existing deck
4. Renders the new slide(s) via deck-render
5. **Insert mode:** appends the new slide at end, then moves to the requested position
6. **Replace mode:** drops the target slide, appends the new slide, moves to the original index
7. Audits via deck-qa
8. Saves updated .pptx

## Prerequisite

`document-skills` plugin must be installed (for layout-driven generation paths).

## Notes

- After invoking `/deck-slide` for the first time in a session, if the slash command echoes its help text instead of executing, run `/reload-plugins` to activate it.
