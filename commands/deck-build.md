---
description: Generate a full consultancy-grade .pptx deck from inputs and a reference deck
argument-hint: <inputs-dir> <reference.pptx> [output-dir]
---

# /deck-build

Build a full deck from meeting notes / objectives / content instructions, matched to a reference deck's style.

## Arguments

- `<inputs-dir>` — folder containing meeting-notes.md, objectives.md, optional content-instructions.md
- `<reference.pptx>` — the reference deck whose theme + layouts will be inherited
- `[output-dir]` — where to write outputs (default: `./outputs/`)

## What this does

1. Loads the deck-orchestrator skill
2. Loads or generates reference DNA via deck-extract-dna
3. Reads inputs and produces a slide-by-slide plan (Pyramid Principle, action titles)
4. Presents the plan for user approval
5. On approval: renders via deck-render → audits via deck-qa → iterates until clean
6. Outputs final .pptx + qa-report.md

## Prerequisite

`document-skills` plugin must be installed:
```
/plugin install document-skills@anthropic-agent-skills
```

## Notes

- If the slash command echoes its help text instead of executing on first invocation, run `/reload-plugins` to activate it in the current session.
