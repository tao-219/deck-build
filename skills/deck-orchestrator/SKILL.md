---
name: deck-orchestrator
description: This skill should be used when the user asks to build a deck, generate slides, rebuild slides to match a reference template, produce consultancy/McKinsey/BCG/Bain-style slides, apply Pyramid Principle to a presentation, or create a deck with action titles and a reference .pptx for theme/layout vocabulary. Main entry point for consultancy-grade deck generation. Orchestrates the full flow from inputs (meeting notes, objectives, content instructions) and a reference deck through Pyramid Principle structuring, action-title generation, archetype selection, rendering, and adversarial QA.
---

# Deck Orchestrator

Main entry point. Coordinates the five-skill flow:

1. **deck-extract-dna** — profile the reference deck (one-time per template)
2. **deck-orchestrator** (this skill) — ingest inputs, build slide-by-slide plan
3. **deck-render** — delegate to document-skills:pptx with structured specs
4. **deck-qa** — adversarial vision audit + content checks
5. **deck-charts** — specialist consulting charts when needed

## When to use

- User asks to build a full deck from notes/objectives + reference deck
- User asks to insert specific slides into an existing deck
- User wants the output to match McKinsey/BCG/Bain editorial standards (Pyramid Principle, action titles, single-color emphasis charts)

## Inputs

- `inputs/meeting-notes.md` (or similar content source)
- `inputs/objectives.md` (deck purpose, audience, length)
- `inputs/content-instructions.md` (specific slide asks, optional)
- `inputs/reference-deck.pptx` (theme + layout vocabulary source)
- `inputs/reference-dna.json` (output of deck-extract-dna; cached per reference)

## Outputs

- `output/deck-plan.json` — structured slide-by-slide spec (action titles, visual types, evidence)
- `output/deck.pptx` — final editable .pptx
- `output/qa-report.md` — vision audit findings

## Procedure

### Phase 1: Load context (autonomous)

1. **Load the reference DNA.** Check `inputs/reference-dna.json`. If absent, invoke `deck-extract-dna` (or run the `profile_template.py` script directly: `python ${CLAUDE_PLUGIN_ROOT}/skills/deck-extract-dna/scripts/profile_template.py <reference.pptx> <output_dir>`). The DNA contains palette, fonts, layout vocabulary, and signature lookup.
2. **Load the four reference docs** in this order:
   - `references/pyramid-principle.md` — governing-thought / SCQA / MECE rules
   - `references/action-title-pattern.md` — title construction + two-tone shape + scope qualifiers
   - `references/visual-types.md` — quick selection guide for archetypes vs generic types
   - `references/design-archetypes.md` — full anatomy/color/typography/icon recipes
3. **Read inputs.** Parse `inputs/meeting-notes.md`, `inputs/objectives.md`, optional `inputs/content-instructions.md`. If a single content brief is in the user's message instead, use that — don't require files.

### Phase 2: Structure the argument (autonomous)

4. **Apply Pyramid Principle — capture the argument as DATA, not just prose.** The pyramid is an inspectable artifact that downstream validators (`storyline_check.py`, `logic_structure_check.py`) read back, so build it as structured fields in the plan, not as transient reasoning:
   - **Governing thought** — one sentence, the deck's "so-what". A so-what *assertion* (verb present, ≤ 25 words, states a position/recommendation), never a topic label. → `deck_meta.governing_thought`.
   - **SCQA arc** — draft Situation → Complication → Question → Answer explicitly; `answer` must be the governing thought. → `deck_meta.scqa` (see Phase 2b for the scaffolder).
   - **Key line (pillars)** — decompose into 3–5 MECE supporting pillars. For EACH pillar capture: a stable `id`, the `claim` it asserts, its `logic_type` (`deductive` = premise → premise → conclusion, **or** `inductive` = parallel items of one class), and its `order_basis` (`time` | `structure` | `degree`). → `deck_meta.key_line[]`.
   - **MECE discipline** — pillars must not overlap and must cover the relevant universe. No "Other / Miscellaneous / etc." catch-all; state any deliberate exclusion explicitly ("out of scope: X").
5. **Sketch the slide list and tag each slide to the pyramid.** One slide per pillar (or per sub-pillar if a pillar needs >1 slide). Plus title-cover, the SCQA opening (agenda / context), closing/next-steps as bookends. For each CONTENT slide, record which pillar it serves (`supports_pillar` = a `key_line.id`) and the question it answers (`answers_question`). Structural slides (title-cover, section-divider, closing) carry `supports_pillar: null`.

### Phase 2b: Scaffold the SCQA opening (autonomous)

Turn the governing thought into an opening the audience can follow. This is the **generator** for `deck_meta.scqa` and the first content slides — SCQA is the weakest-supported Minto criterion when skipped, so draft it explicitly rather than letting it stay implicit:

