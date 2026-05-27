# Minto Enforcement — Implementation Log

Implements P1–P6 from `_minto/minto-gap-analysis.md` so the 8 Minto criteria
(`_minto/minto-rubric.md`) become first-class **enforced** disciplines: generated as
data in the plan schema AND validated by executable checks (deterministic scripts +
whole-deck LLM-judges), gated into the deck-qa loop. Additive only; the validators
degrade gracefully on an old flat plan. Proven by `tests/smoke_test.py`
(Part 1: 16/16 deterministic) + a judged Part 2 (see `tests/SMOKE-RESULTS.md`).

All citations are post-edit line numbers.

---

## P1 — Pyramid + SCQA plan schema (the enabler) · criteria 1,2,6,7,8

`skills/deck-orchestrator/SKILL.md`
- `:50-54` — Phase 2 now builds the argument as **data**: governing thought (so-what assertion), SCQA arc, `key_line[]` pillars with `id`/`claim`/`logic_type`/`order_basis`, MECE discipline.
- `:55` — Phase 2 step 5 tags each content slide with `supports_pillar` + `answers_question`.
- `:73` — Phase 3 step 8 sub-bullet: pyramid linkage per slide (orphans must be assigned or cut).
- `:96-108` — Phase 4 schema extended additively: `deck_meta.scqa{situation,complication,question,answer}`, `deck_meta.key_line[{id,claim,logic_type,order_basis}]`, per-slide `supports_pillar` + `answers_question`.
- `:139` — schema note: additive / back-compatible; enums for `logic_type`/`order_basis`; `supports_pillar` values incl. the `"governing_thought"` apex marker; graceful-degradation contract.
- `:141` — approval gate (step 10) now renders the pyramid (governing thought → SCQA → pillars → grouped slides), not just the slide list.

## P2 — Storyline read-through validator (whole-deck judge) · criterion 5 (+1)

`scripts/storyline_check.py` (new, 334 lines)
- `:62` `build_title_sequence` — ordered titles from the plan (rendered titles override via `--manifest`); reuses `action_title_lint` helpers (`:48-51`), never duplicates title logic.
- `:89` `screen_governing_thought` — deterministic Criterion-1 screen (present, ≤25 words, verb, not topic).
- `:156` `build_judge_prompt` — self-contained whole-deck Criterion-1/2/5 judge prompt (titles interpolated).
- `:225` `build_packet` — deterministic findings + judge packet; degrades on flat plan; exit 1 on a failed governing-thought screen.

`skills/deck-qa/SKILL.md`
- `:27` "Four-layer" → **"Five-layer audit"** + per-slide-vs-whole-deck framing.
- `:121-136` — **Layer 5: Storyline & logic (whole-deck judge)**; `:127` Layer 5a runs `storyline_check.py` then one fresh whole-deck `Agent`.
- `:152-156` — iteration loop runs all five layers; Layer-5 breaks gate; Layer 5 re-runs in full when any title/order/linkage changes.

## P3 — Action-title linter → assertion + so-what · criteria 4 (substance), 3 (slide-level)

`scripts/action_title_lint.py`
- `:149-160` — `STRUCTURAL_ARCHETYPES` + `QUANTITATIVE_ARCHETYPES` (one copy; imported by the new scripts).
- `:478-558` — `--semantic` tier: `build_semantic_prompt` (`:491`) + `build_semantic_packet` (`:528`) emit an assertion/so-what/number judge packet; deterministic screen unchanged.
- `:560-588` — `main()` gains `--plan` + `--semantic`; attaches `semantic_judge_packet`; exit code still set by the cheap deterministic screen.
- `:16,:21-35` — docstring updated for the substance tier + importable names.

`skills/deck-qa/SKILL.md:76` — **Layer 2b** sub-step wires `--semantic` to a fresh `Agent`; cheap screen still gates.

## P4 — MECE + vertical/horizontal logic checker · criteria 6,7,8

`scripts/logic_structure_check.py` (new, 467 lines)
- `:39-49` `CATCHALL_TOKENS`/`CATCHALL_PHRASES`; `:61-62` valid enums; `:64` `APEX_MARKER`.
- `:161` `check_mece` (C8 catch-all over pillar claims + on-slide groupings), `:177` `check_vertical` (C6 orphans / childless / dangling refs, apex-exempt), `:220` `check_horizontal` (C7 logic_type + order_basis present/valid), `:245` `check_render_order` (render order == plan), `:263` `check_archetype_logic` (P6).
- `:331-...` `build_packet` — graceful degrade when no `key_line`; emits the C6/7/8 whole-deck judge packet; exit 1 on any High.

`skills/deck-qa/SKILL.md:138` — **Layer 5b** runs `logic_structure_check.py` then one fresh whole-deck `Agent`; folded into Layer 5 (NOT bolted onto the per-slide audit).

## P5 — SCQA scaffolder + opening-arc check · criterion 2 (+1,3)

`skills/deck-orchestrator/SKILL.md:57-65` — **Phase 2b: Scaffold the SCQA opening** — drafts S→C→Q→A as data, generates the opening 1–3 slides (answer-first), self-checks before Phase 3.
Opening-arc *check* reuses the Layer 5a judge: `storyline_check.py` carries the deterministic `answer ≈ governing_thought` proxy (`answer_matches_governing_thought`) + the opening-arc judge prompt.

## P6 — Archetype ↔ logic-structure mapping · criterion 7 aid

- `skills/deck-orchestrator/references/design-archetypes.md:25-40` — "Logic shape (argument fit)" table (deductive/sequential vs inductive/parallel vs single-claim) + enforcement note.
- `skills/deck-orchestrator/references/visual-types.md:93` — selection rule 7 (match archetype logic shape to the argument).
- Consistency *check*: `logic_structure_check.py` `ARCHETYPE_LOGIC` (`:69`) + `check_archetype_logic` (`:263`).

## DOCS

- `README.md` — deck-qa "four-layer" → five-layer (storyline & logic); added `storyline_check.py` + `logic_structure_check.py` to the scripts list.
- `.claude-plugin/marketplace.json` — description now states Minto Pyramid enforcement (argument tree + whole-deck storyline/logic judge + semantic so-what title judge).
- `skills/deck-orchestrator/references/pyramid-principle.md:72-78` — cross-links the MECE check + the four deck tests to the enforcing scripts (Layers 5a/5b/2b).

## SMOKE TEST

- `tests/fixtures/good-plan.json`, `bad-plan.json`, `flat-plan.json` — synthetic / brand-neutral.
- `tests/fixtures/make_fixture_deck.py` — renders a plan to a neutral `.pptx` via Path-B helpers.
- `tests/smoke_test.py` — 16 deterministic checks (every script runs clean + emits valid packets; FLAG bad / PASS good; flat → graceful skip; exit codes). **16/16 PASS.**
- `tests/SMOKE-RESULTS.md` — 8-criteria → validator → pass/fail map; records the judged Part 2 (judge PASSES good, FLAGS bad on both layers).
- `.gitignore` — ignores `tests/_artifacts/` (regenerated packets).

## Discipline notes

- Additive only; no unrelated refactors. The one shared extraction: `STRUCTURAL_ARCHETYPES`/`QUANTITATIVE_ARCHETYPES` live once in `action_title_lint.py` and are imported by `storyline_check.py` / `logic_structure_check.py` (honors "never duplicate title logic").
- `deck-charts` stub untouched. Per-slide vision audit (Layer 1) untouched — the storyline/logic checks are a NEW whole-deck mode.
- Scripts are deterministic + emit judge packets; no API calls in scripts (judges run from the deck-qa procedure via the Agent tool).
- One principled refinement beyond the spec letter: the `"governing_thought"` apex marker exempts the thesis slide from the orphan check (a pyramid apex sits above the pillars). Documented at `SKILL.md:139`.