- **Draft S → C → Q → A as data** (populate `deck_meta.scqa`):
  - **Situation** — a factual baseline the audience already accepts (no tension yet).
  - **Complication** — the change / threat / opportunity that makes the Situation unsustainable. It must be a *genuine new tension*, not a restatement of the Situation.
  - **Question** — the question the Complication forces. May stay implicit for the compressed SCR shape (then carry the resolution in `answer`).
  - **Answer** — the resolution. **The Answer must be the governing thought** (`scqa.answer` == `deck_meta.governing_thought`).
- **Generate the opening 1–3 slides from the arc.** Map Situation → Complication → (Question) → Answer onto the first content slides *in that order*, so the audience reaches the recommendation already primed. The Answer/recommendation slide lands within the first ~20% of content slides (answer-first) — never buried in the back half.
- **Self-check before Phase 3:** Is the Complication a real tension (not a paraphrase of the Situation)? Does the Answer appear up front? Is the Answer the governing thought? The deck-qa **Layer 5a** judge re-checks all three (`storyline_check.py` carries the deterministic `answer ≈ governing_thought` proxy + the opening-arc judge) — fix them here, not at QA.

### Phase 3: Plan each slide (autonomous)

For EACH slide:

6. **Write the action title** following `action-title-pattern.md`:
   - Verb test, ≤15 words, active voice, specific, no banned weasel words.
   - Default to **two-tone shape**: `bold short claim` + en-dash + `normal-weight elaboration`. If title is ≤8 words, single-weight is OK.
7. **Pick the archetype** following `visual-types.md` selection rules:
   - **Recipe archetypes ALWAYS beat generic visual types** when both fit. The recipes in `design-archetypes.md` are the highest-quality patterns.
   - **Selection meta-rules**: spotlight beats equal-weighting; block-list beats data-table for execs; three-state only when status is time-sequenced; sub-callout when there's a secondary takeaway.
   - **No fallback to `bullets`.** If no archetype fits, propose a new one and ask the user.
8. **Sketch the content** for each slot the archetype expects:
   - For `two-col-overview-with-subcallout`: left-column purpose + objectives, 4 numbered agenda items, 2–3 desired-outcome callouts.
   - For `spotlight-comparison-columns`: focus column, context columns, scope qualifier per column, focus-marker label, per-column footer content.
   - For each archetype, see its anatomy section in `design-archetypes.md`.
   - **Pyramid linkage:** set `supports_pillar` (the `key_line.id` this slide defends) and `answers_question` (the specific question it answers for that pillar). A content slide with no pillar is an orphan — assign it or cut it.

### Phase 4: Emit and approve plan (gate — STOP for user approval)

9. **Emit `deck-plan.json`** with this structure:

```json
{
  "deck_meta": {
    "governing_thought": "...",
    "audience": "...",
    "reference_deck": "<path>",
    "reference_dna": "<path to reference-dna.json>",
    "scqa": {
      "situation": "factual baseline the audience already accepts",
      "complication": "the change / tension that makes the situation unsustainable",
      "question": "the question the complication raises (may be null for the compressed SCR shape)",
      "answer": "the resolution — MUST be the governing thought"
    },
    "key_line": [
      {"id": "P1", "claim": "first pillar — a full assertion", "logic_type": "inductive", "order_basis": "degree"},
      {"id": "P2", "claim": "second pillar — a full assertion", "logic_type": "inductive", "order_basis": "degree"},
      {"id": "P3", "claim": "third pillar — a full assertion",  "logic_type": "inductive", "order_basis": "degree"}
    ]
  },
  "slides": [
    {
      "slide_number": 1,
      "archetype": "title-cover",
      "title_bold": "...",
      "title_normal": null,
      "supports_pillar": null,
      "answers_question": null,
      "content": {...}
    },
    {
      "slide_number": 2,
      "archetype": "two-col-overview-with-subcallout",
      "title_bold": "Today's session",
      "title_normal": "identify Canada CRR pain points and assess SAI built-in coverage to inform Workshop 2",
      "supports_pillar": "P1",
      "answers_question": "What will today's session produce?",
      "content": {
        "left": {"purpose": "...", "objectives": ["...", "..."]},
        "agenda": [{"n": 1, "topic": "..."}, ...],
        "sub_callout": [
          {"icon": "target", "label": "...", "caption": "..."},
          {"icon": "network", "label": "...", "caption": "..."}
        ]
      }
    }
  ]
}
```

> **Schema is additive / back-compatible.** `deck_meta.scqa`, `deck_meta.key_line`, and the per-slide `supports_pillar` / `answers_question` extend the original flat schema. `logic_type` ∈ `{deductive, inductive}`; `order_basis` ∈ `{time, structure, degree}`. `supports_pillar` is a `key_line.id` for an evidence slide, `null` for a structural slide (cover / divider / closing), or the literal `"governing_thought"` for the **apex** slide that presents the thesis (the SCQA Answer / recommendation) — the apex sits above the pillars, so it is exempt from the orphan check. A slide may carry an optional `logic_type` to override its pillar's (used by the archetype↔logic check). A plan that omits these fields still renders, and the Minto validators (`storyline_check.py`, `logic_structure_check.py`) **degrade gracefully** — they warn and skip the affected check rather than fail on an older flat plan.

10. **Present the plan to the user for approval — show the pyramid, not just the slide list.** Render: the governing thought; the SCQA arc (S → C → Q → A); the key-line pillars; then the slide list grouped under the pillar each slide supports (with its action title + archetype). The user is approving the **argument structure**, not just slide ordering. Stop and wait for approval, modification, or rejection before proceeding. **STOP HERE.**

### Phase 5: Render (post-approval)

11. **Render via `deck-render`.** For each slide:
    - **Recipe archetype** → use Path B (raw shape construction) with the helper recipes from `${CLAUDE_PLUGIN_ROOT}/scripts/deck_helpers.py`.
    - **Generic visual type** → use Path A (delegate to `document-skills:pptx`).
    - Honor the **footer-clearance budget** per archetype (see `design-archetypes.md`).
12. **Save the output deck** at the path specified in the plan.

### Phase 6: QA loop (post-render)

13. **Run archetype-compliance check**: `python ${CLAUDE_PLUGIN_ROOT}/scripts/archetype_compliance.py <deck.pptx> --plan <plan.json>`. Catches footer-clearance overruns, container clipping, two-tone title violations, verb-test failures.
14. **Run vision-LLM defect scan** via `deck-qa` skill (Layer 1).
15. **Iterate**: if any High-severity issues, regenerate affected slides and re-QA. Stop when (a) no High remaining, OR (b) iteration count ≥3 → escalate to user.
16. **Surface remaining Medium/Low issues** in the final report.

### Phase 7: Deliver

17. Output: final `.pptx` + `qa-report.md` + the approved `deck-plan.json` (for traceability).
18. **STOP.** Do not auto-iterate further without user direction.

---

## Quick-start: standalone slide rebuild from another window

If you only need to rebuild ONE slide in an existing deck (the most common use case during deck-finishing), skip Phases 1–4 and use this minimal path:

```python
import sys
sys.path.insert(0, "${CLAUDE_PLUGIN_ROOT}/scripts")  # post-install
# For standalone use without plugin install, replace the above with:
# sys.path.insert(0, "/Users/taoli/projects/deck-build/scripts")
from deck_helpers import (
    PRIMARY, FONT_HEADING, TEXT_DARK,
    two_tone_title, numbered_agenda_block, sub_callout_grid,
    spotlight_callout, target_icon, network_icon, globe_icon,
    section_header, strip_shapes, replace_title, add_arrow,
)
from pptx import Presentation

prs = Presentation("path/to/working-deck.pptx")
slide = prs.slides[N - 1]  # 1-indexed

# 1. Inventory: figure out what to keep
for s in slide.shapes:
    print(s.name, s.shape_type)

# 2. Strip and rebuild per archetype recipe (see design-archetypes.md)
strip_shapes(slide, keep_names={"Title 1", "Slide Number Placeholder", ...})
replace_title(slide, "Bold claim", "normal-weight elaboration")
# ...add archetype components per recipe...

prs.save("path/to/working-deck.pptx")
```

Then run `python ${CLAUDE_PLUGIN_ROOT}/scripts/archetype_compliance.py <deck.pptx>` to verify — exit code 0 = pass.

**Plugin slash commands (`/deck-slide`, `/deck-build`, `/deck-clean`, `/deck-preview`, `/deck-extract-dna`):** if a command echoes its help text instead of executing on first invocation in a session, run `/reload-plugins` to activate it. After editing plugin source files at `/Users/taoli/projects/deck-build/`, run `/plugin marketplace update deck-build` followed by `/reload-plugins` to pick up changes.

## Hard rules

- Every slide title must be a complete sentence with a verb (action title).
- Maximum 15 words per title.
- One idea per slide.
- Every data claim cites a footnote source.
- All colors must be from the reference deck's extracted palette.
- All fonts must be from the reference deck's font scheme.

## References

- `references/pyramid-principle.md` — structure and narrative arc rules
- `references/action-title-pattern.md` — title construction rules, two-tone visual rendering, inline scope qualifier convention
- `references/visual-types.md` — vocabulary mapping (claim type → slide archetype → layout capability) with quick-selection guide
- `references/design-archetypes.md` — recipe book for the four high-quality archetypes (anatomy, color, typography, icon usage, common pitfalls). The orchestrator must pick a recipe archetype over a generic visual type whenever the recipe fits.

## Archetype-first selection rule

When the slide is not a basic data display:

1. Read `references/design-archetypes.md` first — see if a recipe archetype fits.
2. Only if no recipe fits, fall back to a generic visual type from `references/visual-types.md`.
3. Apply the selection meta-rules: **spotlight over equal weighting**, **block-list over data-table for execs**, **three-state only for time-sequenced status**, **sub-callout grid when there's a secondary takeaway**.

The plan's per-slide spec must include an `archetype` field naming the chosen recipe (or generic visual type). The renderer (`deck-render`) and QA (`deck-qa`) both consume this field — picking the wrong archetype is the #1 quality failure mode.
